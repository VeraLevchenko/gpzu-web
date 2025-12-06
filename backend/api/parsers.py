"""
Общий API для парсеров.

Все модули (Kaiten, MidMif, TU, ГПЗУ) используют эти endpoints
вместо дублирования кода парсинга.

ОБНОВЛЕНО: добавлена передача площадей ЗОУИТ в API ответе
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from fastapi.responses import JSONResponse
import logging
from datetime import date

from parsers.application_parser import parse_application_docx
from parsers.egrn_parser import parse_egrn_xml
from models.gp_data import GPData, ParcelInfo
from utils.spatial_analysis import perform_spatial_analysis
from utils.coords import renumber_egrn_contours


router = APIRouter(prefix="/api/parsers", tags=["parsers"])
logger = logging.getLogger("gpzu-web.parsers")


@router.post("/application")
async def parse_application(file: UploadFile = File(...)):
    """
    Парсинг заявления из DOCX файла.
    
    Используется модулями: Kaiten, TU, ГПЗУ
    """
    try:
        if not file.filename.endswith('.docx'):
            raise HTTPException(status_code=400, detail="Поддерживается только формат DOCX")
        
        content = await file.read()
        logger.info(f"Парсинг заявления: {file.filename} ({len(content)} байт)")
        
        # parse_application_docx возвращает объект ApplicationData
        app_data = parse_application_docx(content)
        
        # Преобразуем в словарь с конвертацией date в строку
        result = {
            "number": app_data.number,
            "date": app_data.date.strftime('%Y-%m-%d') if isinstance(app_data.date, date) else str(app_data.date) if app_data.date else None,
            "date_text": app_data.date_text,
            "applicant": app_data.applicant,
            "cadnum": app_data.cadnum,
            "purpose": app_data.purpose,
            "service_date": app_data.service_date.strftime('%Y-%m-%d') if isinstance(app_data.service_date, date) else str(app_data.service_date) if app_data.service_date else None
        }
        
        logger.info(f"Заявление распарсено: №{result.get('number')}, КН={result.get('cadnum')}")
        
        return JSONResponse(content={
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Ошибка парсинга заявления: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/egrn")
async def parse_egrn(file: UploadFile = File(...)):
    """
    Парсинг выписки ЕГРН из XML файла.
    
    Используется модулями: MidMif, TU, ГПЗУ
    """
    try:
        if not file.filename.endswith('.xml'):
            raise HTTPException(status_code=400, detail="Поддерживается только формат XML")
        
        content = await file.read()
        logger.info(f"Парсинг ЕГРН: {file.filename} ({len(content)} байт)")
        
        # parse_egrn_xml возвращает объект EGRNData
        egrn_data = parse_egrn_xml(content)
        
        # Нумерация точек как для MID/MIF (общая функция)
        # contours: List[List[Coord]]
        numbered_contours = renumber_egrn_contours(egrn_data.contours)
        flat_coords = [pt for contour in numbered_contours for pt in contour]
        
        # Преобразуем в словарь
        result = {
            "cadnum": egrn_data.cadnum,
            "address": egrn_data.address,
            "area": egrn_data.area,
            "region": egrn_data.region,
            "municipality": egrn_data.municipality,
            "settlement": egrn_data.settlement,
            "permitted_use": egrn_data.permitted_use,
            "coordinates": [
                {
                    "num": coord.num,
                    "x": coord.x,
                    "y": coord.y
                }
                for coord in flat_coords
            ]
        }
        
        logger.info(
            f"ЕГРН распарсен: КН={result.get('cadnum')}, "
            f"точек={len(result.get('coordinates', []))}"
        )
        
        return JSONResponse(content={
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Ошибка парсинга ЕГРН: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spatial")
async def spatial_analysis(request: Request):
    """
    Пространственный анализ участка.
    
    Используется модулями: ГПЗУ (автоматически), остальные по запросу
    ОБНОВЛЕНО: возвращает площади ЗОУИТ
    """
    try:
        data = await request.json()
        cadnum = data.get("cadnum")
        coordinates = data.get("coordinates", [])
        
        if not cadnum:
            raise HTTPException(status_code=400, detail="Не указан кадастровый номер")
        
        if not coordinates:
            raise HTTPException(status_code=400, detail="Не указаны координаты")
        
        logger.info(f"Пространственный анализ: КН={cadnum}, точек={len(coordinates)}")
        
        # Создаём GPData для анализа
        gp_data = GPData()
        gp_data.parcel = ParcelInfo(
            cadnum=cadnum,
            address="",
            area="",
            coordinates=coordinates
        )
        
        # Выполняем анализ
        gp_data = perform_spatial_analysis(gp_data)
        
        # Формируем ответ
        result = {
            "zone": {
                "code": gp_data.zone.code if gp_data.zone else "",
                "name": gp_data.zone.name if gp_data.zone else ""
            } if gp_data.zone else None,
            
            "district": {
                "code": gp_data.district.code if gp_data.district else "",
                "name": gp_data.district.name if gp_data.district else ""
            } if gp_data.district else None,
            
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
            
            # 🔥 ОБНОВЛЕНО: Добавлено поле "area" для каждой ЗОУИТ
            "zouit": [
                {
                    "name": z.name,
                    "registry_number": z.registry_number,
                    "restrictions": z.restrictions,
                    "area": z.area_sqm,   # ← полностью как было, float без округления
                }
                for z in gp_data.zouit
            ],
            
            "planning_project": {
                "exists": gp_data.planning_project.exists if gp_data.planning_project else False,
                "decision_full": gp_data.planning_project.decision_full if gp_data.planning_project else "Документация по планировке территории не утверждена",
                "project_type": gp_data.planning_project.project_type if gp_data.planning_project else None,
                "project_name": gp_data.planning_project.project_name if gp_data.planning_project else None,
            } if gp_data.planning_project else {
                "exists": False,
                "decision_full": "Документация по планировке территории не утверждена"
            },
            
            "warnings": gp_data.warnings,
            "errors": gp_data.errors
        }
        
        # Подсчёт ЗОУИТ с площадями для логирования
        zouit_with_areas = sum(1 for z in gp_data.zouit if z.area_sqm is not None and z.area_sqm > 0)
        
        logger.info(
            f"Анализ выполнен: зона={result.get('zone')}, район={result.get('district')}, "
            f"ОКС={len(result['capital_objects'])}, ЗОУИТ={len(result['zouit'])} "
            f"(с площадями: {zouit_with_areas})"
        )
        
        return JSONResponse(content={
            "success": True,
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Ошибка пространственного анализа: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def parsers_health():
    """Проверка работоспособности парсеров"""
    return JSONResponse(content={
        "status": "ok",
        "service": "parsers",
        "available": ["application", "egrn", "spatial"]
    })
