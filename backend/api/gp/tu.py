# backend/api/gp/tu.py
"""
API endpoints для подготовки запросов ТУ (технических условий).

ОБНОВЛЕНО (01.01.2025): Интеграция с БД
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form, Request
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import io
import zipfile
from datetime import datetime
import re

from parsers.application_parser import parse_application_docx, ApplicationData
from parsers.egrn_parser import parse_egrn_xml, EGRNData
from generator.tu_requests_builder import build_tu_docs_with_outgoing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/tu", tags=["tu"])


@router.post("/parse-application")
async def parse_application_endpoint(file: UploadFile = File(...)):
    """Парсинг заявления о выдаче ГПЗУ из DOCX файла."""
    
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате DOCX")
    
    try:
        content = await file.read()
        logger.info(f"ТУ: получено заявление {file.filename}, размер {len(content)} байт")
        
        app_data: ApplicationData = parse_application_docx(content)
        
        return {
            "success": True,
            "data": {
                "number": app_data.number,
                "date": app_data.date.isoformat() if app_data.date else None,
                "date_text": app_data.date_text,
                "applicant": app_data.applicant,
                "cadnum": app_data.cadnum,
                "purpose": app_data.purpose,
            }
        }
        
    except Exception as ex:
        logger.exception(f"ТУ: ошибка парсинга заявления: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки заявления: {str(ex)}")


@router.post("/parse-egrn")
async def parse_egrn_endpoint(file: UploadFile = File(...)):
    """Парсинг выписки ЕГРН для извлечения данных участка."""
    
    if not file.filename or not (file.filename.lower().endswith('.xml') or file.filename.lower().endswith('.zip')):
        raise HTTPException(status_code=400, detail="Файл должен быть в формате XML или ZIP")
    
    try:
        content = await file.read()
        logger.info(f"ТУ: получена выписка ЕГРН {file.filename}, размер {len(content)} байт")
        
        egrn: EGRNData = parse_egrn_xml(content)
        
        if not egrn.is_land:
            raise HTTPException(status_code=400, detail="Это не выписка ЕГРН по земельному участку")
        
        return {
            "success": True,
            "data": {
                "cadnum": egrn.cadnum,
                "address": egrn.address,
                "area": egrn.area,
                "permitted_use": egrn.permitted_use,
            }
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"ТУ: ошибка парсинга ЕГРН: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка обработки выписки ЕГРН: {str(ex)}")


@router.post("/generate")
async def generate_tu_endpoint(request: Request):
    """
    Генерация запросов ТУ с регистрацией в БД.
    
    ОБНОВЛЕНО: Теперь создает Application + TuRequest в БД
    
    Принимает JSON:
    {
        "application": {
            "number": "...",
            "date": "...",
            "applicant": "..."
        },
        "egrn": {
            "cadnum": "...",
            "address": "...",
            "area": "...",
            "vri": "..."
        }
    }
    
    Также поддерживает старый формат с Form данными для обратной совместимости.
    """
    
    try:
        # Пробуем JSON формат (новый)
        try:
            data = await request.json()
            application = data.get("application", {})
            egrn = data.get("egrn", {})
            
            cadnum = egrn.get("cadnum")
            address = egrn.get("address")
            area = egrn.get("area")
            vri = egrn.get("vri") or egrn.get("permitted_use")
            app_number = application.get("number")
            app_date = application.get("date")
            applicant = application.get("applicant")
            
        except:
            # Fallback на Form данные (старый формат)
            form = await request.form()
            cadnum = form.get("cadnum")
            address = form.get("address")
            area = form.get("area")
            vri = form.get("vri")
            app_number = form.get("app_number")
            app_date = form.get("app_date")
            applicant = form.get("applicant")
        
        # Валидация
        if not all([cadnum, address, area, vri, app_number, app_date, applicant]):
            raise HTTPException(status_code=400, detail="Неполные данные")
        
        logger.info(f"📝 ТУ: генерация запросов для КН {cadnum}, заявление {app_number}")
        
        # Генерируем документы (теперь с записью в БД)
        docs = build_tu_docs_with_outgoing(
            cadnum=cadnum,
            address=address,
            area=area,
            vri=vri,
            app_number=app_number,
            app_date=app_date,
            applicant=applicant,
        )
        
        logger.info(f"✅ ТУ: сгенерировано документов: {len(docs)}")
        
        # Создаём ZIP архив
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, file_bytes in docs:
                zip_file.writestr(filename, file_bytes)
                logger.info(f"📦 ТУ: добавлен в архив: {filename}")
        
        zip_buffer.seek(0)
        
        # Формируем имя ZIP архива
        cadnum_safe = cadnum.replace(":", "_")
        
        date_for_filename = ""
        try:
            digits = re.findall(r'\d+', app_date)
            if len(digits) >= 3:
                day, month, year = digits[0], digits[1], digits[2]
                date_for_filename = f"{day}-{month}-{year}"
            else:
                date_for_filename = datetime.now().strftime("%d-%m-%Y")
        except:
            date_for_filename = datetime.now().strftime("%d-%m-%Y")
        
        zip_filename = f"TU_{cadnum_safe}_{date_for_filename}.zip"
        
        logger.info(f"📤 ТУ: отправка архива {zip_filename}")
        
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'}
        )
        
    except HTTPException:
        raise
    except RuntimeError as ex:
        logger.error(f"❌ ТУ: ошибка генерации: {ex}")
        raise HTTPException(status_code=500, detail=str(ex))
    except Exception as ex:
        logger.exception(f"❌ ТУ: неожиданная ошибка: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации запросов ТУ: {str(ex)}")