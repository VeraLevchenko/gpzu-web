# utils/spatial_analysis.py
"""
Модуль пространственного анализа земельного участка.
ПОЛНАЯ ВЕРСИЯ С РАСЧЁТОМ ПЛОЩАДЕЙ ЗОУИТ
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any

# Импорт Shapely для расчёта площадей
try:
    from shapely.geometry import Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

from models.gp_data import (
    GPData,
    TerritorialZoneInfo,
    DistrictInfo,
    CapitalObject,
    PlanningProject,
    RestrictionZone,
)
from core.layers_config import LayerPaths
from parsers.tab_parser import (
    parse_zones_layer,
    parse_districts_layer,
    find_zone_for_parcel,
    find_district_for_parcel,
    parse_capital_objects_layer,
    find_objects_on_parcel,
    parse_planning_projects_layer,
    check_planning_project_intersection,
    parse_zouit_layer_extended,
    find_restrictions_for_parcel,
)

logger = logging.getLogger("gpzu-bot.spatial_analysis")


def perform_spatial_analysis(gp_data: GPData) -> GPData:
    """Выполнить комплексный пространственный анализ участка"""
    logger.info(f"Начало пространственного анализа для участка {gp_data.parcel.cadnum}")
    
    coords = _get_parcel_coords(gp_data)
    if not coords:
        gp_data.add_error("Отсутствуют координаты участка")
        logger.error("Нет координат участка для анализа")
        return gp_data
    
    logger.info("Этап 1/6: Определение района города")
    _analyze_district(gp_data, coords)
    
    logger.info("Этап 2/6: Определение территориальной зоны")
    _analyze_zone(gp_data, coords)
    
    logger.info("Этап 3/6: Поиск объектов капстроительства")
    _analyze_capital_objects(gp_data, coords)
    
    logger.info("Этап 4/6: Проверка проектов планировки")
    _analyze_planning_projects(gp_data, coords)
    
    logger.info("Этап 5/6: Проверка ЗОУИТ с расчётом площадей")
    _analyze_zouit(gp_data, coords)
    
    logger.info("Этап 6/6: Проверка прочих ограничений")
    _analyze_other_restrictions(gp_data, coords)

    gp_data.analysis_completed = True
    logger.info("Пространственный анализ завершён успешно")
    
    return gp_data


def _get_parcel_coords(gp_data: GPData) -> List[Tuple[float, float]]:
    """
    Извлечь координаты участка для пространственного анализа.
    
    Returns:
        List[(север, восток)] - координаты для Shapely
    """
    coords_list = gp_data.parcel.coordinates
    if not coords_list:
        return []
    
    result = []
    for coord in coords_list:
        try:
            x_str = coord.get('x', '')
            y_str = coord.get('y', '')
            
            x_val = float(x_str.replace(',', '.').replace(' ', ''))
            y_val = float(y_str.replace(',', '.').replace(' ', ''))
            
            result.append((x_val, y_val))
            
        except (ValueError, AttributeError, KeyError) as ex:
            logger.warning(f"Ошибка парсинга координаты: {ex}")
            continue
    
    if result:
        logger.info(f"Извлечено {len(result)} координат для анализа")
        if len(result) > 0:
            min_x = min(c[0] for c in result)
            max_x = max(c[0] for c in result)
            min_y = min(c[1] for c in result)
            max_y = max(c[1] for c in result)
            logger.info(f"Границы участка: X({min_x:.2f}..{max_x:.2f}), Y({min_y:.2f}..{max_y:.2f})")
    
    return result


def _analyze_district(gp_data: GPData, coords: List[Tuple[float, float]]):
    """Определить район города для участка."""
    if not LayerPaths.DISTRICTS.exists():
        msg = f"Слой районов не найден: {LayerPaths.DISTRICTS}"
        logger.warning(msg)
        gp_data.add_warning(msg)
        gp_data.district = DistrictInfo()
        return
    
    try:
        districts = parse_districts_layer(LayerPaths.DISTRICTS)
        if not districts:
            logger.warning("Слой районов пуст")
            gp_data.add_warning("Слой районов не содержит данных")
            gp_data.district = DistrictInfo()
            return
        
        district_info = find_district_for_parcel(coords, districts)
        if district_info:
            gp_data.district = DistrictInfo(
                name=district_info.get('name'),
                code=district_info.get('code'),
            )
            logger.info(f"Район определён: {district_info.get('code')} {district_info.get('name')}")
            
            gp_data.parcel.district = gp_data.district.name
        else:
            logger.warning("Не удалось определить район участка")
            gp_data.add_warning("Район города не определён")
            gp_data.district = DistrictInfo()
            
    except Exception as ex:
        msg = f"Ошибка при определении района: {ex}"
        logger.exception(msg)
        gp_data.add_error(msg)
        gp_data.district = DistrictInfo()


def _analyze_zone(gp_data: GPData, coords: List[Tuple[float, float]]):
    """Определить территориальную зону участка"""
    if not LayerPaths.ZONES.exists():
        msg = f"Слой зон не найден: {LayerPaths.ZONES}"
        logger.warning(msg)
        gp_data.add_warning(msg)
        return
    
    try:
        zones = parse_zones_layer(LayerPaths.ZONES)
        if not zones:
            logger.warning("Слой зон пуст")
            gp_data.add_warning("Слой территориальных зон не содержит данных")
            return
        
        zone_info = find_zone_for_parcel(coords, zones)
        if zone_info:
            zone = TerritorialZoneInfo(
                name=zone_info.get('name'),
                code=zone_info.get('code'),
            )
            
            zone.multiple_zones = zone_info.get('multiple_zones', False)
            zone.all_zones = zone_info.get('all_zones', [])
            zone.overlap_percent = zone_info.get('overlap_percent')
            
            gp_data.zone = zone
            
            if zone_info.get('multiple_zones'):
                all_zones_list = zone_info.get('all_zones', [])
                zones_text = ", ".join([
                    f"{z['code']} ({z['overlap_percent']:.1f}%)"
                    for z in all_zones_list
                ])
                warning_msg = (
                    f"⚠️ Участок пересекается с несколькими территориальными зонами: {zones_text}. "
                    f"Выбрана зона с максимальным перекрытием: {zone_info.get('code')} "
                    f"({zone_info.get('overlap_percent'):.1f}%)"
                )
                gp_data.add_warning(warning_msg)
                logger.warning(warning_msg)
            
            logger.info(f"Зона определена: {zone_info.get('code')} {zone_info.get('name')}")
        else:
            logger.warning("Не удалось определить зону участка")
            gp_data.add_warning("Территориальная зона не определена")
            
    except Exception as ex:
        msg = f"Ошибка при определении зоны: {ex}"
        logger.exception(msg)
        gp_data.add_error(msg)


def _analyze_capital_objects(gp_data: GPData, coords: List[Tuple[float, float]]):
    """Найти объекты капстроительства на участке"""
    if not LayerPaths.CAPITAL_OBJECTS.exists():
        msg = f"Слой объектов не найден: {LayerPaths.CAPITAL_OBJECTS}"
        logger.warning(msg)
        gp_data.add_warning(msg)
        return
    
    try:
        objects = parse_capital_objects_layer(LayerPaths.CAPITAL_OBJECTS)
        if not objects:
            logger.info("Слой объектов пуст")
            return
        
        found = find_objects_on_parcel(coords, objects)
        for obj_dict in found:
            cap_obj = CapitalObject(
                cadnum=obj_dict.get('cadnum'),
                object_type=obj_dict.get('object_type'),
                purpose=obj_dict.get('purpose'),
                area=obj_dict.get('area'),
                floors=obj_dict.get('floors'),
                geometry=obj_dict.get('geometry'),  # ✅ ПОЛНАЯ геометрия ОКС из слоя
            )
            gp_data.capital_objects.append(cap_obj)
        
        if found:
            logger.info(f"Найдено объектов на участке: {len(found)}")
        else:
            logger.info("Объекты капстроительства на участке отсутствуют")
            
    except Exception as ex:
        msg = f"Ошибка при поиске объектов: {ex}"
        logger.exception(msg)
        gp_data.add_error(msg)


def _analyze_planning_projects(gp_data: GPData, coords: List[Tuple[float, float]]):
    """Проверить попадание в проект планировки"""
    if not LayerPaths.PLANNING_PROJECTS.exists():
        msg = f"Слой ППТ не найден: {LayerPaths.PLANNING_PROJECTS}"
        logger.warning(msg)
        gp_data.add_warning(msg)
        gp_data.planning_project = PlanningProject(exists=False)
        gp_data.planning_project.decision_full = gp_data.planning_project.get_formatted_description()
        return
    
    try:
        projects = parse_planning_projects_layer(LayerPaths.PLANNING_PROJECTS)
        if not projects:
            logger.info("Слой проектов планировки пуст")
            gp_data.planning_project = PlanningProject(exists=False)
            gp_data.planning_project.decision_full = gp_data.planning_project.get_formatted_description()
            return
        
        project_info = check_planning_project_intersection(coords, projects)
        if project_info:
            planning_project = PlanningProject(
                exists=True,
                project_type=project_info.get('project_type'),
                project_name=project_info.get('project_name'),
                decision_number=project_info.get('decision_number'),
                decision_date=project_info.get('decision_date'),
                decision_authority=project_info.get('decision_authority'),
            )
            planning_project.decision_full = planning_project.get_formatted_description()
            gp_data.planning_project = planning_project
            
            logger.info(
                f"Участок входит в границы ППТ: {project_info.get('project_type')} "
                f'"{project_info.get("project_name")}"'
            )
        else:
            gp_data.planning_project = PlanningProject(exists=False)
            gp_data.planning_project.decision_full = gp_data.planning_project.get_formatted_description()
            logger.info("Участок не входит в границы ППТ")
            
    except Exception as ex:
        msg = f"Ошибка при проверке ППТ: {ex}"
        logger.exception(msg)
        gp_data.add_error(msg)
        gp_data.planning_project = PlanningProject(exists=False)
        gp_data.planning_project.decision_full = gp_data.planning_project.get_formatted_description()


def _analyze_zouit(gp_data: GPData, coords: List[Tuple[float, float]]):
    """
    ПОЛНАЯ ВЕРСИЯ: Проверить наличие ЗОУИТ с реальным расчётом площади пересечения
    """
    if not LayerPaths.ZOUIT.exists():
        logger.debug(f"Слой ЗОУИТ не найден: {LayerPaths.ZOUIT}")
        return
    
    try:
        # Парсим слой ЗОУИТ с геометрией
        restrictions = parse_zouit_layer_extended(LayerPaths.ZOUIT, "ЗОУИТ")
        
        if not restrictions:
            logger.info("Слой ЗОУИТ пуст или не содержит данных")
            return
        
        logger.info(f"Загружено {len(restrictions)} ЗОУИТ из слоя для проверки")
        
        # Проверяем можем ли мы посчитать площадь
        if len(coords) < 3:
            logger.warning("Недостаточно координат для расчёта площади пересечения с ЗОУИТ")
            # Используем старый метод без площади
            found = find_restrictions_for_parcel(coords, restrictions)
            for restr_dict in found:
                restriction = RestrictionZone(
                    zone_type=restr_dict.get('zone_type', "ЗОУИТ"),
                    name=restr_dict.get('name'),
                    registry_number=restr_dict.get('registry_number'),
                    decision_number=restr_dict.get('decision_number'),
                    decision_date=restr_dict.get('decision_date'),
                    decision_authority=restr_dict.get('decision_authority'),
                    area_sqm=None  # Не смогли посчитать площадь
                )
                gp_data.zouit.append(restriction)
            
            if found:
                logger.info(f"Найдено ЗОУИТ: {len(found)} (без расчёта площади)")
            return
        
        # Проверяем доступность Shapely
        if not SHAPELY_AVAILABLE:
            logger.warning("Shapely не доступен. Расчёт площади недоступен. Используется старый метод.")
            # Используем старый метод
            found = find_restrictions_for_parcel(coords, restrictions)
            for restr_dict in found:
                restriction = RestrictionZone(
                    zone_type=restr_dict.get('zone_type', "ЗОУИТ"),
                    name=restr_dict.get('name'),
                    registry_number=restr_dict.get('registry_number'),
                    decision_number=restr_dict.get('decision_number'),
                    decision_date=restr_dict.get('decision_date'),
                    decision_authority=restr_dict.get('decision_authority'),
                    area_sqm=None
                )
                gp_data.zouit.append(restriction)
            
            if found:
                logger.info(f"Найдено ЗОУИТ: {len(found)} (без расчёта площади)")
            return
        
        # === НОВОЕ: ПОЛНОЦЕННЫЙ РАСЧЁТ ПЛОЩАДЕЙ === #
        
        # Создаём полигон участка
        try:
            parcel_polygon = Polygon(coords)
            if not parcel_polygon.is_valid:
                logger.warning("Полигон участка некорректен, пытаемся исправить")
                parcel_polygon = parcel_polygon.buffer(0)  # Попытка исправить геометрию
                
            logger.info(f"📐 Создан полигон участка. Площадь: {parcel_polygon.area:.2f} кв.м")
            
        except Exception as ex:
            logger.warning(f"Ошибка создания полигона участка: {ex}. Используется старый метод.")
            # Fallback на старый метод
            found = find_restrictions_for_parcel(coords, restrictions)
            for restr_dict in found:
                restriction = RestrictionZone(
                    zone_type=restr_dict.get('zone_type', "ЗОУИТ"),
                    name=restr_dict.get('name'),
                    registry_number=restr_dict.get('registry_number'),
                    decision_number=restr_dict.get('decision_number'),
                    decision_date=restr_dict.get('decision_date'),
                    decision_authority=restr_dict.get('decision_authority'),
                    area_sqm=None
                )
                gp_data.zouit.append(restriction)
            
            if found:
                logger.info(f"Найдено ЗОУИТ: {len(found)} (без расчёта площади)")
            return
        
        # Проверяем пересечения и считаем площади
        found_restrictions = []
        total_area = 0.0
        
        for i, restr in enumerate(restrictions):
            restr_geom = restr.get('geometry')
            if restr_geom is None:
                logger.debug(f"ЗОУИТ {restr.get('name', 'Unknown')} не имеет геометрии, пропускаем")
                continue
            
            try:
                # Проверяем пересечение
                if not parcel_polygon.intersects(restr_geom):
                    continue
                
                # 🔥 РЕАЛЬНЫЙ РАСЧЁТ ПЛОЩАДИ ПЕРЕСЕЧЕНИЯ
                intersection = parcel_polygon.intersection(restr_geom)
                intersection_area = intersection.area if hasattr(intersection, 'area') else 0.0
                
                # ФИЛЬТР: Игнорируем ЗОУИТ с площадью менее 1 кв.м
                if intersection_area < 1.0:
                    logger.debug(f"Игнорируем ЗОУИТ {restr.get('name', 'Unknown')} - площадь пересечения слишком мала: {intersection_area:.3f} кв.м")
                    continue
                
                # Создаём ограничение с площадью И ПОЛНОЙ ГЕОМЕТРИЕЙ
                restriction = RestrictionZone(
                    zone_type=restr.get('zone_type', "ЗОУИТ"),
                    name=restr.get('name'),
                    registry_number=restr.get('registry_number'),
                    decision_number=restr.get('decision_number'),
                    decision_date=restr.get('decision_date'),
                    decision_authority=restr.get('decision_authority'),
                    area_sqm=intersection_area,  # 🔥 РЕАЛЬНАЯ ПЛОЩАДЬ ПЕРЕСЕЧЕНИЯ
                    geometry=restr_geom           # ✅ ПОЛНАЯ геометрия ЗОУИТ (для карты!)
                )
                
                gp_data.zouit.append(restriction)
                found_restrictions.append(restriction)
                total_area += intersection_area
                
                logger.info(f"✅ Найдена ЗОУИТ: {restriction.get_full_name()}, площадь пересечения: {intersection_area:.2f} кв.м")
                
            except Exception as ex:
                logger.warning(f"Ошибка при расчёте площади пересечения с ЗОУИТ {restr.get('name', 'Unknown')}: {ex}")
                # Добавляем без площади как fallback
                restriction = RestrictionZone(
                    zone_type=restr.get('zone_type', "ЗОУИТ"),
                    name=restr.get('name'),
                    registry_number=restr.get('registry_number'),
                    decision_number=restr.get('decision_number'),
                    decision_date=restr.get('decision_date'),
                    decision_authority=restr.get('decision_authority'),
                    area_sqm=None
                )
                gp_data.zouit.append(restriction)
                found_restrictions.append(restriction)
        
        # Итоговая статистика
        if found_restrictions:
            areas_calculated = [r for r in found_restrictions if r.area_sqm is not None]
            logger.info(f"📊 Найдено ЗОУИТ: {len(found_restrictions)}")
            logger.info(f"📐 С рассчитанными площадями: {len(areas_calculated)}")
            if total_area > 0:
                logger.info(f"📊 Общая площадь пересечения: {total_area:.2f} кв.м")
        else:
            logger.info("ЗОУИТ не обнаружены для участка")
        
    except Exception as ex:
        msg = f"Ошибка при проверке ЗОУИТ: {ex}"
        logger.exception(msg)
        gp_data.add_warning(msg)


def _analyze_other_restrictions(gp_data: GPData, coords: List[Tuple[float, float]]):
    """Проверить АГО, КРТ, ОКН"""
    pass


def test_layers_availability() -> Dict[str, bool]:
    """Проверить доступность слоёв"""
    return LayerPaths.check_layers_exist()


def get_analysis_summary(gp_data: GPData) -> str:
    """Получить сводку анализа"""
    if not gp_data.analysis_completed:
        return "Анализ ещё не выполнен"
    return gp_data.get_summary()