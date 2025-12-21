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
    zouit_files: Optional[List[Tuple[Path, Path]]] = None,
    has_zouit_labels: bool = False,
    red_lines_path: str = "/mnt/graphics/NOVOKUZ/Красные_линии.TAB",
    use_absolute_paths: bool = False
) -> Path:
    """
    Создать WOR-файл рабочего набора с правильными стилями.
    
    ✨ ЦВЕТОВАЯ СХЕМА:
    КАРТА 1 (Градплан):
    - Точки участка: КРАСНЫЕ кружки с подписями номеров (включены)
    - Зона строительства: КРАСНАЯ штриховка
    - ЗОУИТ: ЧЁРНЫЕ линии без заливки
    - Участок: КРАСНАЯ жирная линия (17,2)
    
    КАРТА 2 (Ситуационный план):
    - Участок: КРАСНАЯ жирная линия
    - Остальные слои: обычное отображение
    
    Args:
        workspace_dir: Корневая директория проекта
        cadnum: Кадастровый номер участка
        has_oks: Есть ли слой ОКС
        zouit_files: Список файлов ЗОУИТ [(mif, mid), ...]
        red_lines_path: Путь к слою красных линий
        use_absolute_paths: Использовать абсолютные пути
    
    Returns:
        Path к созданному WOR-файлу
    """
    
    from core.layers_config import LayerPaths
    
    logger.info(f"Создание WOR-файла с красивыми цветами для {cadnum}")
    
    workspace_dir = Path(workspace_dir)
    wor_path = workspace_dir / "рабочий_набор.WOR"
    
    # Относительный путь к папке со слоями
    layers_subdir = "База_проекта"
    
    # ========== КАРТА 1: Основная (градплан) ========== #
    
    # Порядок слоёв (снизу вверх):
    map1_layers = []
    
    # 1. ОКС (если есть) - самый нижний слой
    if has_oks:
        map1_layers.append("окс")
    
    # 2. Точки участка
    map1_layers.append("участок_точки")
    
    # 3. Зона строительства
    map1_layers.append("зона_строительства")
    
    # 4. ЗОУИТ (если есть)
    if zouit_files:
        for mif_path, _ in zouit_files:
            map1_layers.append(mif_path.stem)
    
    # 4-Б. Подписи ЗОУИТ (если есть)
    if has_zouit_labels:
        map1_layers.append("зоуит_подписи")
    
    # 5. Участок - самый верхний слой
    map1_layers.append("участок")
    
    map1_from_str = ",".join(map1_layers)
    
    # ========== КАРТА 2: Ситуационный план ========== #
    
    situation_layers = LayerPaths.get_situation_map_layers()
    
    map2_layers = ["участок", "Подписи", "ACTUAL_LAND", "Строения", "Проезды"]
    map2_from_str = ",".join(map2_layers)
    
    # ========== Создание содержимого WOR-файла ========== #
    
    wor_content = '''!Workspace
!Version  950
!Charset WindowsCyrillic
'''
    
    # ========== Открываем таблицы ========== #
    
    # Таблицы из подпапки "База_проекта"
    wor_content += f'Open Table "{layers_subdir}\\\\участок.TAB" As участок Interactive\n'
    wor_content += f'Open Table "{layers_subdir}\\\\участок_точки.TAB" As участок_точки Interactive\n'
    wor_content += f'Open Table "{layers_subdir}\\\\зона_строительства.TAB" As зона_строительства Interactive\n'
    
    if has_oks:
        wor_content += f'Open Table "{layers_subdir}\\\\окс.TAB" As окс Interactive\n'
    
    # Открываем каждый файл ЗОУИТ
    if zouit_files:
        for mif_path, _ in zouit_files:
            filename = mif_path.name.replace('.MIF', '.TAB')
            table_name = mif_path.stem
            wor_content += f'Open Table "{layers_subdir}\\\\{filename}" As {table_name} Interactive\n'
    
    # Открываем слой подписей ЗОУИТ (если есть)
    if has_zouit_labels:
        wor_content += f'Open Table "{layers_subdir}\\\\зоуит_подписи.TAB" As зоуит_подписи Interactive\n'
    
    # Открываем внешние слои для карты 2
    for layer_path in situation_layers:
        if layer_path.exists():
            layer_name = layer_path.stem
            wor_content += f'Open Table "{layer_path}" As {layer_name} Interactive\n'
    
    # ========== КАРТА 1: Градостроительный план ========== #
    
    wor_content += f'''Map From {map1_from_str} 
  Position (0.0520833,0.0520833) Units "in"
  Width 9.91667 Units "in" Height 7 Units "in" 
Set Window FrontWindow() ScrollBars Off Autoscroll On Enhanced On Smooth Text Antialias Image High
Set Map
  CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997
  Zoom Entire Layer 1
  Preserve Zoom Display Zoom
  Distance Units "m" Area Units "sq m" XY Units "m"
'''
    
    # ========== СТИЛИ СЛОЁВ КАРТЫ 1 ========== #
    
    layer_index = 1
    
    # ✅ СЛОЙ: ОКС (если есть)
    if has_oks:
        wor_content += f'''Set Map
  Layer {layer_index}
    Display Graphic
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
'''
        layer_index += 1
    
    # ✅ СЛОЙ: Точки участка (КРАСНЫЕ КРУЖКИ С ПОДПИСЯМИ)
    wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (34,16711680,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line None Position Right Font ("Arial CYR",256,9,16711680,16777215) Pen (1,2,0) 
      With Номер_точки
      Parallel On Auto Off Overlap Off Duplicates On Offset 4
      Visibility On
'''
    layer_index += 1
    
    # ✅ СЛОЙ: Зона строительства (КРАСНАЯ ШТРИХОВКА)
    wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (1,2,16711680) Brush (44,16711680) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Кадастровый_номе
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
'''
    layer_index += 1
    
    # ✅ СЛОИ: ЗОУИТ (ЧЁРНЫЕ ЛИНИИ БЕЗ ЗАЛИВКИ, БЕЗ ПОДПИСЕЙ)
    if zouit_files:
        for i, (mif_path, _) in enumerate(zouit_files):
            # Чёрная линия, без заливки, БЕЗ подписей
            wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
'''
            layer_index += 1
    
    # ✅ СЛОЙ: Подписи ЗОУИТ (НЕВИДИМЫЕ ТОЧКИ С ПОДПИСЯМИ)
    if has_zouit_labels:
        wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Symbol (31,0,0)
    Label Line None Position Center Font ("Arial CYR",256,10,0,16777215) Pen (1,2,0) 
      With Реестровый_номер
      Parallel On Auto On Overlap Off Duplicates On Offset 2
      Visibility On
'''
        layer_index += 1
    
    # ✅ СЛОЙ: Участок (КРАСНАЯ ЖИРНАЯ ЛИНИЯ)
    wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (17,2,16711680) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
'''
    
    wor_content += '''Set Window FrontWindow() Printer
 Name "PDF24" Orientation Portrait Copies 1
 Papersize 9
'''
    
    # ========== КАРТА 2: Ситуационный план ========== #
    
    wor_content += f'''Map From {map2_from_str} 
  Position (0.572917,0.697917) Units "in"
  Width 7.8125 Units "in" Height 4.71875 Units "in" 
Set Window FrontWindow() ScrollBars Off Autoscroll On Enhanced On Smooth Text Antialias Image High
Set Map
  CoordSys Earth Projection 8, 1001, "m", 88.46666666666, 0, 1, 2300000, -5512900.5719999997
  Zoom Entire Layer 1
  Preserve Zoom Display Zoom
  Distance Units "m" Area Units "sq m" XY Units "m"
  Distance Type Cartesian
'''
    
    # ========== СТИЛИ СЛОЁВ КАРТЫ 2 ========== #
    
    # Слой 1: Участок (КРАСНАЯ ЖИРНАЯ ЛИНИЯ)
    wor_content += '''Set Map
  Layer 1
    Display Global
    Global Pen (17,2,16711680) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
'''
    
    # Остальные слои: обычное отображение
    for i in range(2, len(map2_layers) + 1):
        wor_content += f'''  Layer {i}
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
'''
    
    wor_content += '''Set Window FrontWindow() Printer
 Name "PDF24" Orientation Portrait Copies 1
 Papersize 9
'''
    
    # ========== Финализация ========== #
    
    wor_content += '''Dim WorkspaceMaximizedWindow As Integer
WorkspaceMaximizedWindow = Frontwindow()
Set Window WorkspaceMaximizedWindow Max
Undim WorkspaceMaximizedWindow
'''
    
    # ========== Запись файла ========== #
    
    with open(wor_path, 'wb') as f:
        f.write(wor_content.encode('cp1251'))
    
    # ========== Логирование ========== #
    
    logger.info(f"WOR-файл создан: {wor_path}")
    logger.info(f"  Слои используют относительные пути: {layers_subdir}\\")
    logger.info(f"  КАРТА 1: {len(map1_layers)} слоёв")
    logger.info(f"    - Точки участка: красные кружки с подписями")
    logger.info(f"    - Зона строительства: красная штриховка")
    if zouit_files:
        logger.info(f"    - ЗОУИТ: {len(zouit_files)} слоёв (чёрные линии)")
    if has_zouit_labels:
        logger.info(f"    - Подписи ЗОУИТ: отдельный слой (невидимые точки)")
    logger.info(f"    - Участок: красная жирная линия")
    logger.info(f"  КАРТА 2: {len(map2_layers)} слоёв")
    
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