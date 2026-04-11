# backend/generator/spatial_adapter.py
"""
Адаптер для преобразования результатов пространственного анализа
в модели данных рабочего набора MapInfo.

Использует существующий модуль utils/spatial_analysis.py для поиска
пересечений, но конвертирует результаты в формат для генератора MIF/TAB.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional
import logging

from models.workspace_data import (
    WorkspaceData,
    ParcelLayer,
    BuildingZoneLayer,
    CapitalObjectInfo,
    ZouitInfo,
    AgoInfo,
)
from models.gp_data import GPData, ParcelInfo
from utils.spatial_analysis import perform_spatial_analysis
from generator.geometry_builder import create_building_zone
from parsers.egrn_parser import EGRNData
from utils.coords import renumber_egrn_contours

logger = logging.getLogger(__name__)


def create_workspace_from_egrn(egrn_data: EGRNData) -> WorkspaceData:
    """
    Создать полный WorkspaceData из выписки ЕГРН с автоматическим
    пространственным анализом.
    
    Workflow:
    1. Парсинг ЕГРН → координаты участка
    2. Пространственный анализ → поиск ОКС, ЗОУИТ
    3. Создание зоны строительства (буфер -5м)
    4. Сборка WorkspaceData для генерации MIF/TAB
    
    Args:
        egrn_data: Распарсенная выписка ЕГРН
    
    Returns:
        WorkspaceData со всеми найденными объектами
    """
    
    logger.info(f"Создание рабочего набора для участка {egrn_data.cadnum}")
    
    # ========== ШАГ 1: Преобразование координат ========== #
    
    coordinates = _convert_egrn_coordinates(egrn_data.coordinates)
    if not coordinates or len(coordinates) < 3:
            raise ValueError(f"Недостаточно координат: {len(coordinates)}")
    
    logger.info(f"Координат участка: {len(coordinates)}")        
    
    
    numbered_contours = renumber_egrn_contours(egrn_data.contours)
    logger.info(f"Контуров с нумерацией: {len(numbered_contours)}")
    
    parcel = ParcelLayer(
        cadnum=egrn_data.cadnum or "Без_номера",
        coordinates=coordinates,
        area=float(egrn_data.area) if egrn_data.area else None,
        address=egrn_data.address,
        numbered_contours=numbered_contours  # ← ДОБАВИТЬ ЭТОТ ПАРАМЕТР
    )
    
        
    logger.info(f"Слой участка создан, площадь: {parcel.geometry.area:.2f} кв.м")
    
    # ========== ШАГ 3: Создание зоны строительства ========== #
    
    building_zone_geom = create_building_zone(coordinates, buffer_distance=-1.0)
    building_zone = BuildingZoneLayer(geometry=building_zone_geom)
    
    logger.info(f"Зона строительства создана, площадь: {building_zone.geometry.area:.2f} кв.м")
    
    # ========== ШАГ 4: Пространственный анализ ========== #
    
    # Создаём GPData для пространственного анализа
    gp_data = GPData()
    gp_data.parcel = ParcelInfo(
        cadnum=egrn_data.cadnum or "Без_номера",
        address=egrn_data.address or "",
        area=str(egrn_data.area) if egrn_data.area else "",
        coordinates=[
            {"num": str(i+1), "x": str(x), "y": str(y)}
            for i, (x, y) in enumerate(coordinates)
        ]
    )
    
    # Выполняем анализ (находит ОКС, ЗОУИТ и т.д.)
    gp_data = perform_spatial_analysis(gp_data)
    
    logger.info(f"Пространственный анализ завершён")
    logger.info(f"  - ОКС найдено: {len(gp_data.capital_objects)}")
    logger.info(f"  - ЗОУИТ найдено: {len(gp_data.zouit)}")
    
    # ========== ШАГ 5: Конвертация ОКС ========== #
    
    capital_objects = _convert_capital_objects(gp_data.capital_objects)
    
    # ========== ШАГ 6: Конвертация ЗОУИТ ========== #

    zouit = _convert_zouit(gp_data.zouit)

    # ========== ШАГ 6-Б: Конвертация АГО ========== #

    ago = _convert_ago(gp_data)

    # ========== ШАГ 7: Сборка WorkspaceData ========== #

    from datetime import datetime

    workspace = WorkspaceData(
        parcel=parcel,
        building_zone=building_zone,
        capital_objects=capital_objects,
        zouit=zouit,
        ago=ago,
        created_at=datetime.now().isoformat()
    )

    logger.info(f"✅ WorkspaceData создан:")
    logger.info(f"   - Участок: {workspace.parcel.cadnum}")
    logger.info(f"   - ОКС: {len(workspace.capital_objects)}")
    logger.info(f"   - ЗОУИТ: {len(workspace.zouit)}")
    logger.info(f"   - АГО: {ago.index if ago else 'нет'}")
    
    return workspace


def _convert_egrn_coordinates(
    egrn_coords: List[any]
) -> List[Tuple[float, float]]:
    """
    Преобразовать координаты из ЕГРН в формат [(x, y), ...].
    
    Args:
        egrn_coords: Список объектов Coordinate из парсера ЕГРН
    
    Returns:
        Список кортежей (x, y)
    """
    
    coordinates = []
    
    for coord in egrn_coords:
        try:
            # Координаты из ЕГРН могут содержать запятые
            x_str = str(coord.x).replace(',', '.').replace(' ', '')
            y_str = str(coord.y).replace(',', '.').replace(' ', '')
            
            x = float(x_str)
            y = float(y_str)
            
            coordinates.append((x, y))
            
        except (ValueError, AttributeError) as e:
            logger.warning(f"Пропуск некорректной координаты: {e}")
            continue
    
    return coordinates


def _convert_capital_objects(
    gp_capital_objects: List[any]
) -> List[CapitalObjectInfo]:
    """
    Конвертировать ОКС из GPData.capital_objects в CapitalObjectInfo.
    
    Args:
        gp_capital_objects: Список CapitalObject из gp_data
    
    Returns:
        Список CapitalObjectInfo для рабочего набора
    """
    
    result = []
    
    for obj in gp_capital_objects:
        # Извлекаем геометрию если есть
        geometry = getattr(obj, 'geometry', None)
        
        capital_obj = CapitalObjectInfo(
            cadnum=getattr(obj, 'cadnum', None),
            object_type=getattr(obj, 'object_type', None),
            purpose=getattr(obj, 'purpose', None),
            area=getattr(obj, 'area_sqm', None),
            floors=getattr(obj, 'floors', None),
            geometry=geometry
        )
        
        result.append(capital_obj)
        
        logger.debug(
            f"ОКС: {capital_obj.cadnum or 'б/н'} - "
            f"{capital_obj.object_type} ({capital_obj.purpose}), "
            f"площадь: {capital_obj.area or 'н/д'} кв.м"
        )
    
    return result


def _convert_zouit(
    gp_zouit: List[any]
) -> List[ZouitInfo]:
    """
    Конвертировать ЗОУИТ из GPData.zouit в ZouitInfo.
    
    После патча spatial_analysis.py объект RestrictionZone уже содержит
    геометрию пересечения в поле geometry.
    
    Args:
        gp_zouit: Список RestrictionZone из gp_data
    
    Returns:
        Список ZouitInfo для рабочего набора
    """
    
    result = []
    
    for zone in gp_zouit:
        # Извлекаем геометрию (после патча она уже есть в RestrictionZone)
        geometry = getattr(zone, 'geometry', None)
        
        # ✅ ОБНОВЛЕНО: Добавлено получение реестрового номера
        registry_number = getattr(zone, 'registry_number', None)
        
        zouit_obj = ZouitInfo(
            name=getattr(zone, 'name', None),
            type=getattr(zone, 'zone_type', None),
            registry_number=registry_number,  # ✅ ДОБАВЛЕНО
            restriction=_format_restriction(zone),
            geometry=geometry
        )
        
        result.append(zouit_obj)
        
        logger.debug(
            f"ЗОУИТ: {zouit_obj.name} ({zouit_obj.type}) - "
            f"реестр: {registry_number or 'нет'} - "
            f"геометрия: {'✅' if geometry else '❌'}"
        )
    
    return result


def _convert_ago(gp_data: GPData) -> Optional[AgoInfo]:
    """
    Конвертировать данные АГО из GPData в AgoInfo для рабочего набора.
    """
    ago_index = getattr(gp_data, 'ago_index', None)
    if not ago_index:
        return None

    geometry = getattr(gp_data, 'ago_geometry', None)
    if geometry is None:
        logger.warning(f"АГО {ago_index}: индекс найден, но геометрия отсутствует — слой не создаётся")
        return None

    logger.debug(f"АГО: {ago_index} — геометрия ✅")
    return AgoInfo(index=ago_index, geometry=geometry)


def _format_restriction(zone: any) -> str:
    """
    Сформировать описание ограничения для ЗОУИТ.
    
    Args:
        zone: Объект RestrictionZone
    
    Returns:
        Строка с описанием ограничения
    """
    
    parts = []
    
    # Реестровый номер
    reg_num = getattr(zone, 'registry_number', None)
    if reg_num:
        parts.append(f"Реестровый номер: {reg_num}")
    
    # Решение
    decision_num = getattr(zone, 'decision_number', None)
    decision_date = getattr(zone, 'decision_date', None)
    decision_auth = getattr(zone, 'decision_authority', None)
    
    if decision_num or decision_date:
        decision_parts = []
        if decision_num:
            decision_parts.append(f"№{decision_num}")
        if decision_date:
            decision_parts.append(f"от {decision_date}")
        
        decision_str = " ".join(decision_parts)
        
        if decision_auth:
            parts.append(f"{decision_auth}: {decision_str}")
        else:
            parts.append(f"Решение: {decision_str}")
    
    # Площадь пересечения
    area = getattr(zone, 'area_sqm', None)
    if area is not None and area > 0:
        parts.append(f"Площадь пересечения: {area:.2f} кв.м")
    
    return "; ".join(parts) if parts else "Ограничения использования территории"


# ================ ПРИМЕР ИСПОЛЬЗОВАНИЯ ================ #

if __name__ == "__main__":
    import tempfile
    from parsers.egrn_parser import parse_egrn_xml
    
    print("=" * 60)
    print("ТЕСТ: Создание рабочего набора из ЕГРН")
    print("=" * 60)
    
    # Путь к тестовой выписке ЕГРН
    test_egrn_path = Path("/home/gpzu-web/backend/uploads/магазин лесная 14.xml")
    
    if not test_egrn_path.exists():
        print(f"❌ Тестовый файл не найден: {test_egrn_path}")
        print("Укажите путь к вашей выписке ЕГРН")
        exit(1)
    
    # Парсим ЕГРН
    with open(test_egrn_path, 'rb') as f:
        egrn_data = parse_egrn_xml(f.read())
    
    print(f"\n📄 ЕГРН распарсен:")
    print(f"   Кадастровый номер: {egrn_data.cadnum}")
    print(f"   Площадь: {egrn_data.area} кв.м")
    print(f"   Адрес: {egrn_data.address}")
    print()
    
    # Создаём рабочий набор
    try:
        workspace = create_workspace_from_egrn(egrn_data)
        
        print("\n✅ Рабочий набор создан!")
        print(f"\n📊 Статистика:")
        print(f"   Участок: {workspace.parcel.cadnum}")
        print(f"   Площадь участка: {workspace.parcel.geometry.area:.2f} кв.м")
        print(f"   Площадь зоны строительства: {workspace.building_zone.geometry.area:.2f} кв.м")
        print(f"   ОКС найдено: {len(workspace.capital_objects)}")
        print(f"   ЗОУИТ найдено: {len(workspace.zouit)}")
        
        if workspace.capital_objects:
            print(f"\n📍 ОКС:")
            for oks in workspace.capital_objects:
                print(f"   - {oks.cadnum or 'б/н'}: {oks.object_type} ({oks.purpose})")
        
        if workspace.zouit:
            print(f"\n⚠️  ЗОУИТ:")
            for zone in workspace.zouit:
                print(f"   - {zone.name} ({zone.type})")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)