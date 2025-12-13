# backend/generator/geometry_builder.py
"""
Генератор геометрии для рабочего набора MapInfo.

Функции для создания геометрических объектов:
- Зона строительства (буфер -5м от границ участка)
- Валидация и обработка геометрии
"""

from __future__ import annotations
from typing import List, Tuple, Optional
import logging
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid

logger = logging.getLogger(__name__)


def create_building_zone(
    parcel_coords: List[Tuple[float, float]],
    buffer_distance: float = -5.0
) -> Polygon:
    """
    Создает зону строительства с отступом от границ земельного участка.
    
    Согласно требованиям к графической части градплана:
    - Минимальные отступы от границ ЗУ = 5 метров внутрь
    - Отображается штриховкой
    
    Args:
        parcel_coords: Координаты границ участка [(x, y), ...]
                       где x = север, y = восток (формат из парсера ЕГРН)
        buffer_distance: Расстояние буфера в метрах.
                        Отрицательное значение = отступ внутрь участка.
                        По умолчанию -5.0 (5 метров внутрь)
    
    Returns:
        Polygon с зоной строительства (может быть пустым если буфер слишком большой)
    
    Raises:
        ValueError: Если координаты некорректны
    
    Example:
        >>> coords = [(2209000, 447000), (2209100, 447000), 
        ...           (2209100, 447100), (2209000, 447100)]
        >>> zone = create_building_zone(coords, buffer_distance=-5.0)
        >>> print(f"Площадь зоны: {zone.area:.2f} кв.м")
    """
    
    if not parcel_coords or len(parcel_coords) < 3:
        raise ValueError(
            f"Недостаточно координат для построения полигона. "
            f"Требуется минимум 3 точки, получено: {len(parcel_coords)}"
        )
    
    try:
        # Создаем полигон участка
        parcel_polygon = Polygon(parcel_coords)
        
        # Проверяем валидность
        if not parcel_polygon.is_valid:
            logger.warning("Полигон участка невалидный, пытаемся исправить...")
            parcel_polygon = make_valid(parcel_polygon)
            
            # Если после исправления получился MultiPolygon, берем самый большой
            if isinstance(parcel_polygon, MultiPolygon):
                logger.warning("Получен MultiPolygon, выбираем самый большой полигон")
                parcel_polygon = max(parcel_polygon.geoms, key=lambda p: p.area)
        
        logger.info(f"Полигон участка создан. Площадь: {parcel_polygon.area:.2f} кв.м")
        
        # Создаем буфер (отрицательное значение = внутрь)
        building_zone = parcel_polygon.buffer(
            buffer_distance,
            cap_style='square',      # Прямые углы (не скругленные)
            join_style='mitre',      # Острые углы
            mitre_limit=5.0          # Ограничение для острых углов
        )
        
        # Проверяем что буфер не пустой
        if building_zone.is_empty:
            logger.warning(
                f"Зона строительства пустая! Буфер {buffer_distance}м слишком большой "
                f"для участка площадью {parcel_polygon.area:.2f} кв.м"
            )
            # Возвращаем пустой полигон
            return Polygon()
        
        # Если получился MultiPolygon (например, участок Г-образный), берем самый большой
        if isinstance(building_zone, MultiPolygon):
            logger.info("Зона строительства разделилась на несколько частей, выбираем самую большую")
            building_zone = max(building_zone.geoms, key=lambda p: p.area)
        
        logger.info(
            f"Зона строительства создана. "
            f"Площадь: {building_zone.area:.2f} кв.м "
            f"({building_zone.area / parcel_polygon.area * 100:.1f}% от участка)"
        )
        
        return building_zone
        
    except Exception as e:
        logger.error(f"Ошибка создания зоны строительства: {e}")
        raise ValueError(f"Не удалось создать зону строительства: {e}")


def validate_geometry(geometry: Polygon) -> Tuple[bool, Optional[str]]:
    """
    Проверяет валидность геометрии.
    
    Args:
        geometry: Полигон для проверки
    
    Returns:
        Кортеж (валидна, сообщение об ошибке)
    
    Example:
        >>> polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
        >>> is_valid, error = validate_geometry(polygon)
        >>> print(f"Валидна: {is_valid}")
    """
    
    if geometry is None:
        return False, "Геометрия пустая (None)"
    
    if geometry.is_empty:
        return False, "Геометрия пустая (empty)"
    
    if not geometry.is_valid:
        return False, f"Невалидная геометрия: {geometry.is_valid_reason}"
    
    if geometry.area < 1.0:
        return False, f"Площадь слишком мала: {geometry.area:.2f} кв.м"
    
    return True, None


def get_geometry_bounds(geometry: Polygon) -> Tuple[float, float, float, float]:
    """
    Получает границы геометрии (bounding box).
    
    Args:
        geometry: Полигон
    
    Returns:
        Кортеж (min_x, min_y, max_x, max_y)
        где x = север, y = восток
    
    Example:
        >>> polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        >>> bounds = get_geometry_bounds(polygon)
        >>> print(f"Границы: {bounds}")
        Границы: (0.0, 0.0, 10.0, 10.0)
    """
    
    return geometry.bounds  # (minx, miny, maxx, maxy)


def get_geometry_centroid(geometry: Polygon) -> Tuple[float, float]:
    """
    Получает центроид (центр масс) геометрии.
    
    Args:
        geometry: Полигон
    
    Returns:
        Кортеж (x, y) координат центра
        где x = север, y = восток
    
    Example:
        >>> polygon = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        >>> center = get_geometry_centroid(polygon)
        >>> print(f"Центр: {center}")
        Центр: (5.0, 5.0)
    """
    
    centroid = geometry.centroid
    return (centroid.x, centroid.y)


def simplify_geometry(
    geometry: Polygon,
    tolerance: float = 0.1
) -> Polygon:
    """
    Упрощает геометрию, удаляя лишние точки.
    
    Полезно для уменьшения размера файлов TAB.
    
    Args:
        geometry: Полигон для упрощения
        tolerance: Допустимое отклонение в метрах (по умолчанию 0.1м = 10см)
    
    Returns:
        Упрощенный полигон
    
    Example:
        >>> # Полигон с 1000 точек
        >>> simplified = simplify_geometry(polygon, tolerance=1.0)
        >>> # Полигон с ~100 точек
    """
    
    return geometry.simplify(tolerance, preserve_topology=True)


def get_geometry_info(geometry: Polygon) -> dict:
    """
    Получает информацию о геометрии для отладки.
    
    Args:
        geometry: Полигон
    
    Returns:
        Словарь с информацией о геометрии
    
    Example:
        >>> info = get_geometry_info(polygon)
        >>> print(info)
        {
            'type': 'Polygon',
            'is_valid': True,
            'area': 1234.56,
            'perimeter': 150.0,
            'num_points': 50,
            'bounds': (0, 0, 100, 100),
            'centroid': (50.0, 50.0)
        }
    """
    
    is_valid, error = validate_geometry(geometry)
    
    info = {
        'type': geometry.geom_type,
        'is_valid': is_valid,
        'validation_error': error,
        'is_empty': geometry.is_empty,
        'area': round(geometry.area, 2) if not geometry.is_empty else 0,
        'perimeter': round(geometry.length, 2) if not geometry.is_empty else 0,
        'num_points': len(geometry.exterior.coords) if not geometry.is_empty else 0,
        'bounds': geometry.bounds if not geometry.is_empty else None,
        'centroid': (round(geometry.centroid.x, 2), round(geometry.centroid.y, 2)) if not geometry.is_empty else None
    }
    
    return info


# ================ ПРИМЕР ИСПОЛЬЗОВАНИЯ ================ #

if __name__ == "__main__":
    # Пример: создание зоны строительства для тестового участка
    
    # Координаты прямоугольного участка 100x100 метров
    # x = север, y = восток (формат из ЕГРН парсера)
    test_coords = [
        (2209000, 447000),  # юго-запад
        (2209100, 447000),  # юго-восток
        (2209100, 447100),  # северо-восток
        (2209000, 447100),  # северо-запад
        (2209000, 447000),  # замыкаем контур
    ]
    
    print("=" * 60)
    print("ТЕСТ: Создание зоны строительства")
    print("=" * 60)
    
    # Создаем зону с отступом 5м
    building_zone = create_building_zone(test_coords, buffer_distance=-5.0)
    
    # Информация о зоне
    info = get_geometry_info(building_zone)
    
    print(f"\nРезультат:")
    print(f"  Тип: {info['type']}")
    print(f"  Валидна: {info['is_valid']}")
    print(f"  Площадь: {info['area']} кв.м")
    print(f"  Периметр: {info['perimeter']} м")
    print(f"  Количество точек: {info['num_points']}")
    print(f"  Центр: {info['centroid']}")
    
    # Исходный участок для сравнения
    original = Polygon(test_coords)
    print(f"\nСравнение:")
    print(f"  Площадь участка: {original.area:.2f} кв.м")
    print(f"  Площадь зоны: {building_zone.area:.2f} кв.м")
    print(f"  Процент от участка: {building_zone.area / original.area * 100:.1f}%")
    print(f"  Потеря площади: {original.area - building_zone.area:.2f} кв.м")
    
    print("=" * 60)