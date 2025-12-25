# backend/generator/mif_writer.py
"""
Генератор MIF/MID файлов MapInfo для рабочего набора.

🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Все файлы пишутся в бинарном режиме ('wb') 
с явной кодировкой CP1251 для корректного отображения русских символов в MapInfo.

MIF (MapInfo Interchange Format) - текстовый формат MapInfo
Каждый слой состоит из двух файлов:
- .MIF - геометрия, структура полей, система координат
- .MID - атрибутивные данные
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import logging
import tempfile
import shutil
from datetime import datetime

logger = logging.getLogger(__name__)


# ================ КОНСТАНТЫ ДИРЕКТОРИЙ ================ #

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp" / "workspace"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ================ СИСТЕМА КООРДИНАТ ================ #

# МСК-42 зона 2 (Кемеровская область, Новокузнецк)
MSK42_COORDSYS = 'CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997 Bounds (-7786100, -9553200) (12213900, 10446800)'


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def escape_mif_string(s: str) -> str:
    """Экранировать строку для MIF/MID."""
    if s is None:
        return '""'
    s = str(s).replace('"', '""')
    return f'"{s}"'


def safe_encode_cp1251(s: str) -> str:
    """
    Безопасно подготовить строку для записи в CP1251.
    
    🔥 КРИТИЧЕСКИ ВАЖНО: Эта функция обеспечивает корректную конвертацию
    UTF-8 → CP1251 для русских символов в MapInfo.
    """
    if s is None or s == '':
        return ''
    
    try:
        s = str(s)
        
        if isinstance(s, bytes):
            s = s.decode('utf-8', errors='replace')
        
        try:
            encoded = s.encode('cp1251', errors='strict')
            return encoded.decode('cp1251')
        except UnicodeEncodeError as enc_err:
            logger.warning(
                f"Символы не поддерживаются в CP1251: '{s[:100]}...' "
                f"Позиция: {enc_err.start}-{enc_err.end}"
            )
            encoded = s.encode('cp1251', errors='replace')
            return encoded.decode('cp1251')
            
    except Exception as e:
        logger.error(f"Ошибка кодировки: '{s[:50]}...': {e}")
        return str(s).encode('ascii', errors='replace').decode('ascii')


def format_mif_number(n: Optional[float]) -> str:
    """Форматировать число для MIF/MID."""
    if n is None:
        return '0'
    return str(n)


# ================ СОЗДАНИЕ MIF/MID УЧАСТКА ================ #

def create_parcel_mif(
    parcel_data: Any,
    output_dir: Path,
    filename: str = "участок"
) -> Tuple[Path, Path]:
    """Создать MIF/MID файлы земельного участка."""
    
    logger.info(f"Создание MIF/MID участка: {parcel_data.cadnum}")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    coords = parcel_data.coordinates
    
    # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Бинарный режим записи
    with open(mif_path, 'wb') as f:
        def w(text: str):
            f.write(text.encode('cp1251'))
        
        w('Version   450\n')
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f'{MSK42_COORDSYS}\n')
        w('Columns 3\n')
        w('  Кадастровый_номер Char(254)\n')
        w('  Адрес Char(254)\n')
        w('  Площадь Float\n')
        w('Data\n\n')
        
        w('Region  1\n')
        w(f'  {len(coords)}\n')
        for x, y in coords:
            w(f'{x} {y}\n')
        w('    Pen (1,2,0)\n')
        w('    Brush (1,0,16777215)\n')
    
    with open(mid_path, 'wb') as f:
        cadnum_safe = safe_encode_cp1251(parcel_data.cadnum)
        address_safe = safe_encode_cp1251(parcel_data.address or "")
        
        cadnum = escape_mif_string(cadnum_safe)
        address = escape_mif_string(address_safe)
        logger.info(f"📐 Площадь участка: {parcel_data.area} (тип: {type(parcel_data.area)})")
        area = format_mif_number(parcel_data.area)
        
        line = f'{cadnum},{address},{area}\n'
        f.write(line.encode('cp1251'))
    
    logger.info(f"✅ MIF/MID участка созданы")
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ТОЧЕК УЧАСТКА ================ #

def create_parcel_points_mif(
    parcel_data: Any,
    output_dir: Path,
    filename: str = "участок_точки"
) -> Tuple[Path, Path]:
    """Создать MIF/MID файлы характерных точек участка."""
    
    logger.info(f"Создание MIF/MID точек: {len(parcel_data.coordinates)} точек")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    coords = parcel_data.coordinates
    
    with open(mif_path, 'wb') as f:
        def w(text: str):
            f.write(text.encode('cp1251'))
        
        w('Version   450\n')
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f'{MSK42_COORDSYS}\n')
        w('Columns 2\n')
        w('  Кадастровый_номер Char(254)\n')
        w('  Номер_точки Integer\n')
        w('Data\n\n')
        
        for i, (x, y) in enumerate(coords, start=1):
            w(f'Point {x} {y}\n')
            w('    Symbol (34,6,12)\n')
            w('\n')
    
    with open(mid_path, 'wb') as f:
        cadnum_safe = safe_encode_cp1251(parcel_data.cadnum)
        cadnum = escape_mif_string(cadnum_safe)
        
        for i in range(1, len(coords) + 1):
            line = f'{cadnum},{i}\n'
            f.write(line.encode('cp1251'))
    
    logger.info(f"✅ MIF/MID точек созданы")
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ЗОНЫ СТРОИТЕЛЬСТВА ================ #

def create_building_zone_mif(
    building_zone_data: Any,
    cadnum: str,
    output_dir: Path,
    filename: str = "зона_строительства"
) -> Tuple[Path, Path]:
    """Создать MIF/MID файлы зоны строительства."""
    
    logger.info("Создание MIF/MID зоны строительства")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    if building_zone_data.geometry.is_empty:
        logger.warning("Зона строительства пустая!")
        with open(mif_path, 'wb') as f:
            f.write('Version   450\n'.encode('cp1251'))
            f.write('Charset "WindowsCyrillic"\n'.encode('cp1251'))
            f.write(f'{MSK42_COORDSYS}\n'.encode('cp1251'))
            f.write('Columns 0\nData\n'.encode('cp1251'))
        with open(mid_path, 'wb') as f:
            pass
        return mif_path, mid_path
    
    coords = building_zone_data.coordinates
    
    with open(mif_path, 'wb') as f:
        def w(text: str):
            f.write(text.encode('cp1251'))
        
        w('Version   450\n')
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f'{MSK42_COORDSYS}\n')
        w('Columns 3\n')
        w('  Кадастровый_номер Char(254)\n')
        w('  Описание Char(254)\n')
        w('  Площадь Float\n')
        w('Data\n\n')
        
        w('Region  1\n')
        w(f'  {len(coords)}\n')
        for x, y in coords:
            w(f'{x} {y}\n')
        w('    Pen (1,2,0)\n')
        w('    Brush (2,0,16777215)\n')
    
    with open(mid_path, 'wb') as f:
        cadnum_safe = safe_encode_cp1251(cadnum)
        desc_safe = safe_encode_cp1251("Минимальные отступы от границ ЗУ")
        
        cadnum_str = escape_mif_string(cadnum_safe)
        desc = escape_mif_string(desc_safe)
        area = format_mif_number(building_zone_data.geometry.area)
        
        line = f'{cadnum_str},{desc},{area}\n'
        f.write(line.encode('cp1251'))
    
    logger.info(f"✅ MIF/MID зоны строительства созданы")
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ОКС ================ #

def create_oks_mif(
    capital_objects: List[Any],
    output_dir: Path,
    filename: str = "окс"
) -> Optional[Tuple[Path, Path]]:
    """Создать MIF/MID файлы объектов капитального строительства."""
    
    if not capital_objects:
        logger.info("Нет ОКС для создания MIF/MID")
        return None
    
    logger.info(f"Создание MIF/MID ОКС: {len(capital_objects)} объектов")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    valid_objects = [obj for obj in capital_objects if obj.geometry is not None]
    
    if not valid_objects:
        logger.warning("Нет ОКС с геометрией")
        return None
    
    with open(mif_path, 'wb') as f:
        def w(text: str):
            f.write(text.encode('cp1251'))
        
        w('Version   450\n')
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f'{MSK42_COORDSYS}\n')
        w('Columns 6\n')
        w('  Номер Integer\n')
        w('  Кадастровый_номер Char(254)\n')
        w('  Тип_объекта Char(254)\n')
        w('  Назначение Char(254)\n')
        w('  Площадь Float\n')
        w('  Этажность Integer\n')
        w('Data\n\n')
        
        for i, obj in enumerate(valid_objects, start=1):
            geom = obj.geometry
            
            if hasattr(geom, 'x') and hasattr(geom, 'y'):
                w(f'Point {geom.x} {geom.y}\n')
                w('    Symbol (35,12,0)\n')
            elif hasattr(geom, 'exterior'):
                coords = list(geom.exterior.coords)
                w('Region  1\n')
                w(f'  {len(coords)}\n')
                for x, y in coords:
                    w(f'{x} {y}\n')
                w('    Pen (1,2,0)\n')
                w('    Brush (1,0,16777215)\n')
            w('\n')
    
    with open(mid_path, 'wb') as f:
        for i, obj in enumerate(valid_objects, start=1):
            num = str(i)
            
            cadnum_safe = safe_encode_cp1251(obj.cadnum or "")
            type_safe = safe_encode_cp1251(obj.object_type or "")
            purpose_safe = safe_encode_cp1251(obj.purpose or "")
            
            cadnum = escape_mif_string(cadnum_safe)
            obj_type = escape_mif_string(type_safe)
            purpose = escape_mif_string(purpose_safe)
            
            area = format_mif_number(obj.area)
            floors = str(obj.floors) if obj.floors else "0"
            
            line = f'{num},{cadnum},{obj_type},{purpose},{area},{floors}\n'
            f.write(line.encode('cp1251'))
    
    logger.info(f"✅ MIF/MID ОКС созданы: {len(valid_objects)} объектов")
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ЗОУИТ (ОТДЕЛЬНЫЕ СЛОИ) ================ #

def create_zouit_mif(
    zouit_list: List[Any],
    output_dir: Path,
    filename: str = "зоуит"
) -> Optional[List[Tuple[Path, Path]]]:
    """
    Создать отдельные MIF/MID файлы для каждой ЗОУИТ.
    
    ✨ ОБНОВЛЕНО:
    - Каждая зона создается в отдельном слое (файле)
    - Добавлено поле "Реестровый_номер"
    - БЕЗ заливки - только контур
    - ✅ MultiPolygon: записываются ВСЕ части как отдельные регионы
    - ✅ ДОБАВЛЕНО детальное логирование
    
    Args:
        zouit_list: Список объектов ZouitInfo
        output_dir: Директория для сохранения
        filename: Не используется (для совместимости)
    
    Returns:
        Список кортежей [(Path к MIF, Path к MID), ...] для каждой зоны
        или None если зон нет
    """
    
    if not zouit_list:
        logger.info("Нет ЗОУИТ для создания MIF/MID")
        return None
    
    logger.info(f"Создание отдельных слоёв ЗОУИТ: {len(zouit_list)} зон")
    
    output_dir = Path(output_dir)
    
    # Фильтруем зоны с геометрией
    valid_zones = [z for z in zouit_list if z.geometry is not None]
    
    if not valid_zones:
        logger.warning("Нет ЗОУИТ с геометрией")
        return None
    
    logger.info(f"ЗОУИТ с геометрией: {len(valid_zones)} из {len(zouit_list)}")
    
    created_files = []
    
    # ✅ ДОБАВИТЬ: импорт для обработки MultiPolygon
    from shapely.geometry import MultiPolygon, Polygon
    
    # Создаем отдельный слой для каждой зоны
    for i, zone in enumerate(valid_zones, start=1):
        
        # Формируем безопасное имя файла из типа зоны
        safe_name = zone.type or zone.name or f"зона_{i}"
        
        # Убираем недопустимые символы для имени файла
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        safe_name = safe_name.replace(":", "_").replace("*", "_")
        safe_name = safe_name.replace("?", "_").replace('"', "_")
        safe_name = safe_name.replace("<", "_").replace(">", "_")
        safe_name = safe_name.replace("|", "_").strip()
        
        # Ограничиваем длину имени файла
        if len(safe_name) > 40:
            safe_name = safe_name[:40]
        
        filename_base = f"зоуит_{i}_{safe_name}"
        
        mif_path = output_dir / f"{filename_base}.MIF"
        mid_path = output_dir / f"{filename_base}.MID"
        
        logger.info(f"Создание слоя ЗОУИТ {i}/{len(valid_zones)}: {safe_name}")
        
        # ========== Создание MIF ========== #
        
        geom = zone.geometry
        
        if geom is None:
            logger.warning(f"  ❌ ЗОУИТ {i} ({safe_name}): геометрия = None, пропускаем")
            continue
        
        # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Обработка MultiPolygon
        polygons_to_write = []
        
        if isinstance(geom, MultiPolygon):
            # Записываем ВСЕ части MultiPolygon
            num_parts = len(geom.geoms)
            logger.info(f"  Геометрия ЗОУИТ {i} - MultiPolygon с {num_parts} частями, записываем ВСЕ")
            polygons_to_write = list(geom.geoms)
        elif isinstance(geom, Polygon):
            # Обычный Polygon
            logger.info(f"  Геометрия ЗОУИТ {i} - Polygon")
            polygons_to_write = [geom]
        else:
            logger.warning(f"  ❌ ЗОУИТ {i} ({safe_name}): неизвестный тип геометрии {type(geom).__name__}, пропускаем")
            continue
        
        # Фильтруем пустые полигоны
        valid_polygons = [p for p in polygons_to_write if p and not p.is_empty and hasattr(p, 'exterior')]
        
        if not valid_polygons:
            logger.warning(f"  ❌ ЗОУИТ {i} ({safe_name}): нет валидных полигонов, пропускаем")
            continue
        
        # Подсчитываем общее количество точек
        total_points = sum(len(p.exterior.coords) for p in valid_polygons)
        logger.info(f"  ✅ ЗОУИТ {i} ({safe_name}): записываем {len(valid_polygons)} полигонов с {total_points} точками")
        
        # ========== Запись MIF ========== #
        
        with open(mif_path, 'wb') as f:
            def w(text: str):
                f.write(text.encode('cp1251'))
            
            # Заголовок
            w('Version   450\n')
            w('Charset "WindowsCyrillic"\n')
            w('Delimiter ","\n')
            w(f'{MSK42_COORDSYS}\n')
            
            # ✅ ОБНОВЛЕНО: Добавлено поле Реестровый_номер
            w('Columns 4\n')
            w('  Наименование Char(254)\n')
            w('  Тип Char(254)\n')
            w('  Реестровый_номер Char(254)\n')
            w('  Ограничения Char(254)\n')
            w('Data\n\n')
            
            # ✅ КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Записываем MultiPolygon как Region с несколькими частями
            if len(valid_polygons) == 1:
                # Один полигон - простой регион
                coords = list(valid_polygons[0].exterior.coords)
                w('Region  1\n')
                w(f'  {len(coords)}\n')
                for x, y in coords:
                    w(f'{x} {y}\n')
            else:
                # Несколько полигонов - регион с несколькими частями
                w(f'Region  {len(valid_polygons)}\n')
                for poly in valid_polygons:
                    coords = list(poly.exterior.coords)
                    w(f'  {len(coords)}\n')
                    for x, y in coords:
                        w(f'{x} {y}\n')
            
            # БЕЗ ЗАЛИВКИ - только контур
            w('    Pen (1,2,0)\n')
            w('    Brush (1,0,16777215)\n')
            w('\n')
        
        # ========== Создание MID ========== #
        
        with open(mid_path, 'wb') as f:
            # Безопасная конвертация UTF-8 → CP1251
            name_safe = safe_encode_cp1251(zone.name or "")
            type_safe = safe_encode_cp1251(zone.type or "")
            restriction_safe = safe_encode_cp1251(zone.restriction or "")
            
            # ✅ НОВОЕ: Получаем реестровый номер из объекта zone
            registry_number = ""
            if hasattr(zone, 'registry_number') and zone.registry_number:
                registry_number = zone.registry_number
            registry_safe = safe_encode_cp1251(registry_number)
            
            # Экранирование для MIF
            name = escape_mif_string(name_safe)
            ztype = escape_mif_string(type_safe)
            registry = escape_mif_string(registry_safe)
            restriction = escape_mif_string(restriction_safe)
            
            # ✅ ОБНОВЛЕНО: Добавлен реестровый номер
            line = f'{name},{ztype},{registry},{restriction}\n'
            f.write(line.encode('cp1251'))
        
        created_files.append((mif_path, mid_path))
        logger.info(f"  ✅ Слой ЗОУИТ {i} создан: {mif_path.name}")
    
    logger.info(f"✅ Создано отдельных слоёв ЗОУИТ: {len(created_files)}")
    
    return created_files

def create_zouit_labels_mif(
    zouit_list: List[Any],
    parcel_geometry: Any,
    output_dir: Path,
    filename: str = "зоуит_подписи"
) -> Optional[Tuple[Path, Path]]:
    """
    Создать отдельный слой с точками-подписями для ЗОУИТ.
    
    Создаёт невидимые точки в центре ПЕРЕСЕЧЕНИЯ каждой ЗОУИТ с участком.
    Это позволяет:
    - В основном слое ЗОУИТ хранить ВСЮ зону целиком
    - В слое подписей иметь точки ТОЛЬКО в границах участка
    
    Args:
        zouit_list: Список объектов ZouitInfo с геометрией
        parcel_geometry: Геометрия участка (Polygon из workspace.parcel.geometry)
        output_dir: Директория для сохранения
        filename: Имя файла (по умолчанию "зоуит_подписи")
    
    Returns:
        Кортеж (Path к MIF, Path к MID) или None если нет зон
    """
    
    if not zouit_list:
        logger.info("Нет ЗОУИТ для создания слоя подписей")
        return None
    
    logger.info(f"Создание отдельного слоя подписей ЗОУИТ: {len(zouit_list)} зон")
    
    from shapely.geometry import MultiPolygon, Polygon
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    # Собираем точки для подписей
    label_points = []
    
    for i, zone in enumerate(zouit_list, start=1):
        if not zone.geometry:
            logger.debug(f"ЗОУИТ {i} ({zone.name}): нет геометрии, пропускаем")
            continue
        
        try:
            # 🔥 КЛЮЧЕВОЙ МОМЕНТ: Вычисляем пересечение с участком
            intersection = parcel_geometry.intersection(zone.geometry)
            
            if intersection.is_empty:
                logger.debug(f"ЗОУИТ {i} ({zone.name}): нет пересечения с участком")
                continue
            
            if intersection.area < 1.0:
                logger.debug(f"ЗОУИТ {i} ({zone.name}): пересечение слишком мало ({intersection.area:.2f} кв.м)")
                continue
            
            # Для MultiPolygon берём самую большую часть пересечения
            if isinstance(intersection, MultiPolygon):
                logger.info(f"  ЗОУИТ {i} ({zone.name}): MultiPolygon пересечение, берём самую большую часть")
                intersection = max(intersection.geoms, key=lambda p: p.area)
            
            if not isinstance(intersection, Polygon):
                logger.warning(f"ЗОУИТ {i} ({zone.name}): пересечение не Polygon ({type(intersection).__name__})")
                continue
            
            # Точка в центре ПЕРЕСЕЧЕНИЯ
            centroid = intersection.centroid
            
            # Получаем реестровый номер
            registry_number = getattr(zone, 'registry_number', None) or zone.name or "ЗОУИТ"
            
            label_points.append({
                'x': centroid.x,
                'y': centroid.y,
                'registry_number': registry_number,
                'name': zone.name or "",
                'type': zone.type or ""
            })
            
            logger.info(f"  ✅ Точка подписи для '{zone.name}': X={centroid.x:.2f}, Y={centroid.y:.2f}")
            
        except Exception as e:
            logger.warning(f"Ошибка создания точки подписи для ЗОУИТ {i} ({zone.name}): {e}")
            continue
    
    if not label_points:
        logger.warning("Не создано ни одной точки подписи ЗОУИТ")
        return None
    
    logger.info(f"📍 Создано точек подписей: {len(label_points)}")
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'wb') as f:
        def w(text: str):
            f.write(text.encode('cp1251'))
        
        # Заголовок
        w('Version   450\n')
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f'{MSK42_COORDSYS}\n')
        
        # Поля
        w('Columns 3\n')
        w('  Реестровый_номер Char(254)\n')
        w('  Наименование Char(254)\n')
        w('  Тип Char(254)\n')
        w('Data\n\n')
        
        # Точки (невидимые)
        for point in label_points:
            w(f'Point {point["x"]} {point["y"]}\n')
            w('\n')
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'wb') as f:
        for point in label_points:
            registry_safe = safe_encode_cp1251(point['registry_number'])
            name_safe = safe_encode_cp1251(point['name'])
            type_safe = safe_encode_cp1251(point['type'])
            
            registry = escape_mif_string(registry_safe)
            name = escape_mif_string(name_safe)
            zone_type = escape_mif_string(type_safe)
            
            line = f'{registry},{name},{zone_type}\n'
            f.write(line.encode('cp1251'))
    
    logger.info(f"✅ Слой подписей ЗОУИТ создан: {mif_path.name}")
    
    return mif_path, mid_path


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def create_workspace_directory(cadnum: str) -> Path:
    """
    Создать рабочую директорию с правильной структурой.
    
    ✨ ОБНОВЛЕНО: Новая структура папок
    
    Структура:
    GP_Graphics_<cadnum>/
    ├── README.txt                    # Инструкция для пользователя
    ├── рабочий_набор.WOR            # Рабочий набор MapInfo
    └── База_проекта/                # Подпапка со всеми слоями
        ├── участок.TAB
        ├── участок_точки.TAB
        ├── зона_строительства.TAB
        ├── окс.TAB
        └── зоуит_*.TAB
    
    Args:
        cadnum: Кадастровый номер участка
    
    Returns:
        Path к созданной директории (корневая папка проекта)
    """
    
    import tempfile
    from pathlib import Path
    
    # Формируем имя папки: GP_Graphics_42:30:0102050:255
    safe_cadnum = cadnum.replace(':', '_')
    dir_name = f"GP_Graphics_{safe_cadnum}"
    
    # Создаём корневую директорию
    base_dir = Path("/home/gpzu-web/backend/temp/workspace") / dir_name
    base_dir.mkdir(parents=True, exist_ok=True)
    
    # Создаём подпапку "База проекта"
    project_base = base_dir / "База_проекта"
    project_base.mkdir(parents=True, exist_ok=True)
    
    # Создаём README.txt с инструкцией
    readme_path = base_dir / "README.txt"
    readme_content = f"""ГРАФИЧЕСКАЯ ЧАСТЬ ГРАДОСТРОИТЕЛЬНОГО ПЛАНА
Кадастровый номер: {cadnum}

СТРУКТУРА ПРОЕКТА:
==================

рабочий_набор.WOR       - Рабочий набор MapInfo (2 карты)
База_проекта/           - Папка со всеми слоями проекта

ИНСТРУКЦИЯ ПО ОТКРЫТИЮ:
=======================

1. Убедитесь что установлен MapInfo Professional
2. Откройте файл "рабочий_набор.WOR"
3. Автоматически откроются 2 карты:
   - Карта 1: Градостроительный план (детальная)
   - Карта 2: Ситуационный план (обзорная)

СОДЕРЖАНИЕ СЛОЁВ:
=================

База_проекта/ содержит:
  - участок.TAB              : Границы земельного участка
  - участок_точки.TAB        : Характерные точки границ
  - зона_строительства.TAB   : Минимальные отступы от границ (-5м)
  - окс.TAB                  : Объекты капитального строительства (если есть)
  - зоуит_*.TAB              : Зоны с особыми условиями использования (если есть)

КАРТА 1 (Градостроительный план):
  Показывает детальную информацию об участке, зоне строительства,
  объектах капстроительства и ограничениях (ЗОУИТ).

КАРТА 2 (Ситуационный план):
  Показывает расположение участка в контексте окружающей застройки,
  с адресными подписями, строениями и дорогами.

ПРИМЕЧАНИЯ:
===========

- Все файлы в кодировке Windows-1251 (CP1251)
- Система координат: МСК-42 зона 1
- Для корректного отображения требуется MapInfo Professional 7.0+

Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}
Создано автоматически системой GPZU-Web
"""
    
    with open(readme_path, 'w', encoding='cp1251') as f:
        f.write(readme_content)
    
    logger.info(f"Создана рабочая директория: {base_dir}")
    logger.info(f"  - Корневая папка: {base_dir.name}")
    logger.info(f"  - Подпапка слоёв: База_проекта")
    logger.info(f"  - README.txt создан")
    
    return base_dir


def get_project_base_dir(workspace_dir: Path) -> Path:
    """
    Получить путь к подпапке "База проекта".
    
    Args:
        workspace_dir: Корневая директория проекта
    
    Returns:
        Path к папке "База_проекта"
    """
    return workspace_dir / "База_проекта"


def cleanup_workspace_directory(workspace_dir: Path):
    """Удалить временную рабочую директорию."""
    try:
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
            logger.info(f"Удалена временная директория: {workspace_dir}")
    except Exception as e:
        logger.warning(f"Не удалось удалить директорию {workspace_dir}: {e}")


def get_mif_files_list(output_dir: Path) -> List[Path]:
    """Получить список всех MIF/MID файлов в директории."""
    output_dir = Path(output_dir)
    files = []
    
    extensions = ['.MIF', '.MID']
    for ext in extensions:
        files.extend(output_dir.glob(f'*{ext}'))
    
    logger.info(f"Найдено файлов MIF/MID: {len(files)}")
    return sorted(files)