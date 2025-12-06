# backend/api/gp/midmif.py
"""
API endpoints для генерации MID/MIF файлов из выписки ЕГРН.
ИСПРАВЛЕННАЯ ВЕРСИЯ - координаты X и Y поменяны местами
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import List, Tuple
import logging
import io
import zipfile

from parsers.egrn_parser import parse_egrn_xml, EGRNData, Coord as ECoord
from generator.midmif_builder import build_mid_mif_from_contours
from utils.coords import renumber_egrn_contours

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/midmif", tags=["midmif"])


@router.post("/preview")
async def preview_coordinates(file: UploadFile = File(...)):
    """
    Предпросмотр координат из выписки ЕГРН.
    
    ИСПРАВЛЕНО: Координаты X и Y поменяны местами
    - X теперь = восток (исходный Y из ЕГРН)
    - Y теперь = север (исходный X из ЕГРН)
    
    Args:
        file: XML или ZIP файл выписки ЕГРН
    
    Returns:
        JSON с координатами в формате X=восток, Y=север
    """
    
    # Проверка формата файла
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
        logger.info(f"Получен файл ЕГРН: {file.filename} ({len(content)} байт)")
        
        # Парсим ЕГРН
        egrn: EGRNData = parse_egrn_xml(content)
        logger.info(f"Выписка распарсена: КН={egrn.cadnum}")
        
        # Проверяем, что это земельный участок
        if not egrn.is_land:
            raise HTTPException(
                status_code=400,
                detail="Это не выписка ЕГРН по земельному участку"
            )
        
        # Проверяем наличие контуров
        if not egrn.contours:
            raise HTTPException(
                status_code=400,
                detail="В выписке ЕГРН отсутствуют координаты границ участка"
            )
        
        # Пересчитываем нумерацию точек
        numbered_contours = renumber_egrn_contours(egrn.contours)
        
        # Собираем все точки
        all_points = [
            pt for cnt in numbered_contours for pt in cnt
        ]
        
        # ИСПРАВЛЕНО: Формируем ответ с поменянными местами координатами
        # В парсере ЕГРН: x = север (из <y> XML), y = восток (из <x> XML)
        # Теперь возвращаем: x = восток, y = север
        coordinates = []
        for pt in all_points:
            coordinates.append({
                "num": pt.num,
                "x": pt.y,  # X = восток (исходный Y из парсера)
                "y": pt.x   # Y = север (исходный X из парсера)
            })
        
        logger.info(f"Координаты подготовлены (X=восток, Y=север): {len(coordinates)} точек")
        
        return {
            "success": True,
            "cadnum": egrn.cadnum or "—",
            "total_points": len(all_points),
            "coordinates": coordinates,
            "note": "Координаты в порядке X (восток), Y (север) — формат для MapInfo"
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Ошибка предпросмотра: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(ex)}"
        )


@router.post("/generate")
async def generate_midmif(file: UploadFile = File(...)):
    """
    Генерация MID/MIF файлов из выписки ЕГРН.
    
    ИСПРАВЛЕНО: Координаты в файлах MID/MIF будут в формате X=восток, Y=север
    
    Args:
        file: XML или ZIP файл выписки ЕГРН
    
    Returns:
        StreamingResponse с ZIP архивом
    """
    
    # Проверка формата файла
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
        logger.info(f"Получен файл ЕГРН: {file.filename} ({len(content)} байт)")
        
        # Парсим ЕГРН
        egrn: EGRNData = parse_egrn_xml(content)
        logger.info(f"Выписка распарсена: КН={egrn.cadnum}")
        
        # Проверяем, что это земельный участок
        if not egrn.is_land:
            raise HTTPException(
                status_code=400,
                detail="Это не выписка ЕГРН по земельному участку"
            )
        
        # Проверяем наличие контуров
        if not egrn.contours:
            raise HTTPException(
                status_code=400,
                detail="В выписке ЕГРН отсутствуют координаты границ участка"
            )
        
        # Пересчитываем нумерацию точек
        numbered_contours = renumber_egrn_contours(egrn.contours)
        
        # ИСПРАВЛЕНО: Формируем структуру для генератора с поменянными координатами
        # В парсере ЕГРН: pt.x = север, pt.y = восток
        # Для MID/MIF нужно: X = восток, Y = север
        contours_for_builder: List[List[Tuple[str, str, str]]] = []
        for cnt in numbered_contours:
            contours_for_builder.append([
                (c.num, c.y, c.x) for c in cnt  # ИСПРАВЛЕНО: поменяли местами c.x и c.y
            ])
        
        logger.info("Координаты для MID/MIF подготовлены (X=восток, Y=север)")
        
        # Генерируем MID/MIF
        base_name, mif_bytes, mid_bytes = build_mid_mif_from_contours(
            egrn.cadnum,
            contours_for_builder
        )
        
        logger.info(f"MID/MIF сгенерированы для {egrn.cadnum}")
        
        # Создаём ZIP архив в памяти
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(f"{base_name}.mif", mif_bytes)
            zip_file.writestr(f"{base_name}.mid", mid_bytes)
        
        zip_buffer.seek(0)
        
        # Возвращаем ZIP архив
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={base_name}.zip"
            }
        )
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Ошибка генерации MID/MIF: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(ex)}"
        )