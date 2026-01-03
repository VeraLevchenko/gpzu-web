from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Dict, Any
import logging

from parsers.application_parser import parse_application_docx, ApplicationData
from utils.kaiten_service import create_card
from database import SessionLocal
from models.application import Application
from core.config import (
    KAITEN_DOMAIN,
    KAITEN_SPACE_ID,
    KAITEN_BOARD_ID,
    KAITEN_FIELD_CADNUM,
    KAITEN_FIELD_SUBMIT_METHOD,
    KAITEN_SUBMIT_METHOD_EPGU,
    KAITEN_FIELD_INCOMING_DATE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/kaiten", tags=["kaiten"])


def get_or_create_application(app_data: Dict[str, Any], db_session) -> int:
    """Находит существующее заявление или создает новое."""
    app_number = app_data.get('number', '')
    
    existing = db_session.query(Application).filter(Application.number == app_number).first()
    
    if existing:
        logger.info(f"✅ Найдено существующее заявление #{app_number} (ID: {existing.id})")
        return existing.id
    
    logger.info(f"📝 Создаем новое заявление #{app_number}")
    
    application = Application(
        number=app_number,
        date=app_data.get('date_text', ''),
        applicant=app_data.get('applicant', ''),
        phone='—',
        email='—',
        cadnum=app_data.get('cadnum', ''),
        address='—',
        area=None,
        permitted_use=app_data.get('purpose', ''),
        status='in_progress'
    )
    
    db_session.add(application)
    db_session.flush()
    
    logger.info(f"✅ Заявление создано (ID: {application.id})")
    return application.id


@router.post("/parse-application")
async def parse_application_endpoint(file: UploadFile = File(...)):
    """Парсинг заявления из DOCX"""
    
    if not file.filename.lower().endswith('.docx'):
        raise HTTPException(400, "Файл должен быть в формате DOCX")
    
    try:
        content = await file.read()
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
                "service_date": app_data.service_date.isoformat() if app_data.service_date else None,
            }
        }
        
    except Exception as ex:
        logger.exception(f"Ошибка парсинга: {ex}")
        raise HTTPException(500, f"Ошибка обработки файла: {str(ex)}")


@router.post("/create-task")
async def create_task_endpoint(data: Dict[str, Any]):
    """Создание задачи в Kaiten с записью в БД"""
    
    db = SessionLocal()
    
    try:
        app_data = data.get("application", {})
        
        # ========== СОЗДАЕМ/НАХОДИМ APPLICATION В БД ========== #
        application_id = get_or_create_application(app_data, db)
        db.commit()
        
        # ========== СОЗДАЕМ КАРТОЧКУ В KAITEN ========== #
        applicant = app_data.get("applicant", "Неизвестный заявитель")
        number = app_data.get("number")
        
        if number and applicant:
            title = f"{number} {applicant}"
        elif number:
            title = number
        else:
            title = applicant
        
        cadnum = app_data.get("cadnum", "—")
        purpose = app_data.get("purpose", "—")
        date_text = app_data.get("date_text", "—")
        
        description = (
            f"**Заявление №:** {number or 'б/н'}\n"
            f"**Заявитель:** {applicant}\n"
            f"**Кадастровый номер:** {cadnum}\n"
            f"**Цель:** {purpose}\n"
            f"**Дата заявления:** {date_text}\n\n"
            "created by web app"
        )
        
        properties = {}
        
        if KAITEN_FIELD_CADNUM and cadnum and cadnum != "—":
            properties[KAITEN_FIELD_CADNUM] = cadnum
        
        if KAITEN_FIELD_SUBMIT_METHOD and KAITEN_SUBMIT_METHOD_EPGU:
            properties[KAITEN_FIELD_SUBMIT_METHOD] = [KAITEN_SUBMIT_METHOD_EPGU]
        
        incoming_date = app_data.get("date")
        if KAITEN_FIELD_INCOMING_DATE and incoming_date:
            properties[KAITEN_FIELD_INCOMING_DATE] = {
                "date": incoming_date,
                "time": None,
                "tzOffset": None,
            }
        
        card_id = await create_card(
            title=title,
            description=description,
            due_date=app_data.get("service_date"),
            properties=properties or None,
        )
        
        if not card_id:
            raise HTTPException(500, "Не удалось создать карточку в Kaiten")
        
        card_url = (
            f"https://{KAITEN_DOMAIN}"
            f"/space/{KAITEN_SPACE_ID}"
            f"/boards/card/{card_id}"
        )
        
        logger.info(f"✅ Задача создана: Application ID={application_id}, Kaiten card={card_id}")
        
        return {
            "success": True,
            "card_id": card_id,
            "card_url": card_url,
            "application_id": application_id
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as ex:
        db.rollback()
        logger.exception(f"Ошибка создания задачи: {ex}")
        raise HTTPException(500, f"Ошибка: {str(ex)}")
    finally:
        db.close()