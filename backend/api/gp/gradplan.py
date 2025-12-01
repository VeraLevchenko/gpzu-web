# backend/api/gp/gradplan.py
"""
API endpoints для подготовки градостроительных планов (ГПЗУ).
"""

import io
import os
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse

from parsers.application_parser import parse_application_docx, ApplicationData
from parsers.egrn_parser import parse_egrn_xml, EGRNData
from models.gp_data import GPData, create_gp_data_from_parsed
from utils.spatial_analysis import perform_spatial_analysis
from generator.gp_builder import GPBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gp/gradplan", tags=["gradplan"])

# Путь к шаблону градплана
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATE_PATH = BASE_DIR / "templates" / "gpzu_template.docx"


# ========================================================================
# ENDPOINT 1: Парсинг заявления
# ========================================================================

@router.post("/parse-application")
async def parse_application_endpoint(file: UploadFile = File(...)):
    """
    Парсинг заявления о выдаче ГПЗУ из DOCX файла.
    
    Извлекает:
    - Номер заявления
    - Дату заявления
    - Заявителя (ФИО или наименование организации)
    - Кадастровый номер земельного участка
    - Цель использования участка
    - Срок оказания услуги (+14 рабочих дней)
    
    Args:
        file: DOCX файл заявления
    
    Returns:
        JSON с данными заявления
    """
    
    # Проверка формата файла
    if not file.filename or not file.filename.lower().endswith('.docx'):
        raise HTTPException(
            status_code=400,
            detail="Файл должен быть в формате DOCX"
        )
    
    try:
        # Читаем файл
        content = await file.read()
        logger.info(f"Получен файл заявления: {file.filename} ({len(content)} байт)")
        
        # Парсим
        app_data: ApplicationData = parse_application_docx(content)
        logger.info(f"Заявление распарсено: заявитель={app_data.applicant}, КН={app_data.cadnum}")
        
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
                "service_date": app_data.service_date.isoformat() if app_data.service_date else None,
            }
        }
        
    except Exception as ex:
        logger.exception(f"Ошибка парсинга заявления: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(ex)}"
        )


# ========================================================================
# ENDPOINT 2: Парсинг выписки ЕГРН
# ========================================================================

@router.post("/parse-egrn")
async def parse_egrn_endpoint(file: UploadFile = File(...)):
    """
    Парсинг выписки из ЕГРН (XML или ZIP).
    
    Извлекает:
    - Кадастровый номер участка
    - Адрес
    - Площадь
    - Вид разрешённого использования (ВРИ)
    - Координаты границ участка
    - Объекты капитального строительства
    
    ВАЖНО: Координаты автоматически преобразуются из формата ЕГРН (X=север, Y=восток)
    в формат для пространственного анализа (x=восток, y=север).
    
    Args:
        file: XML или ZIP файл выписки ЕГРН
    
    Returns:
        JSON с данными участка
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
        
        # Парсим
        egrn: EGRNData = parse_egrn_xml(content)
        logger.info(f"Выписка распарсена: КН={egrn.cadnum}, адрес={egrn.address}")
        
        # Проверяем, что это земельный участок
        if not egrn.is_land:
            raise HTTPException(
                status_code=400,
                detail="Это не выписка ЕГРН по земельному участку"
            )
        
        # Преобразуем координаты для JSON
        # КРИТИЧНО: Меняем X↔Y для совместимости со слоями
        coords_dicts = []
        for c in egrn.coordinates:
            coords_dicts.append({
                'num': c.num,
                'x': c.y,  # Y из ЕГРН (восток) → x в JSON
                'y': c.x   # X из ЕГРН (север) → y в JSON
            })
        
        # Формируем ответ
        return {
            "success": True,
            "data": {
                "cadnum": egrn.cadnum,
                "address": egrn.address,
                "area": egrn.area,
                "region": egrn.region,
                "municipality": egrn.municipality,
                "settlement": egrn.settlement,
                "permitted_use": egrn.permitted_use,
                "coordinates": coords_dicts,
                "capital_objects_egrn": egrn.capital_objects,
            }
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Ошибка парсинга ЕГРН: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка обработки файла: {str(ex)}"
        )


# ========================================================================
# ENDPOINT 3: Пространственный анализ
# ========================================================================

@router.post("/analyze")
async def analyze_endpoint(data: Dict[str, Any]):
    """
    Выполнение пространственного анализа земельного участка.
    
    Анализ включает:
    1. Определение территориальной зоны
    2. Поиск объектов капитального строительства
    3. Проверка проектов планировки территории
    4. Поиск зон с особыми условиями (ЗОУИТ)
    5. Проверка объектов культурного наследия (ОКН)
    
    Принимает:
    - application: данные заявления (из parse-application)
    - egrn: данные ЕГРН (из parse-egrn)
    
    Возвращает:
    - Полные данные GPData с результатами анализа
    - warnings: предупреждения (например, о множественных зонах)
    - errors: критические ошибки
    
    Args:
        data: JSON с полями application и egrn
    
    Returns:
        JSON с результатами анализа
    """
    
    try:
        logger.info("Начало пространственного анализа")
        
        # Проверяем наличие данных
        if 'application' not in data or 'egrn' not in data:
            raise HTTPException(
                status_code=400,
                detail="Необходимо передать данные заявления (application) и ЕГРН (egrn)"
            )
        
        application_dict = data['application']
        egrn_dict = data['egrn']
        
        # Проверяем наличие координат
        if not egrn_dict.get('coordinates'):
            raise HTTPException(
                status_code=400,
                detail="В данных ЕГРН отсутствуют координаты участка"
            )
        
        logger.info(
            f"Анализ для участка: КН={egrn_dict.get('cadnum')}, "
            f"координат={len(egrn_dict.get('coordinates', []))}"
        )
        
        # Создаём объект GPData
        gp_data = create_gp_data_from_parsed(application_dict, egrn_dict)
        
        # Выполняем пространственный анализ
        gp_data = perform_spatial_analysis(gp_data)
        
        logger.info("Пространственный анализ завершён успешно")
        
        # Формируем ответ
        # ВАЖНО: Используем to_dict() для исключения внутренних полей
        result_data = gp_data.to_dict()
        
        # Добавляем warnings и errors отдельно (они нужны пользователю, но не в to_dict)
        return {
            "success": True,
            "data": result_data,
            "warnings": gp_data.warnings,
            "errors": gp_data.errors,
        }
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Ошибка при анализе: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка пространственного анализа: {str(ex)}"
        )


# ========================================================================
# ENDPOINT 4: Генерация документа ГПЗУ
# ========================================================================

@router.post("/generate")
async def generate_gp_endpoint(data: Dict[str, Any]):
    """
    Генерация документа градостроительного плана (ГПЗУ).
    
    Принимает:
    - Полные данные GPData (application, parcel, zone, zouit, и т.д.)
    
    Возвращает:
    - DOCX файл с готовым градпланом
    
    Процесс:
    1. Валидация входных данных
    2. Создание объекта GPBuilder
    3. Генерация документа с вставкой блоков зон и ЗОУИТ
    4. Возврат файла для скачивания
    """
    
    try:
        logger.info("Начало генерации документа ГПЗУ")
        
        # ===== ВАЛИДАЦИЯ ДАННЫХ ===== #
        
        # Проверяем наличие основных секций
        if 'parcel' not in data or not data['parcel']:
            raise HTTPException(
                status_code=400,
                detail="Отсутствуют данные о земельном участке (parcel)"
            )
        
        if 'zone' not in data or not data['zone']:
            raise HTTPException(
                status_code=400,
                detail="Отсутствуют данные о территориальной зоне (zone)"
            )
        
        parcel = data['parcel']
        zone = data['zone']
        
        # Проверяем обязательные поля участка
        if not parcel.get('cadnum'):
            raise HTTPException(
                status_code=400,
                detail="Не указан кадастровый номер участка"
            )
        
        # Проверяем код зоны (критично для подбора блоков)
        if not zone.get('code'):
            raise HTTPException(
                status_code=400,
                detail="Не указан код территориальной зоны"
            )
        
        logger.info(f"Генерация ГПЗУ для участка {parcel['cadnum']}, зона {zone['code']}")
        
        # ===== ПОДГОТОВКА ДАННЫХ ===== #
        
        # Убираем внутренние поля из зоны (если они есть)
        zone_clean = dict(zone)
        zone_clean.pop('_multiple_zones', None)
        zone_clean.pop('_all_zones', None)
        zone_clean.pop('_overlap_percent', None)
        data['zone'] = zone_clean
        
        # ===== ГЕНЕРАЦИЯ ДОКУМЕНТА ===== #
        
        # Путь к шаблону
        template_path = TEMPLATE_PATH
        
        if not template_path.exists():
            logger.error(f"Шаблон не найден: {template_path}")
            raise HTTPException(
                status_code=500,
                detail=f"Шаблон градплана не найден: {template_path.name}"
            )
        
        # Создаём генератор
        builder = GPBuilder(str(template_path))
        
        # Создаём временный файл для результата
        output_fd, output_path = tempfile.mkstemp(suffix='.docx', prefix='gpzu_')
        os.close(output_fd)  # Закрываем файловый дескриптор
        
        try:
            # Генерируем документ
            result_path = builder.generate(data, output_path)
            
            logger.info(f"Документ ГПЗУ успешно сгенерирован: {result_path}")
            
            # Читаем файл
            with open(result_path, 'rb') as f:
                docx_bytes = f.read()
            
            # Формируем имя файла для скачивания
            cadnum = parcel['cadnum'].replace(':', '_')
            filename = f"GPZU_{cadnum}.docx"
            
            # Возвращаем файл
            return StreamingResponse(
                io.BytesIO(docx_bytes),
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f"attachment; filename={filename}"
                }
            )
            
        finally:
            # Удаляем временный файл
            try:
                if os.path.exists(output_path):
                    os.remove(output_path)
            except Exception as e:
                logger.warning(f"Не удалось удалить временный файл: {e}")
        
    except HTTPException:
        raise
    except Exception as ex:
        logger.exception(f"Ошибка генерации ГПЗУ: {ex}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка генерации документа: {str(ex)}"
        )