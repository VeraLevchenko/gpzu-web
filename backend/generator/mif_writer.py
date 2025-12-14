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
    filename: str = "зоуит"  # Параметр игнорируется, оставлен для совместимости
) -> Optional[List[Tuple[Path, Path]]]:
    """
    Создать отдельные MIF/MID файлы для каждой ЗОУИТ.
    
    ✨ НОВОЕ: Каждая зона создается в отдельном слое (файле).
    ✨ БЕЗ заливки - только контур.
    
    Args:
        zouit_list: Список объектов ZouitInfo
        output_dir: Директория для сохранения
        filename: Не используется (для совместимости)
    
    Returns:
        Список кортежей (Path к MIF, Path к MID) для каждой зоны
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
    
    created_files = []
    
    # Создаем отдельный слой для каждой зоны
    for i, zone in enumerate(valid_zones, start=1):
        
        # Формируем имя файла из типа зоны
        # Убираем недопустимые символы для имени файла
        safe_name = zone.type or zone.name or f"зона_{i}"
        safe_name = safe_name.replace("/", "_").replace("\\", "_")
        safe_name = safe_name.replace(":", "_").replace("*", "_")
        safe_name = safe_name.replace("?", "_").replace('"', "_")
        safe_name = safe_name.replace("<", "_").replace(">", "_")
        safe_name = safe_name.replace("|", "_").strip()
        
        # Ограничиваем длину имени
        if len(safe_name) > 40:
            safe_name = safe_name[:40]
        
        filename_base = f"зоуит_{i}_{safe_name}"
        
        mif_path = output_dir / f"{filename_base}.MIF"
        mid_path = output_dir / f"{filename_base}.MID"
        
        # ========== Создание MIF ========== #
        
        with open(mif_path, 'wb') as f:
            def w(text: str):
                f.write(text.encode('cp1251'))
            
            # Заголовок
            w('Version   450\n')
            w('Charset "WindowsCyrillic"\n')
            w('Delimiter ","\n')
            w(f'{MSK42_COORDSYS}\n')
            
            # Структура полей
            w('Columns 3\n')
            w('  Наименование Char(254)\n')
            w('  Тип Char(254)\n')
            w('  Ограничения Char(254)\n')
            w('Data\n\n')
            
            # Геометрия
            geom = zone.geometry
            
            if hasattr(geom, 'exterior'):
                # Polygon
                coords = list(geom.exterior.coords)
                w('Region  1\n')
                w(f'  {len(coords)}\n')
                for x, y in coords:
                    w(f'{x} {y}\n')
                
                # ✨ БЕЗ ЗАЛИВКИ - только контур
                w('    Pen (1,2,0)\n')  # Черная линия, ширина 2
                w('    Brush (1,0,16777215)\n')  # Прозрачная заливка
            
            w('\n')
        
        # ========== Создание MID ========== #
        
        with open(mid_path, 'wb') as f:
            # Безопасная конвертация UTF-8 → CP1251
            name_safe = safe_encode_cp1251(zone.name or "")
            type_safe = safe_encode_cp1251(zone.type or "")
            restriction_safe = safe_encode_cp1251(zone.restriction or "")
            
            # Экранирование для MIF
            name = escape_mif_string(name_safe)
            ztype = escape_mif_string(type_safe)
            restriction = escape_mif_string(restriction_safe)
            
            line = f'{name},{ztype},{restriction}\n'
            f.write(line.encode('cp1251'))
        
        created_files.append((mif_path, mid_path))
        logger.info(f"  ✅ Слой ЗОУИТ {i}: {safe_name}")
    
    logger.info(f"✅ Создано отдельных слоёв ЗОУИТ: {len(created_files)}")
    
    return created_files


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
    """Получить список всех MIF/MID файлов в директории."""
    output_dir = Path(output_dir)
    files = []
    
    extensions = ['.MIF', '.MID']
    for ext in extensions:
        files.extend(output_dir.glob(f'*{ext}'))
    
    logger.info(f"Найдено файлов MIF/MID: {len(files)}")
    return sorted(files)