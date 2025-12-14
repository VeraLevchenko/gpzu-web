# backend/generator/wor_builder.py
"""
Генератор WOR-файлов (рабочий набор MapInfo).

WOR (Workspace) - это текстовый файл MapInfo который содержит:
- Список открытых таблиц (слоев)
- Настройки Map Window (карта)
- Настройки Layout Window (компоновка для печати)
- Стили отображения слоев
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


# ЗАМЕНИТЕ ФУНКЦИЮ create_workspace_wor в backend/generator/wor_builder.py

def create_workspace_wor(
    workspace_dir: Path,
    cadnum: str,
    has_oks: bool = False,
    zouit_files: Optional[List[Tuple[Path, Path]]] = None,  # ✅ ИЗМЕНЕНО
    red_lines_path: str = "/mnt/graphics/NOVOKUZ/Красные_линии.TAB",
    use_absolute_paths: bool = False
) -> Path:
    """
    Создать WOR-файл рабочего набора.
    
    ✨ ОБНОВЛЕНО: Поддержка отдельных слоёв для каждой ЗОУИТ.
    
    Рабочий набор содержит:
    - Map Window с открытыми слоями
    - Layout Window с рамкой А3, штампом, легендой
    
    Args:
        workspace_dir: Директория со слоями MIF/MID
        cadnum: Кадастровый номер участка
        has_oks: Есть ли слой ОКС
        zouit_files: Список файлов ЗОУИТ [(mif, mid), ...] или None  # ✅ ИЗМЕНЕНО
        red_lines_path: Путь к слою красных линий
        use_absolute_paths: Использовать абсолютные пути к MIF файлам
    
    Returns:
        Path к созданному WOR-файлу
    """
    
    logger.info(f"Создание WOR-файла рабочего набора для {cadnum}")
    
    workspace_dir = Path(workspace_dir)
    wor_path = workspace_dir / "рабочий_набор.WOR"
    
    # Формируем список слоёв для Map From
    map_layers = ["участок", "участок_точки", "зона_строительства"]
    if has_oks:
        map_layers.append("окс")
    
    # ✅ ОБНОВЛЕНО: Добавляем каждый слой ЗОУИТ
    if zouit_files:
        for i, (mif_path, _) in enumerate(zouit_files, start=1):
            layer_name = mif_path.stem  # Имя без расширения
            map_layers.append(layer_name)
    
    map_from_str = ",".join(map_layers)
    
    # ========== Создание WOR-файла ========== #
    
    wor_content = '''!Workspace
!Version  950
!Charset WindowsCyrillic
Open Table "участок.MIF" As участок Interactive
Open Table "участок_точки.MIF" As участок_точки Interactive
Open Table "зона_строительства.MIF" As зона_строительства Interactive
'''
    
    if has_oks:
        wor_content += 'Open Table "окс.MIF" As окс Interactive\n'
    
    # ✅ ОБНОВЛЕНО: Открываем каждый файл ЗОУИТ отдельно
    if zouit_files:
        for i, (mif_path, _) in enumerate(zouit_files, start=1):
            filename = mif_path.name
            table_name = mif_path.stem
            wor_content += f'Open Table "{filename}" As {table_name} Interactive\n'
    
    wor_content += f'''Map From {map_from_str} 
  Position (0.0520833,0.0520833) Units "in"
  Width 9.91667 Units "in" Height 7 Units "in" 
Set Window FrontWindow() ScrollBars Off Autoscroll On Enhanced On Smooth Text Antialias Image High
Set Map
  CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997
  Zoom Entire Layer 1
  Preserve Zoom Display Zoom
  Distance Units "m" Area Units "sq m" XY Units "m"
Set Map
  Layer 1
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
  Layer 2
    Display Graphic
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
  Layer 3
    Display Graphic
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
Set Window FrontWindow() Printer
 Name "PDF24" Orientation Portrait Copies 1
 Papersize 9
Dim WorkspaceMaximizedWindow As Integer
WorkspaceMaximizedWindow = Frontwindow()
Set Window WorkspaceMaximizedWindow Max
Undim WorkspaceMaximizedWindow
'''
    
    # Записываем файл в правильной кодировке
    with open(wor_path, 'wb') as f:
        f.write(wor_content.encode('cp1251'))
        
    
    logger.info(f"WOR-файл создан: {wor_path}")
    logger.info(f"  Слоёв в рабочем наборе: {len(map_layers)}")
    logger.info(f"  - Участок (полигон + точки)")
    logger.info(f"  - Зона строительства")
    if has_oks:
        logger.info(f"  - ОКС")
    if zouit_files:
        logger.info(f"  - ЗОУИТ: {len(zouit_files)} отдельных слоёв")
    
    return wor_path

def create_simple_wor(
    workspace_dir: Path,
    mif_files: List[str]
) -> Path:
    """
    Создать простой WOR-файл только с Map Window (без Layout).
    
    Используется для быстрого просмотра слоёв.
    
    Args:
        workspace_dir: Директория со слоями
        mif_files: Список имён MIF-файлов для открытия
    
    Returns:
        Path к созданному WOR-файлу
    """
    
    logger.info("Создание простого WOR-файла (только Map Window)")
    
    workspace_dir = Path(workspace_dir)
    wor_path = workspace_dir / "карта.WOR"
    
    with open(wor_path, 'w', encoding='cp1251') as f:
        # Заголовок
        f.write('!table\n')
        f.write('!version 300\n')
        f.write('!charset WindowsCyrillic\n\n')
        
        # Открытие таблиц
        for mif_file in mif_files:
            table_name = Path(mif_file).stem
            f.write(f'Open Table "{mif_file}" As {table_name} Interactive\n')
        
        f.write('\n')
        
        # Map Window
        if mif_files:
            first_table = Path(mif_files[0]).stem
            f.write(f'Map From {first_table}\n')
        
        f.write('Set Map\n')
        f.write('  Layer 1\n')
        f.write('  Display Graphic\n')
        f.write('  Display Global\n')
        f.write('Set Window WIN1\n')
        f.write('  Show\n')
    
    logger.info(f"Простой WOR-файл создан: {wor_path}")
    
    return wor_path


# ================ ПРИМЕР ИСПОЛЬЗОВАНИЯ ================ #

if __name__ == "__main__":
    from pathlib import Path
    
    # Тестовый пример
    test_dir = Path("/tmp/test_workspace")
    test_dir.mkdir(exist_ok=True)
    
    # Создаем тестовые MIF файлы (пустые)
    for filename in ["участок.MIF", "участок_точки.MIF", "зона_строительства.MIF"]:
        (test_dir / filename).touch()
    
    print("=" * 60)
    print("ТЕСТ: Создание WOR-файла")
    print("=" * 60)
    
    # Создаем WOR с Layout
    wor_path = create_workspace_wor(
        workspace_dir=test_dir,
        cadnum="42:30:0102050:255",
        has_oks=False,
        has_zouit=False
    )
    
    print(f"\n✅ WOR-файл создан: {wor_path}")
    print(f"Размер: {wor_path.stat().st_size} байт")
    
    # Показываем содержимое
    print(f"\nСодержимое WOR-файла:")
    print("-" * 60)
    with open(wor_path, 'r', encoding='cp1251') as f:
        print(f.read())
    
    print("=" * 60)