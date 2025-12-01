# backend/api/gp/tu.py
"""
API endpoints для подготовки запросов ТУ (технических условий).

Функционал:
- Парсинг заявления из DOCX
- Парсинг выписки ЕГРН
- Генерация 3 запросов ТУ (Водоканал, Газ, Тепло)
- Автоматическая регистрация в журнале Excel
- Скачивание ZIP архива с документами
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import io
import zipfile
from datetime import datetime

from parsers.application_parser import parse_application_docx, ApplicationData
from parsers.egrn_parser import parse_egrn_xml, EGRNData
from generator.tu_requests_builder import build_tu_docs_with_outgoing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/tu", tags=["tu"])


# ============================================================================
# ENDPOINT 1: Парсинг заявления
# ============================================================================

@router.post("/parse-application")
async def parse_application_endpoint(file: UploadFile = File(...)):
    """
    Парсинг заявления о выдаче ГПЗУ из DOCX файла.
    
    Извлекает:
    - Номер заявления
    - Дату заявления
    - Заявителя (ФИО или наименование ЮЛ)
    - Кадастровый номер ЗУ
    - Цель использования ЗУ
    
    Args:
        file: DOCX файл заявления
    
    Returns:
        JSON с данными заявления
    
    Raises:
        400: Неверный формат файла
        500: Ошибка парсинга
    """
    
    # Проверка формата
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате DOCX"
        )
    
    try:
        # Читаем файл
        content = await file.read()
        logger.info(f"ТУ: получено заявление {file.filename}, размер {len(content)} байт")
        
        # Парсим
        app_data: ApplicationData = parse_application_docx(content)
        
        # Формируем ответ
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
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки заявления: {str(ex)}"
        )


# ============================================================================
# ENDPOINT 2: Парсинг выписки ЕГРН
# ============================================================================

@router.post("/parse-egrn")
async def parse_egrn_endpoint(file: UploadFile = File(...)):
    """
    Парсинг выписки ЕГРН для извлечения данных участка.
    
    Извлекает:
    - Кадастровый номер
    - Адрес
    - Площадь
    - ВРИ (вид разрешённого использования)
    
    Args:
        file: XML или ZIP файл выписки ЕГРН
    
    Returns:
        JSON с данными участка
    
    Raises:
        400: Неверный формат или не земельный участок
        500: Ошибка парсинга
    """
    
    # Проверка формата
    if not file.filename or not (
        file.filename.lower().endswith('.xml') or 
        file.filename.lower().endswith('.zip')
    ):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате XML или ZIP"
        )
    
    try:
        # Читаем файл
        content = await file.read()
        logger.info(f"ТУ: получена выписка ЕГРН {file.filename}, размер {len(content)} байт")
        
        # Парсим
        egrn: EGRNData = parse_egrn_xml(content)
        
        # Проверяем что это ЗУ
        if not egrn.is_land:
            raise HTTPException(
                status_code=400,
                detail="Это не выписка ЕГРН по земельному участку"
            )
        
        # Формируем ответ
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
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки выписки ЕГРН: {str(ex)}"
        )


# ============================================================================
# ENDPOINT 3: Генерация запросов ТУ
# ============================================================================

@router.post("/generate")
async def generate_tu_endpoint(
    cadnum: str = Form(..., description="Кадастровый номер"),
    address: str = Form(..., description="Адрес участка"),
    area: str = Form(..., description="Площадь участка"),
    vri: str = Form(..., description="ВРИ (вид разрешённого использования)"),
    app_number: str = Form(..., description="Номер заявления"),
    app_date: str = Form(..., description="Дата заявления"),
    applicant: str = Form(..., description="Заявитель"),
):
    """
    Генерация запросов ТУ с автоматической регистрацией в журнале Excel.
    
    Создаёт 3 документа:
    1. Запрос в Водоканал
    2. Запрос на Газоснабжение
    3. Запрос на Теплоснабжение
    
    Каждому запросу присваивается уникальный исходящий номер.
    Запросы регистрируются в журнале Excel.
    Возвращается ZIP архив с 3 файлами DOCX.
    
    Args:
        cadnum: Кадастровый номер ЗУ
        address: Адрес участка
        area: Площадь участка (кв.м)
        vri: Вид разрешённого использования
        app_number: Номер заявления
        app_date: Дата заявления (например, "15.11.2025")
        applicant: Заявитель (ФИО или наименование организации)
    
    Returns:
        StreamingResponse с ZIP архивом
    
    Raises:
        500: Ошибка генерации или регистрации
    """
    
    try:
        logger.info(
            f"ТУ: генерация запросов для КН {cadnum}, "
            f"заявление {app_number} от {app_date}"
        )
        
        # Генерируем документы с регистрацией
        docs = build_tu_docs_with_outgoing(
            cadnum=cadnum,
            address=address,
            area=area,
            vri=vri,
            app_number=app_number,
            app_date=app_date,
            applicant=applicant,
        )
        
        logger.info(f"ТУ: сгенерировано документов: {len(docs)}")
        
        # Создаём ZIP архив в памяти
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, file_bytes in docs:
                zip_file.writestr(filename, file_bytes)
                logger.info(f"ТУ: добавлен в архив: {filename}")
        
        zip_buffer.seek(0)
        
        # Формируем имя ZIP архива
        # Пример: TU_42_30_0102050255_15-11-2025.zip
        # ВАЖНО: Только латиница и цифры (HTTP header не поддерживает кириллицу)
        import re
        from datetime import datetime
        
        cadnum_safe = cadnum.replace(":", "_")
        
        # Извлекаем дату из app_date (может быть в разных форматах)
        # Варианты: "15.11.2025", "«15» ноября 2025 г.", "2025-11-15"
        date_for_filename = ""
        try:
            # Пробуем извлечь цифры даты
            digits = re.findall(r'\d+', app_date)
            if len(digits) >= 3:
                # Предполагаем формат DD.MM.YYYY или аналогичный
                day, month, year = digits[0], digits[1], digits[2]
                date_for_filename = f"{day}-{month}-{year}"
            else:
                # Если не получилось - используем текущую дату
                date_for_filename = datetime.now().strftime("%d-%m-%Y")
        except Exception:
            # В случае ошибки - текущая дата
            date_for_filename = datetime.now().strftime("%d-%m-%Y")
        
        zip_filename = f"TU_{cadnum_safe}_{date_for_filename}.zip"
        
        logger.info(f"ТУ: отправка архива {zip_filename}")
        
        # Возвращаем ZIP как StreamingResponse
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="{zip_filename}"'
            }
        )
        
    except RuntimeError as ex:
        # Ошибки из build_tu_docs_with_outgoing (журнал открыт, блокировка и т.д.)
        logger.error(f"ТУ: ошибка генерации: {ex}")
        raise HTTPException(
            status_code=500,
            detail=str(ex)
        )
    except Exception as ex:
        logger.exception(f"ТУ: неожиданная ошибка: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации запросов ТУ: {str(ex)}"
        )