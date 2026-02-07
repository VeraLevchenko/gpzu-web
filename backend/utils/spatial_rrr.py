# backend/utils/spatial_rrr.py
"""
Пространственный анализ для модуля РРР (15 слоёв).
"""

from __future__ import annotations

import logging
from typing import List, Tuple, Dict, Any, Optional

try:
    from shapely.geometry import Polygon
    SHAPELY_AVAILABLE = True
except ImportError:
    SHAPELY_AVAILABLE = False

from core.layers_config import LayerPaths
from parsers.tab_parser import (
    parse_capital_objects_layer,
    find_objects_on_parcel,
    parse_zouit_layer_extended,
    find_restrictions_for_parcel,
    parse_planning_projects_layer,
    check_planning_project_intersection,
)

logger = logging.getLogger("gpzu-web.spatial_rrr")


def perform_rrr_spatial_analysis(coordinates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Выполнить пространственный анализ для РРР (15 слоёв).

    Args:
        coordinates: Список координат [{num, x, y}, ...]

    Returns:
        Словарь с результатами анализа по всем слоям
    """
    logger.info(f"Начало пространственного анализа РРР ({len(coordinates)} точек)")

    result = {
        "quarters": None,
        "capital_objects": [],
        "zouit": [],
        "red_lines_inside_area": None,
        "red_lines_outside_area": None,
        "red_lines_description": None,
        "ppipm": [],
        "rrr": [],
        "preliminary_approval": [],
        "preliminary_approval_kumi": [],
        "scheme_location": [],
        "scheme_location_kumi": [],
        "scheme_nto": [],
        "advertising": [],
        "land_bank": [],
        "warnings": [],
    }

    # Преобразуем координаты в формат для Shapely
    coords = _parse_coords(coordinates)
    if not coords:
        result["warnings"].append("Отсутствуют координаты для анализа")
        logger.error("Нет координат для анализа")
        return result

    if len(coords) < 3:
        result["warnings"].append("Недостаточно координат для построения полигона (минимум 3)")
        return result

    # Создаём полигон
    try:
        polygon = Polygon(coords)
        if not polygon.is_valid:
            polygon = polygon.buffer(0)
        logger.info(f"Полигон создан. Площадь: {polygon.area:.2f} кв.м")
    except Exception as ex:
        result["warnings"].append(f"Ошибка создания полигона: {ex}")
        logger.error(f"Ошибка создания полигона: {ex}")
        return result

    # Выполняем анализ по каждому слою
    logger.info("Этап 1/15: Кадастровые кварталы")
    _analyze_cadastral_quarters(result, coords, polygon)

    logger.info("Этап 2/15: Объекты капитального строительства")
    _analyze_capital_objects(result, coords)

    logger.info("Этап 3/15: ЗОУИТ")
    _analyze_zouit(result, coords, polygon)

    logger.info("Этап 4/15: Красные линии")
    _analyze_red_lines(result, polygon)

    logger.info("Этап 5/15: ППиПМ")
    _analyze_ppipm(result, coords)

    logger.info("Этап 6/15: РРР заявления")
    _analyze_rrr_applications(result, coords, polygon)

    logger.info("Этап 7/15: Предварительное согласование")
    _analyze_preliminary_approval(result, coords, polygon)

    logger.info("Этап 8/15: Предварительное согласование КУМИ")
    _analyze_preliminary_approval_kumi(result, coords, polygon)

    logger.info("Этап 9/15: Схема расположения")
    _analyze_scheme_location(result, coords, polygon)

    logger.info("Этап 10/15: Схема расположения КУМИ")
    _analyze_scheme_location_kumi(result, coords, polygon)

    logger.info("Этап 11/15: Схема НТО")
    _analyze_scheme_nto(result, coords, polygon)

    logger.info("Этап 12/15: Реклама")
    _analyze_advertising(result, coords, polygon)

    logger.info("Этап 13/15: Банк ЗУ многодетные")
    _analyze_land_bank(result, coords, polygon)

    logger.info("Этап 14/15: Участки")
    # Участки — информационный слой, пока пропускаем
    pass

    logger.info("Этап 15/15: РРР выходной слой")
    # Выходной слой — только для записи, не для анализа
    pass

    # Формируем предупреждения
    result["warnings"] = "; ".join(result["warnings"]) if result["warnings"] else None

    logger.info("Пространственный анализ РРР завершён")
    return result


def _parse_coords(coordinates: List[Dict[str, Any]]) -> List[Tuple[float, float]]:
    """Преобразовать координаты в список кортежей."""
    parsed = []
    for coord in coordinates:
        try:
            x = float(str(coord.get("x", "")).replace(",", ".").replace(" ", ""))
            y = float(str(coord.get("y", "")).replace(",", ".").replace(" ", ""))
            parsed.append((x, y))
        except (ValueError, AttributeError):
            continue
    return parsed


def _generic_layer_analysis(
    layer_path,
    layer_name: str,
    polygon,
    field_map: Dict[str, str],
    warnings: list,
) -> List[Dict[str, Any]]:
    """
    Обобщённый анализ пересечений с TAB-слоем.

    Args:
        layer_path: Путь к TAB файлу
        layer_name: Название слоя (для логирования)
        polygon: Shapely Polygon участка
        field_map: Маппинг {ключ_результата: имя_поля_в_слое}
        warnings: Список предупреждений

    Returns:
        Список найденных пересечений
    """
    from parsers.tab_parser import parse_tab_file

    if not layer_path.exists():
        warnings.append(f"Слой {layer_name} не найден: {layer_path}")
        logger.warning(f"Слой {layer_name} не найден: {layer_path}")
        return []

    try:
        records = parse_tab_file(layer_path)
        if not records:
            logger.info(f"Слой {layer_name} пуст")
            return []

        results = []
        for record in records:
            geom = record.get("geometry")
            if geom is None:
                continue

            try:
                if not polygon.intersects(geom):
                    continue

                item = {}
                for result_key, field_name in field_map.items():
                    item[result_key] = record.get(field_name, "")
                results.append(item)
            except Exception:
                continue

        if results:
            logger.info(f"Найдено {len(results)} пересечений в слое {layer_name}")
        return results

    except Exception as ex:
        warnings.append(f"Ошибка анализа слоя {layer_name}: {ex}")
        logger.warning(f"Ошибка анализа слоя {layer_name}: {ex}")
        return []


def _analyze_cadastral_quarters(result: dict, coords: list, polygon):
    """Анализ кадастровых кварталов."""
    layer = LayerPaths.RRR_CADASTRAL_QUARTERS
    if not layer.exists():
        result["warnings"].append(f"Слой кадастровых кварталов не найден: {layer}")
        return

    try:
        from parsers.tab_parser import parse_tab_file
        records = parse_tab_file(layer)
        quarters = []
        for record in records:
            geom = record.get("geometry")
            if geom and polygon.intersects(geom):
                cad_num = record.get("CAD_NUM", "")
                if cad_num and cad_num not in quarters:
                    quarters.append(cad_num)
        result["quarters"] = ", ".join(quarters) if quarters else None
    except Exception as ex:
        result["warnings"].append(f"Ошибка анализа кадастровых кварталов: {ex}")
        logger.warning(f"Ошибка анализа кадастровых кварталов: {ex}")


def _analyze_capital_objects(result: dict, coords: list):
    """Анализ объектов капитального строительства."""
    layer = LayerPaths.CAPITAL_OBJECTS
    if not layer.exists():
        result["warnings"].append(f"Слой ОКС не найден: {layer}")
        return

    try:
        objects = parse_capital_objects_layer(layer)
        if not objects:
            return

        found = find_objects_on_parcel(coords, objects)
        for obj in found:
            result["capital_objects"].append({
                "cadnum": obj.get("cadnum", ""),
                "type": obj.get("object_type", ""),
                "address": obj.get("purpose", ""),
            })
    except Exception as ex:
        result["warnings"].append(f"Ошибка анализа ОКС: {ex}")
        logger.warning(f"Ошибка анализа ОКС: {ex}")


def _analyze_zouit(result: dict, coords: list, polygon):
    """Анализ ЗОУИТ."""
    layer = LayerPaths.ZOUIT
    if not layer.exists():
        result["warnings"].append(f"Слой ЗОУИТ не найден: {layer}")
        return

    try:
        restrictions = parse_zouit_layer_extended(layer, "ЗОУИТ")
        if not restrictions:
            return

        found = find_restrictions_for_parcel(coords, restrictions)
        for restr in found:
            result["zouit"].append({
                "registry_number": restr.get("registry_number", ""),
                "name": restr.get("name", ""),
            })
    except Exception as ex:
        result["warnings"].append(f"Ошибка анализа ЗОУИТ: {ex}")
        logger.warning(f"Ошибка анализа ЗОУИТ: {ex}")


def _analyze_red_lines(result: dict, polygon):
    """Анализ красных линий (площади внутри/снаружи)."""
    layer = LayerPaths.RRR_RED_LINES
    if not layer.exists():
        result["warnings"].append(f"Слой красных линий не найден: {layer}")
        return

    if not SHAPELY_AVAILABLE:
        result["warnings"].append("Shapely недоступен для расчёта красных линий")
        return

    try:
        from parsers.tab_parser import parse_tab_file
        records = parse_tab_file(layer)
        if not records:
            return

        # Объединяем все геометрии красных линий
        from shapely.ops import unary_union
        red_line_geoms = []
        descriptions = []
        for record in records:
            geom = record.get("geometry")
            if geom and polygon.intersects(geom):
                red_line_geoms.append(geom)
                desc = record.get("Описание", "")
                if desc and desc not in descriptions:
                    descriptions.append(desc)

        if red_line_geoms:
            red_lines_union = unary_union(red_line_geoms)
            intersection = polygon.intersection(red_lines_union)
            difference = polygon.difference(red_lines_union)

            result["red_lines_inside_area"] = round(intersection.area, 2) if not intersection.is_empty else 0.0
            result["red_lines_outside_area"] = round(difference.area, 2) if not difference.is_empty else 0.0
            result["red_lines_description"] = "; ".join(descriptions) if descriptions else None

            logger.info(
                f"Красные линии: внутри={result['red_lines_inside_area']} кв.м, "
                f"снаружи={result['red_lines_outside_area']} кв.м"
            )

    except Exception as ex:
        result["warnings"].append(f"Ошибка анализа красных линий: {ex}")
        logger.warning(f"Ошибка анализа красных линий: {ex}")


def _analyze_ppipm(result: dict, coords: list):
    """Анализ проектов планировки и межевания."""
    layer = LayerPaths.PLANNING_PROJECTS
    if not layer.exists():
        return

    try:
        projects = parse_planning_projects_layer(layer)
        if not projects:
            return

        project_info = check_planning_project_intersection(coords, projects)
        if project_info:
            result["ppipm"].append({
                "project_name": project_info.get("project_name", ""),
                "note": project_info.get("decision_number", ""),
            })
    except Exception as ex:
        result["warnings"].append(f"Ошибка анализа ППиПМ: {ex}")
        logger.warning(f"Ошибка анализа ППиПМ: {ex}")


def _analyze_rrr_applications(result: dict, coords: list, polygon):
    """Анализ ранее выданных РРР заявлений."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_APPLICATIONS,
        "РРР заявления",
        polygon,
        {
            "incoming_number": "Входящий_номер",
            "incoming_date": "Входящая_дата",
            "applicant": "Заявитель",
            "name": "Наименование",
        },
        result["warnings"],
    )
    result["rrr"] = items


def _analyze_preliminary_approval(result: dict, coords: list, polygon):
    """Анализ предварительного согласования."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_PRELIMINARY_APPROVAL,
        "Предварительное согласование",
        polygon,
        {
            "decision_date": "ДатаРешения",
            "protocol_number": "НомерПротокола_или_решения",
            "object": "Объект",
            "location": "Местоположение",
        },
        result["warnings"],
    )
    result["preliminary_approval"] = items


def _analyze_preliminary_approval_kumi(result: dict, coords: list, polygon):
    """Анализ предварительного согласования КУМИ."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_PRELIMINARY_APPROVAL_KUMI,
        "Предварительное согласование КУМИ",
        polygon,
        {
            "decision_date": "Дата_решения",
            "decision_number": "Номер_решения",
            "cadnum": "Кадастровый_номер_ЗУ",
            "location": "Местоположение",
        },
        result["warnings"],
    )
    result["preliminary_approval_kumi"] = items


def _analyze_scheme_location(result: dict, coords: list, polygon):
    """Анализ схемы расположения."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_SCHEME_LOCATION,
        "Схема расположения",
        polygon,
        {
            "order": "Распоряжение",
            "location": "Местоположение",
            "usage": "Разрешенное_использование",
        },
        result["warnings"],
    )
    result["scheme_location"] = items


def _analyze_scheme_location_kumi(result: dict, coords: list, polygon):
    """Анализ схемы расположения КУМИ."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_SCHEME_LOCATION_KUMI,
        "Схема расположения КУМИ",
        polygon,
        {
            "decision_date": "Дата_решения",
            "decision_number": "Номер_решения",
            "location": "Местоположение",
            "usage": "Разрешенное_использование",
        },
        result["warnings"],
    )
    result["scheme_location_kumi"] = items


def _analyze_scheme_nto(result: dict, coords: list, polygon):
    """Анализ схемы НТО."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_SCHEME_NTO,
        "Схема НТО",
        polygon,
        {
            "number": "Порядковый_номер_в_схеме",
            "address": "Адресный_ориентир",
        },
        result["warnings"],
    )
    result["scheme_nto"] = items


def _analyze_advertising(result: dict, coords: list, polygon):
    """Анализ рекламных конструкций."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_ADVERTISING,
        "Реклама",
        polygon,
        {
            "number": "Номер",
            "address": "Адрес",
            "type": "Вид",
        },
        result["warnings"],
    )
    result["advertising"] = items


def _analyze_land_bank(result: dict, coords: list, polygon):
    """Анализ банка ЗУ для многодетных."""
    items = _generic_layer_analysis(
        LayerPaths.RRR_LAND_BANK,
        "Банк ЗУ многодетные",
        polygon,
        {
            "cadnum": "Кадастровый_номер",
            "location": "Местоположение",
        },
        result["warnings"],
    )
    result["land_bank"] = items
