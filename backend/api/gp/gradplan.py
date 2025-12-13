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

router = APIRouter()
logger = logging.getLogger("gpzu-web.gradplan")

# Путь к шаблону
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "gpzu_template.docx"
UPLOADS_DIR = BASE_DIR / "uploads"

# Создаём директорию для загрузок
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/generate")
async def generate_gradplan(request: Request):
    """
    Генерация градостроительного плана.
    
    Принимает JSON с полными данными для формирования ГПЗУ.
    """
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
        
        # Формируем имя файла
        app_number = data["application"].get("number", "UNKNOWN").replace("/", "-")
        cadnum = data["parcel"].get("cadnum", "UNKNOWN").replace(":", "-")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        output_filename = f"GPZU_{cadnum}_{app_number}_{timestamp}.docx"
        output_path = UPLOADS_DIR / output_filename
        
        # Генерация документа
        builder = GPBuilder(str(TEMPLATE_PATH))
        result_path = builder.generate(data, str(output_path))
        
        logger.info(f"Градплан успешно сформирован: {result_path}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Градостроительный план успешно сформирован",
            "filename": output_filename,
            "download_url": f"/api/gp/gradplan/download/{output_filename}"
        })
        
    except Exception as e:
        logger.error(f"Ошибка генерации градплана: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_gradplan(filename: str):
    """
    Скачивание сгенерированного градплана.
    ИСПРАВЛЕНО: добавлен правильный Content-Disposition заголовок
    """
    file_path = UPLOADS_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # ИСПРАВЛЕНИЕ: добавляем правильные заголовки
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
    """
    Пространственный анализ участка по координатам из ЕГРН.
    
    Определяет:
    - Территориальную зону
    - Объекты капитального строительства
    - ЗОУИТ
    - Документацию по планировке
    
    Входные данные:
    {
        "cadnum": "42:30:0305010:128",
        "coordinates": [
            {"num": "1", "x": "2199600.00", "y": "438100.00"},
            ...
        ]
    }
    """
    try:
        data = await request.json()
        cadnum = data.get("cadnum")
        coordinates = data.get("coordinates", [])
        
        if not cadnum:
            raise HTTPException(status_code=400, detail="Не указан кадастровый номер")
        
        if not coordinates:
            raise HTTPException(status_code=400, detail="Не указаны координаты участка")
        
        logger.info(f"Пространственный анализ для КН: {cadnum}")
        
        # Создаём минимальный объект GPData для анализа
        # coordinates уже в формате списка словарей [{"num": "1", "x": "...", "y": "..."}]
        gp_data = GPData()
        gp_data.parcel = ParcelInfo(
            cadnum=cadnum,
            address="",
            area="",
            coordinates=coordinates  # Передаём как есть - список словарей
        )
        
        # Выполняем пространственный анализ
        gp_data = perform_spatial_analysis(gp_data)
        
        # Формируем ответ
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
    """
    Проверка здоровья API градплана.
    """
    return JSONResponse(content={"status": "ok", "service": "gradplan"})
