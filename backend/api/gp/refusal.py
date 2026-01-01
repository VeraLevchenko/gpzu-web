# backend/api/gp/refusal.py
"""
API endpoints для формирования отказа в выдаче ГПЗУ.

ОБНОВЛЕНО (31.12.2024): Интеграция с БД
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import logging
import io

from generator.refusal_builder import build_refusal_document

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
            "permitted_use": "..."
        },
        "reason_code": "NO_RIGHTS"
    }
    
    ОБНОВЛЕНО: Теперь создает запись в БД (Application + Refusal)
    """
    try:
        data = await request.json()
        
        application = data.get("application")
        egrn = data.get("egrn")
        reason_code = data.get("reason_code")
        
        if not application or not egrn or not reason_code:
            raise HTTPException(status_code=400, detail="Неполные данные")
        
        if reason_code not in REFUSAL_REASONS:
            raise HTTPException(status_code=400, detail="Неверная причина отказа")
        
        reason_info = REFUSAL_REASONS[reason_code]
        
        # Формируем контекст для генератора
        context = {
            "app_number": application.get("number", "—"),
            "app_date": application.get("date", "—"),
            "applicant": application.get("applicant", "—"),
            "phone": application.get("phone", "—"),
            "email": application.get("email", "—"),
            "cadnum": egrn.get("cadnum", "—"),
            "address": egrn.get("address", "—"),
            "area": egrn.get("area", "—"),
            "permitted_use": egrn.get("permitted_use", "—"),
            "reason_code": reason_code,
            "reason_text": reason_info["text"],
            "reason_title": reason_info["title"],
        }
        
        logger.info(f"📝 Генерация отказа для заявления {context['app_number']}, причина: {reason_code}")
        
        # Генерируем документ (теперь с записью в БД)
        docx_bytes, out_number, out_date = build_refusal_document(context)
        
        cadnum_safe = context["cadnum"].replace(":", "_")
        filename = f"Otkaz_{out_number}_{cadnum_safe}.docx"
        
        logger.info(f"✅ Отказ сформирован: исх. №{out_number} от {out_date}")
        
        return StreamingResponse(
            io.BytesIO(docx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
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