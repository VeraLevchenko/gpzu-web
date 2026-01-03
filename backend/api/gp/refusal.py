# backend/api/gp/refusal.py
"""
API endpoints для формирования отказа в выдаче ГПЗУ.

ОБНОВЛЕНО (01.01.2026): Интеграция с БД + уведомления о записи
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
import logging
import io
from datetime import datetime

from generator.refusal_builder import build_refusal_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/refusal", tags=["refusal"])


# Справочник причин отказа
REFUSAL_REASONS = {
    "NO_RIGHTS": {
        "title": "Отсутствие прав на земельный участок",
        "text": "не представлены документы, подтверждающие право на земельный участок"
    },
    "NO_BORDERS": {
        "title": "Земельный участок без границ",
        "text": "границы земельного участка не установлены"
    },
    "NOT_IN_CITY": {
        "title": "Земельный участок не в городе",
        "text": "земельный участок расположен за пределами города"
    },
    "OBJECT_NOT_EXISTS": {
        "title": "Объект не существует",
        "text": "объект отсутствует в ЕГРН"
    },
    "HAS_ACTIVE_GP": {
        "title": "Есть действующий ГП",
        "text": "ранее выданный градплан не утратил силу"
    }
}

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "refusal"}

@router.post("/generate")
async def generate_refusal(request: Request):
    """
    Генерация документа отказа.
    
    Ожидает JSON:
    {
        "application": {
            "number": "...",
            "date": "...",
            "applicant": "...",
            "phone": "...",
            "email": "..."
        },
        "egrn": {
            "cadnum": "...",
            "address": "...",
            "area": "...",
            "vri": "..."
        },
        "refusal": {
            "date": "ДД.ММ.ГГГГ",
            "reason_code": "NO_RIGHTS"
        }
    }
    
    ОБНОВЛЕНО: Создает записи в БД (Application + Refusal) и уведомляет пользователя
    """
    try:
        data = await request.json()
        
        application = data.get("application")
        egrn = data.get("egrn")
        refusal = data.get("refusal")
        
        if not application or not egrn or not refusal:
            raise HTTPException(status_code=400, detail="Неполные данные")
        
        reason_code = refusal.get("reason_code")
        if reason_code not in REFUSAL_REASONS:
            raise HTTPException(status_code=400, detail="Неверная причина отказа")
        
        logger.info(f"📝 Генерация отказа для заявления {application.get('number')}, причина: {reason_code}")
        
        # Формируем контекст для генератора (в новом формате)
        context = {
            "application": application,
            "egrn": egrn,
            "refusal": refusal
        }
        
        # Генерируем документ с записью в БД
        result = build_refusal_doc(context)
        
        cadnum_safe = egrn.get("cadnum", "unknown").replace(":", "_")
        date_str = datetime.now().strftime('%d-%m-%Y')
        filename = f"Otkaz_{cadnum_safe}_{date_str}.docx"
        
        # Формируем сообщение для пользователя
        message = "Отказ успешно сформирован"
        if result['application_created']:
            message += ". ✅ Создана запись в журнале заявлений"
        else:
            message += ". ℹ️ Использована существующая запись заявления"
        message += f". ✅ Запись в журнале отказов (ID: {result['refusal_id']})"
        
        logger.info(f"✅ {message}")
        
        return Response(
            content=result['document'],
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Message": message,
                "X-Application-Created": str(result['application_created']),
                "X-Refusal-ID": str(result['refusal_id'])
            }
        )
    
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"❌ Ошибка генерации отказа: {ex}")
        raise HTTPException(status_code=500, detail=str(ex))


@router.get("/reasons")
async def get_refusal_reasons():
    """Получить список причин отказа"""
    return REFUSAL_REASONS