# backend/generator/mif_writer.py
"""
Генератор MIF/MID файлов MapInfo для рабочего набора.

MIF (MapInfo Interchange Format) - текстовый формат MapInfo
Каждый слой состоит из двух файлов:
- .MIF - геометрия, структура полей, система координат
- .MID - атрибутивные данные

Преимущества перед TAB:
- Текстовый формат (легко проверять)
- Точный контроль над системой координат
- Совместимость с разными версиями MapInfo
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)


# ================ КОНСТАНТЫ ДИРЕКТОРИЙ ================ #

BASE_DIR = Path(__file__).resolve().parent.parent
TEMP_DIR = BASE_DIR / "temp" / "workspace"
TEMP_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# ================ СИСТЕМА КООРДИНАТ ================ #

# МСК-42 зона 2 (Кемеровская область, Новокузнецк)
# Projection 8 = Transverse Mercator (Gauss-Kruger)
# Datum 1001 = Pulkovo 1942
MSK42_COORDSYS = 'CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997 Bounds (-7786100, -9553200) (12213900, 10446800)'


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def escape_mif_string(s: str) -> str:
    """Экранировать строку для MIF/MID."""
    if s is None:
        return '""'
    # Заменяем кавычки на двойные кавычки
    s = str(s).replace('"', '""')
    return f'"{s}"'


def safe_encode_cp1251(s: str) -> str:
    """
    Безопасно подготовить строку для записи в CP1251.
    
    Проблема: Python получает строки в UTF-8 из spatial_analysis.py,
    и при записи в файл с encoding='cp1251' может происходить 
    некорректная конвертация символов.
    
    Решение: Явно конвертируем UTF-8 → CP1251, заменяя несовместимые символы.
    
    Args:
        s: Исходная строка (может быть в UTF-8)
    
    Returns:
        Строка, готовая для записи в файл с encoding='cp1251'
    """
    if s is None or s == '':
        return ''
    
    try:
        # Пробуем закодировать в CP1251
        # errors='replace' заменит несовместимые символы на '?'
        encoded = str(s).encode('cp1251', errors='replace')
        # Декодируем обратно для записи в файл
        return encoded.decode('cp1251')
    except Exception as e:
        logger.warning(f"Ошибка кодировки строки '{s[:50]}...': {e}")
        # Если не получилось, возвращаем ASCII-совместимую версию
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
    """
    Создать MIF/MID файлы земельного участка.
    
    Args:
        parcel_data: Объект ParcelLayer
        output_dir: Директория для сохранения
        filename: Имя файла без расширения
    
    Returns:
        Tuple[Path к MIF, Path к MID]
    """
    
    logger.info(f"Создание MIF/MID участка: {parcel_data.cadnum}")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    coords = parcel_data.coordinates
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('Version   450\n')
        f.write('Charset "WindowsCyrillic"\n')
        f.write('Delimiter ","\n')
        f.write(f'{MSK42_COORDSYS}\n')
        
        # Структура полей
        f.write('Columns 3\n')
        f.write('  Кадастровый_номер Char(254)\n')
        f.write('  Адрес Char(254)\n')
        f.write('  Площадь Float\n')
        f.write('Data\n\n')
        
        # Геометрия - Region (полигон)
        f.write('Region  1\n')
        f.write(f'  {len(coords)}\n')
        for x, y in coords:
            f.write(f'{x} {y}\n')
        
        # Стиль
        f.write('    Pen (1,2,0)\n')  # Черная линия, ширина 2
        f.write('    Brush (1,0,16777215)\n')  # Без заливки
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'w', encoding='cp1251') as f:
        # Безопасная конвертация в CP1251
        cadnum_safe = safe_encode_cp1251(parcel_data.cadnum)
        address_safe = safe_encode_cp1251(parcel_data.address or "")
        
        # Экранирование
        cadnum = escape_mif_string(cadnum_safe)
        address = escape_mif_string(address_safe)
        area = format_mif_number(parcel_data.area)
        
        f.write(f'{cadnum},{address},{area}\n')
    
    logger.info(f"MIF/MID участка созданы: {mif_path.name}, {mid_path.name}")
    logger.info(f"  Кадастровый номер: {parcel_data.cadnum}")
    logger.info(f"  Точек границы: {len(coords)}")
    
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ТОЧЕК УЧАСТКА ================ #

def create_parcel_points_mif(
    parcel_data: Any,
    output_dir: Path,
    filename: str = "участок_точки"
) -> Tuple[Path, Path]:
    """
    Создать MIF/MID файлы характерных точек участка.
    
    Args:
        parcel_data: Объект ParcelLayer
        output_dir: Директория для сохранения
        filename: Имя файла без расширения
    
    Returns:
        Tuple[Path к MIF, Path к MID]
    """
    
    logger.info("Создание MIF/MID точек участка")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    coords = parcel_data.coordinates
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('Version   450\n')
        f.write('Charset "WindowsCyrillic"\n')
        f.write('Delimiter ","\n')
        f.write(f'{MSK42_COORDSYS}\n')
        
        # Структура полей
        f.write('Columns 2\n')
        f.write('  Номер_точки Char(40)\n')
        f.write('  Кадастровый_номер Char(254)\n')
        f.write('Data\n\n')
        
        # Геометрия - Point для каждой точки
        for i, (x, y) in enumerate(coords, start=1):
            f.write(f'Point {x} {y}\n')
            f.write('    Symbol (34,6,12)\n')  # Кружок, размер 6
            f.write('\n')
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'w', encoding='cp1251') as f:
        cadnum_safe = safe_encode_cp1251(parcel_data.cadnum)
        cadnum = escape_mif_string(cadnum_safe)
        
        for i in range(len(coords)):
            num = escape_mif_string(str(i + 1))
            f.write(f'{num},{cadnum}\n')
    
    logger.info(f"MIF/MID точек создан: {mif_path.name}, точек: {len(coords)}")
    
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ЗОНЫ СТРОИТЕЛЬСТВА ================ #

def create_building_zone_mif(
    building_zone_data: Any,
    cadnum: str,
    output_dir: Path,
    filename: str = "зона_строительства"
) -> Tuple[Path, Path]:
    """
    Создать MIF/MID файлы зоны строительства.
    
    Args:
        building_zone_data: Объект BuildingZoneLayer
        cadnum: Кадастровый номер участка
        output_dir: Директория для сохранения
        filename: Имя файла без расширения
    
    Returns:
        Tuple[Path к MIF, Path к MID]
    """
    
    logger.info("Создание MIF/MID зоны строительства")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    if building_zone_data.geometry.is_empty:
        logger.warning("Зона строительства пустая!")
        # Создаем пустые файлы
        with open(mif_path, 'w', encoding='cp1251') as f:
            f.write('Version   450\n')
            f.write('Charset "WindowsCyrillic"\n')
            f.write(f'{MSK42_COORDSYS}\n')
            f.write('Columns 0\nData\n')
        
        with open(mid_path, 'w', encoding='cp1251') as f:
            pass
        
        return mif_path, mid_path
    
    coords = building_zone_data.coordinates
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('Version   450\n')
        f.write('Charset "WindowsCyrillic"\n')
        f.write('Delimiter ","\n')
        f.write(f'{MSK42_COORDSYS}\n')
        
        # Структура полей
        f.write('Columns 3\n')
        f.write('  Кадастровый_номер Char(254)\n')
        f.write('  Описание Char(254)\n')
        f.write('  Площадь Float\n')
        f.write('Data\n\n')
        
        # Геометрия - Region
        f.write('Region  1\n')
        f.write(f'  {len(coords)}\n')
        for x, y in coords:
            f.write(f'{x} {y}\n')
        
        # Стиль - линия потолще, штриховка
        f.write('    Pen (1,2,0)\n')  # Черная линия
        f.write('    Brush (2,0,16777215)\n')  # Штриховка
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'w', encoding='cp1251') as f:
        # Безопасная конвертация
        cadnum_safe = safe_encode_cp1251(cadnum)
        desc_safe = safe_encode_cp1251("Минимальные отступы от границ ЗУ")
        
        # Экранирование
        cadnum_str = escape_mif_string(cadnum_safe)
        desc = escape_mif_string(desc_safe)
        area = format_mif_number(building_zone_data.geometry.area)
        
        f.write(f'{cadnum_str},{desc},{area}\n')
    
    logger.info(f"MIF/MID зоны строительства созданы")
    logger.info(f"  Площадь зоны: {building_zone_data.geometry.area:.2f} кв.м")
    
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ОКС ================ #

def create_oks_mif(
    capital_objects: List[Any],
    output_dir: Path,
    filename: str = "окс"
) -> Optional[Tuple[Path, Path]]:
    """
    Создать MIF/MID файлы объектов капитального строительства.
    
    Args:
        capital_objects: Список объектов CapitalObjectInfo
        output_dir: Директория для сохранения
        filename: Имя файла без расширения
    
    Returns:
        Tuple[Path к MIF, Path к MID] или None если объектов нет
    """
    
    if not capital_objects:
        logger.info("Нет ОКС для создания MIF/MID")
        return None
    
    logger.info(f"Создание MIF/MID ОКС: {len(capital_objects)} объектов")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    # Фильтруем объекты с геометрией
    valid_objects = [obj for obj in capital_objects if obj.geometry is not None]
    
    if not valid_objects:
        logger.warning("Нет ОКС с геометрией")
        return None
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('Version   450\n')
        f.write('Charset "WindowsCyrillic"\n')
        f.write('Delimiter ","\n')
        f.write(f'{MSK42_COORDSYS}\n')
        
        # Структура полей
        f.write('Columns 6\n')
        f.write('  Номер Integer\n')
        f.write('  Кадастровый_номер Char(254)\n')
        f.write('  Тип_объекта Char(254)\n')
        f.write('  Назначение Char(254)\n')
        f.write('  Площадь Float\n')
        f.write('  Этажность Integer\n')
        f.write('Data\n\n')
        
        # Геометрия
        for i, obj in enumerate(valid_objects, start=1):
            geom = obj.geometry
            
            # Определяем тип геометрии
            if hasattr(geom, 'x') and hasattr(geom, 'y'):
                # Point
                f.write(f'Point {geom.x} {geom.y}\n')
                f.write('    Symbol (35,12,0)\n')  # Окружность
            elif hasattr(geom, 'exterior'):
                # Polygon
                coords = list(geom.exterior.coords)
                f.write('Region  1\n')
                f.write(f'  {len(coords)}\n')
                for x, y in coords:
                    f.write(f'{x} {y}\n')
                f.write('    Pen (1,2,0)\n')
                f.write('    Brush (1,0,16777215)\n')
            
            f.write('\n')
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'w', encoding='cp1251') as f:
        for i, obj in enumerate(valid_objects, start=1):
            num = str(i)
            
            # Безопасная конвертация в CP1251
            cadnum_safe = safe_encode_cp1251(obj.cadnum or "")
            type_safe = safe_encode_cp1251(obj.object_type or "")
            purpose_safe = safe_encode_cp1251(obj.purpose or "")
            
            # Экранирование
            cadnum = escape_mif_string(cadnum_safe)
            obj_type = escape_mif_string(type_safe)
            purpose = escape_mif_string(purpose_safe)
            
            area = format_mif_number(obj.area)
            floors = str(obj.floors) if obj.floors else "0"
            
            f.write(f'{num},{cadnum},{obj_type},{purpose},{area},{floors}\n')
    
    logger.info(f"MIF/MID ОКС созданы: {len(valid_objects)} объектов")
    
    return mif_path, mid_path


# ================ СОЗДАНИЕ MIF/MID ЗОУИТ ================ #

def create_zouit_mif(
    zouit_list: List[Any],
    output_dir: Path,
    filename: str = "зоуит"
) -> Optional[Tuple[Path, Path]]:
    """
    Создать MIF/MID файлы ЗОУИТ.
    
    Args:
        zouit_list: Список объектов ZouitInfo
        output_dir: Директория для сохранения
        filename: Имя файла без расширения
    
    Returns:
        Tuple[Path к MIF, Path к MID] или None если зон нет
    """
    
    if not zouit_list:
        logger.info("Нет ЗОУИТ для создания MIF/MID")
        return None
    
    logger.info(f"Создание MIF/MID ЗОУИТ: {len(zouit_list)} зон")
    
    output_dir = Path(output_dir)
    mif_path = output_dir / f"{filename}.MIF"
    mid_path = output_dir / f"{filename}.MID"
    
    # Фильтруем зоны с геометрией
    valid_zones = [z for z in zouit_list if z.geometry is not None]
    
    if not valid_zones:
        logger.warning("Нет ЗОУИТ с геометрией")
        return None
    
    # ========== Создание MIF ========== #
    
    with open(mif_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('Version   450\n')
        f.write('Charset "WindowsCyrillic"\n')
        f.write('Delimiter ","\n')
        f.write(f'{MSK42_COORDSYS}\n')
        
        # Структура полей
        f.write('Columns 3\n')
        f.write('  Наименование Char(254)\n')
        f.write('  Тип Char(254)\n')
        f.write('  Ограничения Char(254)\n')
        f.write('Data\n\n')
        
        # Геометрия
        for zone in valid_zones:
            geom = zone.geometry
            
            if hasattr(geom, 'exterior'):
                # Polygon
                coords = list(geom.exterior.coords)
                f.write('Region  1\n')
                f.write(f'  {len(coords)}\n')
                for x, y in coords:
                    f.write(f'{x} {y}\n')
                f.write('    Pen (1,2,0)\n')
                f.write('    Brush (2,16776960,16777215)\n')  # Желтая заливка
            
            f.write('\n')
    
    # ========== Создание MID ========== #
    
    with open(mid_path, 'w', encoding='cp1251') as f:
        for zone in valid_zones:
            # ✅ ИСПРАВЛЕНИЕ: Безопасная конвертация UTF-8 → CP1251
            name_safe = safe_encode_cp1251(zone.name or "")
            type_safe = safe_encode_cp1251(zone.type or "")
            restriction_safe = safe_encode_cp1251(zone.restriction or "")
            
            # Экранирование для MIF
            name = escape_mif_string(name_safe)
            ztype = escape_mif_string(type_safe)
            restriction = escape_mif_string(restriction_safe)
            
            f.write(f'{name},{ztype},{restriction}\n')
    
    logger.info(f"MIF/MID ЗОУИТ созданы: {len(valid_zones)} зон")
    
    return mif_path, mid_path


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def create_workspace_directory(cadnum: str) -> Path:
    """Создать временную рабочую директорию."""
    from datetime import datetime
    
    safe_cadnum = cadnum.replace(":", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{safe_cadnum}_{timestamp}"
    workspace_dir = TEMP_DIR / dir_name
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Создана рабочая директория: {workspace_dir}")
    
    return workspace_dir


def cleanup_workspace_directory(workspace_dir: Path):
    """Удалить временную рабочую директорию."""
    try:
        if workspace_dir.exists():
            shutil.rmtree(workspace_dir)
            logger.info(f"Удалена временная директория: {workspace_dir}")
    except Exception as e:
        logger.warning(f"Не удалось удалить директорию {workspace_dir}: {e}")


def get_mif_files_list(output_dir: Path) -> List[Path]:
    """
    Получить список всех MIF/MID файлов в директории.
    
    Returns:
        Список путей ко всем файлам
    """
    
    output_dir = Path(output_dir)
    files = []
    
    # Расширения MIF/MID
    extensions = ['.MIF', '.MID']
    
    for ext in extensions:
        files.extend(output_dir.glob(f'*{ext}'))
    
    logger.info(f"Найдено файлов MIF/MID: {len(files)}")
    
    return sorted(files)