# backend/generator/mif_to_tab_converter.py
"""
Конвертер MIF/MID файлов в TAB формат MapInfo.

MIF (MapInfo Interchange Format) - текстовый формат, легко создаётся
TAB (MapInfo Native Format) - бинарный формат, требуется для WOR

Workflow:
1. Создаём MIF/MID с правильной системой координат
2. Конвертируем MIF → TAB используя GDAL/OGR
3. Удаляем MIF/MID (опционально)
4. Используем TAB в WOR-файле
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple
import logging
import subprocess
import shutil

logger = logging.getLogger(__name__)

try:
    import geopandas as gpd
    from osgeo import ogr, osr
    GDAL_AVAILABLE = True
except ImportError:
    GDAL_AVAILABLE = False
    logger.warning("GDAL/OGR не установлен - конвертация MIF→TAB будет использовать subprocess")


# ================ КОНВЕРТАЦИЯ MIF → TAB ================ #

def convert_mif_to_tab_gdal(
    mif_path: Path,
    output_tab_path: Optional[Path] = None,
    remove_mif: bool = False
) -> Path:
    """
    Конвертировать MIF в TAB используя GDAL/OGR напрямую.
    
    Args:
        mif_path: Путь к MIF файлу
        output_tab_path: Путь для TAB (если None - та же директория)
        remove_mif: Удалить MIF после конвертации
    
    Returns:
        Path к созданному TAB файлу
    """
    
    if not GDAL_AVAILABLE:
        raise ImportError("GDAL/OGR не установлен. Используйте convert_mif_to_tab_subprocess")
    
    mif_path = Path(mif_path)
    
    if output_tab_path is None:
        output_tab_path = mif_path.with_suffix('.tab')
    else:
        output_tab_path = Path(output_tab_path)
    
    logger.info(f"Конвертация MIF→TAB (GDAL): {mif_path.name} → {output_tab_path.name}")
    
    try:
        # Открываем MIF
        mif_ds = ogr.Open(str(mif_path))
        if mif_ds is None:
            raise ValueError(f"Не удалось открыть MIF: {mif_path}")
        
        # Создаём TAB драйвер
        tab_driver = ogr.GetDriverByName('MapInfo File')
        if tab_driver is None:
            raise ValueError("MapInfo File драйвер не найден в GDAL")
        
        # Удаляем существующий TAB если есть
        if output_tab_path.exists():
            tab_driver.DeleteDataSource(str(output_tab_path))
        
        # Копируем MIF в TAB
        tab_ds = tab_driver.CopyDataSource(mif_ds, str(output_tab_path))
        
        if tab_ds is None:
            raise ValueError("Не удалось создать TAB файл")
        
        # Закрываем датасеты
        mif_ds = None
        tab_ds = None
        
        logger.info(f"✅ TAB создан: {output_tab_path}")
        
        # Удаляем MIF если требуется
        if remove_mif:
            _remove_mif_files(mif_path)
        
        return output_tab_path
        
    except Exception as e:
        logger.error(f"Ошибка конвертации MIF→TAB: {e}")
        raise


def convert_mif_to_tab_geopandas(
    mif_path: Path,
    output_tab_path: Optional[Path] = None,
    remove_mif: bool = False
) -> Path:
    """
    Конвертировать MIF в TAB используя geopandas.
    
    ВНИМАНИЕ: Этот метод может потерять правильную систему координат!
    Используйте convert_mif_to_tab_gdal если возможно.
    
    Args:
        mif_path: Путь к MIF файлу
        output_tab_path: Путь для TAB
        remove_mif: Удалить MIF после конвертации
    
    Returns:
        Path к созданному TAB файлу
    """
    
    mif_path = Path(mif_path)
    
    if output_tab_path is None:
        output_tab_path = mif_path.with_suffix('.tab')
    else:
        output_tab_path = Path(output_tab_path)
    
    logger.info(f"Конвертация MIF→TAB (geopandas): {mif_path.name}")
    logger.warning("ВНИМАНИЕ: geopandas может потерять систему координат!")
    
    try:
        # Читаем MIF
        gdf = gpd.read_file(mif_path)
        
        # Сохраняем как TAB
        gdf.to_file(output_tab_path, driver='MapInfo File')
        
        logger.info(f"✅ TAB создан: {output_tab_path}")
        
        # Удаляем MIF если требуется
        if remove_mif:
            _remove_mif_files(mif_path)
        
        return output_tab_path
        
    except Exception as e:
        logger.error(f"Ошибка конвертации MIF→TAB (geopandas): {e}")
        raise


def convert_mif_to_tab_subprocess(
    mif_path: Path,
    output_tab_path: Optional[Path] = None,
    remove_mif: bool = False
) -> Path:
    """
    Конвертировать MIF в TAB используя ogr2ogr command-line утилиту.
    
    Требуется установленный GDAL в системе.
    
    Args:
        mif_path: Путь к MIF файлу
        output_tab_path: Путь для TAB
        remove_mif: Удалить MIF после конвертации
    
    Returns:
        Path к созданному TAB файлу
    """
    
    mif_path = Path(mif_path)
    
    if output_tab_path is None:
        output_tab_path = mif_path.with_suffix('.tab')
    else:
        output_tab_path = Path(output_tab_path)
    
    logger.info(f"Конвертация MIF→TAB (ogr2ogr): {mif_path.name}")
    
    try:
        # Удаляем существующий TAB
        if output_tab_path.exists():
            _remove_tab_files(output_tab_path)
        
        # Команда ogr2ogr
        cmd = [
            'ogr2ogr',
            '-f', 'MapInfo File',
            str(output_tab_path),
            str(mif_path)
        ]
        
        # Выполняем команду
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not output_tab_path.exists():
            raise ValueError(f"TAB файл не создан: {output_tab_path}")
        
        logger.info(f"✅ TAB создан: {output_tab_path}")
        
        # Удаляем MIF если требуется
        if remove_mif:
            _remove_mif_files(mif_path)
        
        return output_tab_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка ogr2ogr: {e.stderr}")
        raise
    except FileNotFoundError:
        logger.error("ogr2ogr не найден! Установите GDAL.")
        raise


def convert_mif_to_tab(
    mif_path: Path,
    output_tab_path: Optional[Path] = None,
    remove_mif: bool = False,
    method: str = 'auto'
) -> Path:
    """
    Конвертировать MIF в TAB (автоматический выбор метода).
    
    Args:
        mif_path: Путь к MIF файлу
        output_tab_path: Путь для TAB
        remove_mif: Удалить MIF после конвертации
        method: Метод конвертации ('auto', 'gdal', 'subprocess', 'geopandas')
    
    Returns:
        Path к созданному TAB файлу
    """
    
    if method == 'auto':
        # Пробуем в порядке приоритета
        if GDAL_AVAILABLE:
            return convert_mif_to_tab_gdal(mif_path, output_tab_path, remove_mif)
        else:
            # Пробуем subprocess
            try:
                return convert_mif_to_tab_subprocess(mif_path, output_tab_path, remove_mif)
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.warning("ogr2ogr недоступен, используем geopandas (может потерять проекцию)")
                return convert_mif_to_tab_geopandas(mif_path, output_tab_path, remove_mif)
    
    elif method == 'gdal':
        return convert_mif_to_tab_gdal(mif_path, output_tab_path, remove_mif)
    
    elif method == 'subprocess':
        return convert_mif_to_tab_subprocess(mif_path, output_tab_path, remove_mif)
    
    elif method == 'geopandas':
        return convert_mif_to_tab_geopandas(mif_path, output_tab_path, remove_mif)
    
    else:
        raise ValueError(f"Неизвестный метод: {method}")


# ================ КОНВЕРТАЦИЯ ВСЕХ MIF В ДИРЕКТОРИИ ================ #

def convert_all_mif_to_tab(
    directory: Path,
    remove_mif: bool = False,
    method: str = 'auto'
) -> List[Path]:
    """
    Конвертировать все MIF файлы в директории в TAB.
    
    Args:
        directory: Директория с MIF файлами
        remove_mif: Удалить MIF после конвертации
        method: Метод конвертации
    
    Returns:
        Список созданных TAB файлов
    """
    
    directory = Path(directory)
    mif_files = list(directory.glob('*.MIF')) + list(directory.glob('*.mif'))
    
    logger.info(f"Найдено MIF файлов: {len(mif_files)} в {directory}")
    
    tab_files = []
    
    for mif_file in mif_files:
        try:
            tab_file = convert_mif_to_tab(
                mif_path=mif_file,
                remove_mif=remove_mif,
                method=method
            )
            tab_files.append(tab_file)
        except Exception as e:
            logger.error(f"Не удалось конвертировать {mif_file.name}: {e}")
    
    logger.info(f"✅ Конвертировано MIF→TAB: {len(tab_files)} файлов")
    
    return tab_files


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def _remove_mif_files(mif_path: Path):
    """Удалить MIF и связанный MID файл."""
    mif_path = Path(mif_path)
    mid_path = mif_path.with_suffix('.MID')
    
    try:
        if mif_path.exists():
            mif_path.unlink()
            logger.info(f"Удалён MIF: {mif_path.name}")
        
        if mid_path.exists():
            mid_path.unlink()
            logger.info(f"Удалён MID: {mid_path.name}")
    
    except Exception as e:
        logger.warning(f"Не удалось удалить MIF/MID: {e}")


def _remove_tab_files(tab_path: Path):
    """Удалить TAB и все связанные файлы (.dat, .id, .map)."""
    tab_path = Path(tab_path)
    
    extensions = ['.tab', '.TAB', '.dat', '.DAT', '.id', '.ID', '.map', '.MAP']
    
    for ext in extensions:
        file_path = tab_path.with_suffix(ext)
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Не удалось удалить {file_path.name}: {e}")


def get_tab_files_list(directory: Path) -> List[Path]:
    """Получить список всех TAB файлов в директории."""
    directory = Path(directory)
    
    tab_files = list(directory.glob('*.tab')) + list(directory.glob('*.TAB'))
    
    return sorted(tab_files)


# ================ ПРИМЕР ИСПОЛЬЗОВАНИЯ ================ #

if __name__ == "__main__":
    import tempfile
    
    print("=" * 60)
    print("ТЕСТ: Конвертация MIF → TAB")
    print("=" * 60)
    
    # Создаём тестовую директорию
    test_dir = Path(tempfile.mkdtemp())
    
    # Создаём тестовый MIF (пустышка)
    test_mif = test_dir / "test.MIF"
    test_mid = test_dir / "test.MID"
    
    with open(test_mif, 'w', encoding='cp1251') as f:
        f.write('''Version 450
Charset "WindowsCyrillic"
CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997
Columns 1
  Name Char(50)
Data

Point 2220706.74 449672.33
    Symbol (34,6,12)
''')
    
    with open(test_mid, 'w', encoding='cp1251') as f:
        f.write('"Test Point"\n')
    
    print(f"Создан тестовый MIF: {test_mif}")
    
    # Конвертация
    try:
        tab_file = convert_mif_to_tab(test_mif, method='auto')
        print(f"\n✅ TAB создан: {tab_file}")
        
        # Проверяем что создалось
        tab_files = get_tab_files_list(test_dir)
        print(f"\nФайлы TAB в директории: {len(tab_files)}")
        for f in tab_files:
            print(f"  - {f.name}")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    
    print("\n" + "=" * 60)