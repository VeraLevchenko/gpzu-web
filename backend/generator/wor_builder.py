"""
Генератор WOR-файлов (рабочий набор MapInfo).

WOR (Workspace) - это текстовый файл MapInfo который содержит:
- Список открытых таблиц (слоев)
- Настройки Map Window (карта)
- Настройки Layout Window (компоновка для печати)
- Стили отображения слоев

НОВАЯ ЛОГИКА ОТЧЁТОВ (LAYOUT):
- Layout больше не "вшит" в Python.
- 3 отчёта берутся из шаблонов файлов:
  - templates/wor/layouts/map1_a3_landscape.wor.txt  (карта 1)
  - templates/wor/layouts/map1_a2_landscape.wor.txt  (карта 1)
  - templates/wor/layouts/map2_a4_landscape.wor.txt  (карта 2)

ВНИМАНИЕ:
- Создание карт (Map 1 / Map 2) и стили слоёв не изменялись.
"""

from __future__ import annotations
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
import logging
import os
from dotenv import load_dotenv
from generator.zouit_styles import (get_zouit_style, style_to_layer_global, style_to_legend_rect,)

load_dotenv()

logger = logging.getLogger(__name__)


# ---------- helpers: templates rendering ----------

def _templates_dir() -> Path:
    """backend/templates/wor/layouts"""
    backend_dir = Path(__file__).resolve().parents[1]
    return backend_dir / "templates" / "wor" / "layouts"


def _read_text_auto(path: Path) -> str:
    """
    WOR-шаблоны часто в cp1251. Читаем устойчиво:
    сначала cp1251, потом utf-8.
    """
    data = path.read_bytes()
    try:
        return data.decode("cp1251")
    except Exception:
        return data.decode("utf-8", errors="replace")


def _render_template(text: str, ctx: dict[str, str]) -> str:
    out = text
    for k, v in ctx.items():
        out = out.replace("{{" + k + "}}", v or "")
    return out


def _ensure_nl(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


def _wrap_mi_text(s: str, width: int = 48, indent: str = "  ", max_width: Optional[int] = None) -> str:
    """Перенос длинных строк для MapInfo Create Text (через \n)."""
    s = (s or "").strip()
    if max_width is not None:
        width = int(max_width)
    if not s:
        return ""
    words = s.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
            continue
        if len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    out = lines[0]
    for ln in lines[1:]:
        out += "\n" + indent + ln
    return out


def _wrap_address_for_mapinfo(address: str, width: int = 65) -> str:
    """
    Перенос адреса для MapInfo Create Text.
    MapInfo требует многострочный текст в формате с переносом строк внутри кавычек.
    """
    if not address:
        return ""
    
    address = address.strip()
    words = address.split()
    lines = []
    current_line = ""
    
    for word in words:
        if not current_line:
            current_line = word
        elif len(current_line) + 1 + len(word) <= width:
            current_line += " " + word
        else:
            lines.append(current_line)
            current_line = word
    
    if current_line:
        lines.append(current_line)
    
    # Объединяем строки с переносом для MapInfo
    # В MapInfo многострочный текст записывается как "строка1\n  строка2\n  строка3"
    if len(lines) == 1:
        return lines[0]
    
    result = lines[0]
    for line in lines[1:]:
        result += "\\n" + line  # Используем \\n для экранирования в WOR файле
    
    return result


def _build_zouit_legend_block(
    items: Optional[List[Tuple[str, str]]],
    *,
    template_filename: str,
) -> str:
    """
    Легенда ЗОУИТ:
    - слева прямоугольник-образец (Create Rect) в той же колонке, что и существующие образцы;
      координаты рамки и колонок взяты ТОЧНО из шаблонов map1.
    - справа текст: «наименование (реестровый номер)»
    - перенос строк по ширине рамки легенды (без обрезки)
    - разреженность ТОЛЬКО между разными ЗОУИТ (gap), внутри одного ЗОУИТ межстрочный интервал обычный
    - ни текст, ни прямоугольник не выходят за рамку легенды
    """
    if not items:
        return ""

    # --- точные координаты рамки легенды и колонок образцов из шаблонов ---
    if "map1_a2" in template_filename:
        legend_left  = 19.2944
        legend_right = 23.2618

        symbol_left  = 19.4104
        symbol_right = 20.2875

        x_text = 20.3618
        y0 = 3.75
    else:  # map1_a3
        legend_left  = 12.3333
        legend_right = 16.3007

        symbol_left  = 12.4625
        symbol_right = 13.3049

        x_text = 13.4007
        y0 = 3.75

    # --- параметры размещения ---
    pad_right = 0.01      # чтобы гарантированно не задеть правую рамку легенды
    rect_h = 0.14
    rect_w = symbol_right - symbol_left

    # Межстрочный интервал внутри одного ЗОУИТ — обычный (не разрежаем)
    line_h = 0.09

    # Разреженность ТОЛЬКО между разными ЗОУИТ — увеличиваем gap
    gap = 0.20

    # ширина текстового поля строго внутри рамки легенды
    text_width = (legend_right - pad_right) - x_text
    if text_width < 1.0:
        text_width = 1.0

    # перенос по ширине (без обрезки)
    # Times New Roman 10: ~13 символов/дюйм — берём 13, чтобы не вылезать вправо
    max_chars = max(18, int(text_width * 16))

    out: List[str] = []
    y = y0

    for name, reg in items:
        name = (name or "").strip()
        reg = (reg or "").strip()
        if not name:
            continue

        label = f"{name} ({reg})" if reg else name

        # перенос по словам (реальные \n) — НИКАКОЙ разреженности внутри элемента
        wrapped = _wrap_mi_text(label, max_width=max_chars).strip()
        n_lines = wrapped.count("\n") + 1

        # WOR: внутри кавычек должен быть \n (backslash+n), а кавычки удваиваем
        txt = wrapped.replace("\r", "").replace("\n", "\\n").replace('"', '""')

        # высота блока по тексту
        block_h = max(rect_h, n_lines * line_h)

        # прямоугольник центрируем по высоте блока текста
        y_rect = y + (block_h - rect_h) / 2
        
        # === ДОБАВЛЕНО: стиль из справочника ЗОУИТ ===
        style = get_zouit_style(name)
        pen_line, brush_line = style_to_legend_rect(style)


        # --- прямоугольник-образец (в колонке существующих образцов) ---
        out.append(
            """  Create Rect ({x1},{y1}) ({x2},{y2})
    {pen}
    {brush}""".format(
                x1=round(symbol_left, 4),
                y1=round(y_rect, 4),
                x2=round(symbol_left + rect_w, 4),
                y2=round(y_rect + rect_h, 4),
                pen=pen_line,
                brush=brush_line,
            )
        )


        # --- текст справа, строго в рамке легенды ---
        out.append(
            """  Create Text
    "{txt}"
    ({x1},{y1}) ({x2},{y2})
    Font ("Times New Roman CYR",2,8,0)""".format(
                txt=txt,
                x1=round(x_text, 4),
                y1=round(y, 4),
                x2=round(x_text + text_width, 4),
                y2=round(y + block_h, 4),
            )
        )

        # следующий элемент ниже (разреженность между элементами)
        y += block_h + gap

    return "\n\n".join(out) + "\n"





def _load_and_render_layout(filename: str, ctx: dict[str, str]) -> str:
    path = _templates_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"Не найден шаблон layout: {path}")
    return _ensure_nl(_render_template(_read_text_auto(path), ctx))


def create_workspace_wor(
    workspace_dir: Path,
    cadnum: str,
    has_oks: bool = False,
    has_oks_labels: bool = False,
    zouit_files: Optional[List[Tuple[Path, Path]]] = None,
    has_zouit_labels: bool = False,
    zouit_legend_items: Optional[List[Tuple[str, str]]] = None,
    zouit_list: Optional[list] = None,  # данные workspace.zouit для легенды
    red_lines_path: str = None,
    use_absolute_paths: bool = False,
    address: Optional[str] = None,           # Адрес участка из выписки ЕГРН
    specialist_name: Optional[str] = None,    # ФИО специалиста из учётки
    area: Optional[float] = None
) -> Path:
    """
    Создать WOR-файл рабочего набора с правильными стилями и отчётами (Layout).

    ✨ ЦВЕТОВАЯ СХЕМА:
    КАРТА 1 (Градплан):
    - Точки участка: КРАСНЫЕ кружки с подписями номеров (включены)
    - Зона строительства: КРАСНАЯ штриховка
    - ЗОУИТ: ЧЁРНЫЕ линии без заливки
    - Участок: КРАСНАЯ жирная линия (17,2)

    КАРТА 2 (Ситуационный план):
    - Участок: КРАСНАЯ жирная линия
    - Остальные слои: обычное отображение

    📄 ОТЧЁТЫ (LAYOUT):
    - 3 отчёта подключаются из шаблонов файлов (см. docstring модуля)

    Args:
        workspace_dir: Корневая директория проекта
        cadnum: Кадастровый номер участка из выписки ЕГРН
        has_oks: Есть ли слой ОКС
        zouit_files: Список файлов ЗОУИТ [(mif, mid), ...]
        has_zouit_labels: Есть ли слой подписей ЗОУИТ
        red_lines_path: Путь к слою красных линий
        use_absolute_paths: Использовать абсолютные пути
        address: Адрес участка из выписки ЕГРН
        specialist_name: ФИО главного специалиста из учётной записи

    Returns:
        Path к созданному WOR-файлу
    """

    from core.layers_config import LayerPaths

    logger.info(f"Создание WOR-файла с отчётами (Layout) для {cadnum}")

    workspace_dir = Path(workspace_dir)
    wor_path = workspace_dir / "рабочий_набор.WOR"

    # Относительный путь к папке со слоями
    layers_subdir = "База_проекта"

    if red_lines_path is None:
        red_lines_path = os.getenv("RED_LINES_PATH")

    layer_labels = os.getenv("LAYER_LABELS")
    layer_roads = os.getenv("LAYER_ROADS")
    layer_buildings = os.getenv("LAYER_BUILDINGS")
    layer_actual_land = os.getenv("LAYER_ACTUAL_LAND")

    # Текущая дата для штампа
    current_date = datetime.now().strftime("%d.%m.%Y")

    # Адрес по умолчанию
    if not address:
        address = f"Земельный участок с кадастровым номером {cadnum}"

    # ФИО специалиста по умолчанию
    if not specialist_name:
        specialist_name = "Ляпина К.С."

    # ✅ ДОБАВЛЕНО: Перенос длинного адреса
    # Ширина поля ADDRESS в шаблоне: 4.5 дюйма при шрифте 9pt ≈ 80 символов
    address_wrapped = _wrap_address_for_mapinfo(address or "", width=80)

    # Если список легенды не передан, но есть workspace.zouit — собираем (name, registry_number)
    if (not zouit_legend_items) and zouit_list:
        items: List[Tuple[str, str]] = []
        for z in zouit_list:
            name = getattr(z, 'name', None)
            reg = getattr(z, 'registry_number', None)
            if not name:
                continue
            items.append((str(name), str(reg) if reg else ''))
        # убираем дубли, сохраняя порядок
        seen = set()
        uniq: List[Tuple[str, str]] = []
        for n, r in items:
            key = (n, r)
            if key in seen:
                continue
            seen.add(key)
            uniq.append((n, r))
        zouit_legend_items = uniq


    # ========== КАРТА 1: Основная (градплан) ========== #

    # Порядок слоёв (снизу вверх):
    map1_layers = []

    # 6. Участок - самый верхний слой
    map1_layers.append("участок")

    # 2. Точки участка
    map1_layers.append("участок_точки")

    # 1. ОКС (если есть) - самый нижний слой
    if has_oks:
        map1_layers.append("окс")
    
    if has_oks_labels:
        map1_layers.append("подписи_окс")

    
    # 3. Зона строительства
    map1_layers.append("зона_строительства")

    # 4. ЗОУИТ (если есть)
    if zouit_files:
        for mif_path, _ in zouit_files:
            map1_layers.append(mif_path.stem)

    # 4-Б. Подписи ЗОУИТ (если есть)
    if has_zouit_labels:
        map1_layers.append("зоуит_подписи")

    # 5. Красные линии  # ← ДОБАВЬ ЭТО
    map1_layers.append("Красные_линии")  # ← ДОБАВЬ ЭТО

    
    map1_from_str = ",".join(map1_layers)

    # ========== КАРТА 2: Ситуационный план ========== #

    situation_layers = LayerPaths.get_situation_map_layers()

    map2_layers = ["участок", "Подписи", "ACTUAL_LAND", "Строения", "Проезды"]
    map2_from_str = ",".join(map2_layers)

    # ========== Контекст для шаблонов layout ========== #
    # ✅ ВАЖНО: Создаётся ПОСЛЕ map1_from_str и map2_from_str
    
    ctx = {
        "CADNUM": cadnum,
        "ADDRESS": address_wrapped,  # ✅ ИСПРАВЛЕНО: используем перенесённый адрес
        "DATE_DDMMYYYY": current_date,
        "SPECIALIST": specialist_name or "",
        "AREA": f"{int(round(area))}" if area else "0",
        "MAP1_LAYERS": map1_from_str,  # ✅ Для отчётов A3 и A2
    }

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
        wor_content += f'Open Table "{layers_subdir}\\\\подписи_окс.TAB" As подписи_окс Interactive\n'

    # Открываем каждый файл ЗОУИТ
    if zouit_files:
        for mif_path, _ in zouit_files:
            filename = mif_path.name.replace('.MIF', '.TAB')
            table_name = mif_path.stem
            wor_content += f'Open Table "{layers_subdir}\\\\{filename}" As {table_name} Interactive\n'

    # Открываем слой подписей ЗОУИТ (если есть)
    if has_zouit_labels:
        wor_content += f'Open Table "{layers_subdir}\\\\зоуит_подписи.TAB" As зоуит_подписи Interactive\n'

    # Открываем красные линии
    wor_content += f'Open Table "{red_lines_path}" As Красные_линии Interactive\n'

    # Открываем внешние слои для карты 2 (серверные пути из .env)
    wor_content += f'Open Table "{layer_labels}" As Подписи Interactive\n'
    wor_content += f'Open Table "{layer_roads}" As Проезды Interactive\n'
    wor_content += f'Open Table "{layer_buildings}" As Строения Interactive\n'
    wor_content += f'Open Table "{layer_actual_land}" As ACTUAL_LAND Interactive\n'

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

    # ✅ СОХРАНЯЕМ ID окна карты 1 для использования в Layout
    wor_content += '''Dim map1WindowID As Integer
map1WindowID = FrontWindow()
'''

    # ========== СТИЛИ СЛОЁВ КАРТЫ 1 ========== #

    layer_index = 1

    # ✅ СЛОЙ: Участок (КРАСНАЯ ЖИРНАЯ ЛИНИЯ)
    wor_content += f'''Set Map
    Layer {layer_index}
      Display Global
      Global Pen (17,2,16711680) Brush (1,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
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

    # ✅ СЛОЙ: ОКС (если есть)
    if has_oks:
        wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (1,2,0) Brush (1,16777215,16777215) Symbol (34,0,17) Line (1,2,0) Font ("Arial CYR",0,10,0)
'''
        layer_index += 1

    # ✅ СЛОЙ: подписи_окс — номер ОКС в кружочке
    if has_oks_labels:
        wor_content += f'''Set Map
  Layer {layer_index}
    Display Global
    Global Pen (1,2,0)
    Label Line None Position Center Font ("Arial CYR",513,12,0,16777215) Pen (1,2,0)
      With Номер
      Parallel On Auto Off Overlap Off Duplicates Off Offset 0
      Visibility On
    Visibility On
'''
        layer_index += 1

    # ✅ СЛОЙ: Зона строительства (КРАСНАЯ ШТРИХОВКА)
    wor_content += f'''Set Map
    Layer {layer_index}
        Display Global
        Global Pen (1,2,16711680) Brush (44,16711680) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
        Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0)
          With Кадастровый_номер
          Parallel On Auto Off Overlap Off Duplicates On Offset 2
          Visibility On
'''
    layer_index += 1

    # ЗОУИТ — индивидуальные стили из справочника
    if zouit_files and zouit_list:
        for i, (mif_path, _) in enumerate(zouit_files):
            z = zouit_list[i]
            zouit_name = getattr(z, "name", "") or ""
            style = get_zouit_style(zouit_name)
            style_global = style_to_layer_global(style)

            wor_content += f'''Set Map
    Layer {layer_index}
        Display Global
        {style_global} Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
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

    # ✅ СЛОЙ: Красные линии (СТИЛЬ ИЗ ИСХОДНОГО ФАЙЛА)
    wor_content += f'''Set Map
    Layer {layer_index}
        Display Graphic
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
    Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Кадастровый_номер
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
'''

    # Остальные слои: обычное отображение с подписями
    wor_content += '''  Layer 2
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line Arrow Position Right Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Подпись
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
  Layer 3
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Кадастровый_номер
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
  Layer 4
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Тип
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
  Layer 5
    Display Graphic
    Global Pen (1,2,0) Brush (2,16777215,16777215) Symbol (35,0,12) Line (1,2,0) Font ("Arial CYR",0,9,0)
    Label Line None Position Center Font ("Arial CYR",0,9,0) Pen (1,2,0) 
      With Дорога
      Parallel On Auto Off Overlap Off Duplicates On Offset 2
      Visibility On
'''

    # ========== LAYOUTS: 3 отчёта из файлов-шаблонов ========== #

    # ✅ АКТИВИРУЕМ КАРТУ 1 перед её Layout'ами
    wor_content += '''Set Window map1WindowID Front
'''

    # 1) A3 landscape, карта 1
    ctx["ZOUIT_LEGEND"] = _build_zouit_legend_block(
        zouit_legend_items, template_filename="map1_a3_landscape.wor.txt"
    )
    wor_content += _load_and_render_layout("map1_a3_landscape.wor.txt", ctx)

    # 2) A2 landscape, карта 1
    ctx["ZOUIT_LEGEND"] = _build_zouit_legend_block(
        zouit_legend_items, template_filename="map1_a2_landscape.wor.txt"
    )
    wor_content += _load_and_render_layout("map1_a2_landscape.wor.txt", ctx)

    # 3) A4 landscape, карта 2 (ситуационный план) — без легенды ЗОУИТ
    ctx["ZOUIT_LEGEND"] = ""
    wor_content += _load_and_render_layout("map2_a4_landscape.wor.txt", ctx)

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
    logger.info(f"  LAYOUTS: 3 шаблона из templates/wor/layouts")
    logger.info(f"  Кадастровый номер: {cadnum}")
    logger.info(f"  Адрес: {address}")
    logger.info(f"  Специалист: {specialist_name}")
    logger.info(f"  Дата: {current_date}")

    return wor_path


def create_simple_wor(
    workspace_dir: Path,
    mif_files: List[str]
) -> Path:
    """
    Создать простой WOR-файл только с Map Window (без Layout).

    Используется для быстрого просмотра слоёв.
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
    test_dir = Path("/home/gpzu-web/backend/temp")
    test_dir.mkdir(exist_ok=True)

    # Создаем тестовые MIF файлы (пустые)
    for filename in ["участок.MIF", "участок_точки.MIF", "зона_строительства.MIF"]:
        (test_dir / filename).touch()

    print("=" * 60)
    print("ТЕСТ: Создание WOR-файла с отчётами")
    print("=" * 60)

    # Создаем WOR с Layout
    wor_path = create_workspace_wor(
        workspace_dir=test_dir,
        cadnum="42:30:0102050:255",
        has_oks=False,
        zouit_files=None,
        has_zouit_labels=False,
        address="г. Новокузнецк, Куйбышевский район, ул. Кирова, 1-Б",
        specialist_name="Иванов И.И."
    )

    print(f"\n✅ WOR-файл создан: {wor_path}")
    print(f"Размер: {wor_path.stat().st_size} байт")

    print("=" * 60)