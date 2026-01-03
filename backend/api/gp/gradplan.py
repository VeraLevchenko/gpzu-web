from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
import os
import logging
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from generator.gp_builder import GPBuilder
from models.gp_data import GPData, ParcelInfo
from utils.spatial_analysis import perform_spatial_analysis
from database import SessionLocal
from models.application import Application

router = APIRouter()
logger = logging.getLogger("gpzu-web.gradplan")

# Путь к шаблону
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "gpzu_template.docx"
UPLOADS_DIR = BASE_DIR / "uploads"

# Создаём директорию для загрузок
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def get_or_create_application(app_data: Dict[str, Any], parcel_data: Dict[str, Any], db_session) -> int:
    """Находит существующее заявление или создает новое."""
    app_number = app_data.get('number', '')
    
    existing = db_session.query(Application).filter(Application.number == app_number).first()
    
    if existing:
        logger.info(f"✅ Найдено существующее заявление #{app_number} (ID: {existing.id})")
        return existing.id
    
    logger.info(f"📝 Создаем новое заявление #{app_number}")
    
    application = Application(
        number=app_number,
        date=app_data.get('date', ''),
        applicant=app_data.get('applicant', ''),
        phone=app_data.get('phone', '—'),
        email=app_data.get('email', '—'),
        cadnum=parcel_data.get('cadnum', ''),
        address=parcel_data.get('address', ''),
        area=float(parcel_data.get('area', 0)) if parcel_data.get('area') else None,
        permitted_use=parcel_data.get('permitted_use', ''),
        status='in_progress'
    )
    
    db_session.add(application)
    db_session.flush()
    
    logger.info(f"✅ Заявление создано (ID: {application.id})")
    return application.id


@router.post("/generate")
async def generate_gradplan(request: Request):
    """Генерация градостроительного плана с записью в БД"""
    
    db = SessionLocal()
    
    try:
        data = await request.json()
        logger.info("Получен запрос на генерацию градплана")
        
        # Валидация обязательных полей
        if not data.get("application"):
            raise HTTPException(status_code=400, detail="Отсутствуют данные заявления")
        if not data.get("parcel"):
            raise HTTPException(status_code=400, detail="Отсутствуют данные участка")
        if not data.get("zone"):
            raise HTTPException(status_code=400, detail="Отсутствуют данные территориальной зоны")
        
        # ========== СОЗДАЕМ/НАХОДИМ APPLICATION В БД ========== #
        application_id = get_or_create_application(
            app_data=data["application"],
            parcel_data=data["parcel"],
            db_session=db
        )
        db.commit()
        
        # ========== ГЕНЕРАЦИЯ ДОКУМЕНТА ========== #
        app_number = data["application"].get("number", "UNKNOWN").replace("/", "-")
        cadnum = data["parcel"].get("cadnum", "UNKNOWN").replace(":", "-")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"GPZU_{cadnum}_{app_number}_{timestamp}.docx"
        output_path = UPLOADS_DIR / output_filename
        
        builder = GPBuilder(str(TEMPLATE_PATH))
        result_path = builder.generate(data, str(output_path))
        
        logger.info(f"✅ Градплан успешно сформирован: {result_path} (Application ID: {application_id})")
        
        return JSONResponse(content={
            "success": True,
            "message": "Градостроительный план успешно сформирован",
            "filename": output_filename,
            "download_url": f"/api/gp/gradplan/download/{output_filename}",
            "application_id": application_id
        })
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка генерации градплана: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/download/{filename}")
async def download_gradplan(filename: str):
    """Скачивание сгенерированного градплана"""
    file_path = UPLOADS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.post("/spatial-analysis")
async def spatial_analysis(request: Request):
    """Пространственный анализ участка по координатам из ЕГРН"""
    try:
        data = await request.json()
        cadnum = data.get("cadnum")
        coordinates = data.get("coordinates", [])
        
        if not cadnum:
            raise HTTPException(status_code=400, detail="Не указан кадастровый номер")
        
        if not coordinates:
            raise HTTPException(status_code=400, detail="Не указаны координаты участка")
        
        logger.info(f"Пространственный анализ для КН: {cadnum}")
        
        gp_data = GPData()
        gp_data.parcel = ParcelInfo(
            cadnum=cadnum,
            address="",
            area="",
            coordinates=coordinates
        )
        
        gp_data = perform_spatial_analysis(gp_data)
        
        result = {
            "zone": {
                "code": gp_data.zone.code if gp_data.zone else "",
                "name": gp_data.zone.name if gp_data.zone else ""
            } if gp_data.zone else None,
            
            "capital_objects": [
                {
                    "cadnum": obj.cadnum,
                    "object_type": obj.object_type,
                    "purpose": obj.purpose,
                    "area": obj.area,
                    "floors": obj.floors
                }
                for obj in gp_data.capital_objects
            ],
            
            "zouit": [
                {
                    "name": z.name,
                    "registry_number": z.registry_number,
                    "area": z.area,
                    "document": z.document,
                    "restrictions": z.restrictions
                }
                for z in gp_data.zouit
            ],
            
            "planning_project": {
                "exists": gp_data.planning_project.exists if gp_data.planning_project else False,
                "decision_full": gp_data.planning_project.decision_full if gp_data.planning_project else "Документация по планировке территории не утверждена",
                "project_type": gp_data.planning_project.project_type if gp_data.planning_project else None,
                "project_name": gp_data.planning_project.project_name if gp_data.planning_project else None,
                "decision_number": gp_data.planning_project.decision_number if gp_data.planning_project else None,
                "decision_date": gp_data.planning_project.decision_date if gp_data.planning_project else None,
            } if gp_data.planning_project else {
                "exists": False,
                "decision_full": "Документация по планировке территории не утверждена"
            },
            
            "warnings": gp_data.warnings,
            "errors": gp_data.errors
        }
        
        logger.info(f"Анализ выполнен: зона={result['zone']}, ОКС={len(result['capital_objects'])}, ЗОУИТ={len(result['zouit'])}")
        
        return JSONResponse(content=result)
        
    except Exception as e:
        logger.error(f"Ошибка пространственного анализа: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Проверка здоровья API градплана"""
    return JSONResponse(content={"status": "ok", "service": "gradplan"})