# generator/zouit_styles.py
# -*- coding: utf-8 -*-
"""
Справочник стилей для ЗОУИТ (ACTUAL_ZOUIT.*).

Принцип:
- слой обновляется постоянно → правила по смыслу (ключевые слова/регэкспы),
- один источник правды → одинаковые стили для:
  1) слоёв ЗОУИТ на карте (Set Map Layer... Global Pen/Brush)
  2) полигона-образца в условных обозначениях (Create Rect Pen/Brush)

ВАЖНО:
- номера Brush pattern зависят от MapInfo. Здесь задана рабочая матрица
  (штрих/крест/точки) + по плотности. При необходимости подстройте PATTERN_*.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple


# ---------------------------
# Цвета (MapInfo: 0xRRGGBB)
# ---------------------------

def rgb(r: int, g: int, b: int) -> int:
    return (int(r) << 16) + (int(g) << 8) + int(b)


# Базовые палитры
COLOR_GREEN = rgb(0, 150, 0)
COLOR_GREEN_FILL = rgb(120, 210, 120)

COLOR_GRAY = rgb(120, 120, 120)
COLOR_GRAY_FILL = rgb(205, 205, 205)

COLOR_BLUE = rgb(0, 140, 255)
COLOR_BLUE_FILL = rgb(150, 210, 255)

COLOR_YELLOW = rgb(240, 190, 0)
COLOR_YELLOW_FILL = rgb(255, 235, 140)

COLOR_PINK = rgb(220, 70, 150)
COLOR_PINK_FILL = rgb(255, 190, 225)

# Доп. группы (для “неохваченных” типов)
COLOR_PURPLE = rgb(140, 90, 200)
COLOR_PURPLE_FILL = rgb(220, 205, 245)

COLOR_ORANGE = rgb(230, 120, 0)
COLOR_ORANGE_FILL = rgb(255, 210, 150)

COLOR_BROWN = rgb(140, 85, 40)
COLOR_BROWN_FILL = rgb(235, 205, 175)

COLOR_TEAL = rgb(0, 150, 170)          # ЗСО/водозаборы — отличаем от водоохранных
COLOR_TEAL_FILL = rgb(160, 235, 245)


# --------------------------------------
# Паттерны Brush (подстройте при нужде)
# --------------------------------------
# Плотность: 1 (редко) ... 5 (плотно)

PATTERN_HATCH = {1: 44, 2: 45, 3: 46, 4: 47, 5: 48}   # диагональный штрих
PATTERN_CROSS = {1: 49, 2: 50, 3: 51, 4: 52, 5: 53}   # крестовая штриховка
PATTERN_DOTS  = {1: 54, 2: 55, 3: 56, 4: 57, 5: 58}   # точки


# --------------------------------------
# Структура стиля
# --------------------------------------

@dataclass(frozen=True)
class ZouitStyle:
    pen_width: int
    pen_pattern: int
    pen_color: int
    brush_pattern: int
    brush_color: int

    def wor_pen(self) -> str:
        return f"Pen ({self.pen_pattern},{self.pen_width},{self.pen_color})"

    def wor_brush(self) -> str:
        return f"Brush ({self.brush_pattern},{self.brush_color})"


# --------------------------------------
# Вспомогательные парсеры/детекторы
# --------------------------------------

_RE_WS = re.compile(r"\s+")
_RE_AERODROME_SUBZONE = re.compile(r"(?:подзона|подзоны|зона)\s*([1-7])", re.IGNORECASE)
_RE_FLOOD_INTENSITY = re.compile(r"(сильн(?:ого|ая|ое)|умерен(?:ного|ая|ое)|слаб(?:ого|ая|ое))", re.IGNORECASE)

# ЗСО: “первый/второй/третий пояс” или “1/2/3 пояс”
_RE_ZSO_BELT = re.compile(
    r"(перв(?:ый|ого)\s+пояс|втор(?:ой|ого)\s+пояс|трет(?:ий|ьего)\s+пояс|\b([1-3])\s*пояс)",
    re.IGNORECASE
)

def _norm(s: str) -> str:
    s = (s or "").strip()
    s = _RE_WS.sub(" ", s)
    return s

def _contains_any(text: str, keywords: Tuple[str, ...]) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)

def _clamp_density(d: int) -> int:
    return max(1, min(5, int(d)))

def _pattern_from_density(kind: str, density: int) -> int:
    density = _clamp_density(density)
    if kind == "hatch":
        return PATTERN_HATCH[density]
    if kind == "cross":
        return PATTERN_CROSS[density]
    if kind == "dots":
        return PATTERN_DOTS[density]
    return PATTERN_HATCH[1]


def _aerodrome_density(name: str) -> int:
    """
    Приаэродромные: чем БОЛЬШЕ номер подзоны, тем ПЛОТНЕЕ точки.
    """
    m = _RE_AERODROME_SUBZONE.search(name)
    if not m:
        return 1
    n = int(m.group(1))
    mapping = {7: 4, 6: 5, 5: 4, 4: 3, 3: 2, 2: 2, 1: 1}
    return mapping.get(n, 1)


def _flood_density(name: str) -> int:
    """
    Подтопление/затопление:
    слабое → 1, умеренное → 3, сильное → 5
    """
    m = _RE_FLOOD_INTENSITY.search(name)
    if not m:
        return 2
    v = m.group(1).lower()
    if "сильн" in v:
        return 5
    if "умерен" in v:
        return 3
    if "слаб" in v:
        return 1
    return 2


def _water_density(name: str) -> int:
    """
    Водоохранная/прибрежная/береговая:
    береговая → 5, прибрежная → 3, водоохранная → 2
    """
    t = name.lower()
    if "берегов" in t:
        return 5
    if "прибрежн" in t:
        return 3
    if "водоохран" in t:
        return 2
    return 2


def _zso_density(name: str) -> int:
    """
    Пояса зоны санитарной охраны водозаборов:
    1 пояс → самый плотный (5),
    2 пояс → средний (3),
    3 пояс → редкий (2).
    """
    m = _RE_ZSO_BELT.search(name)
    if not m:
        return 3
    s = (m.group(0) or "").lower()
    if "перв" in s or "1" in s:
        return 5
    if "втор" in s or "2" in s:
        return 3
    if "трет" in s or "3" in s:
        return 2
    return 3


# --------------------------------------
# Главная функция выбора стиля
# --------------------------------------

def get_zouit_style(zouit_name: str) -> ZouitStyle:
    """
    Возвращает стиль для ЗОУИТ по названию/описанию.
    Группы по смыслу (приоритет сверху вниз).
    """
    name = _norm(zouit_name)
    low = name.lower()

    # 8) Культурное наследие (розовый)
    if _contains_any(low, ("культурного наслед", "окн", "памятник", "объект культурного")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_PINK,
            brush_pattern=_pattern_from_density("hatch", 3), brush_color=COLOR_PINK_FILL
        )

    # 9) Геодезия/нивелирная/ГГС (коричневые точки, чтобы не путать с водой)
    if _contains_any(low, ("геодез", "нивели", "ггс", "пункт государственной", "триангуляц", "репер")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_BROWN,
            brush_pattern=_pattern_from_density("dots", 2), brush_color=COLOR_BROWN_FILL
        )

    # 10) Публичные сервитуты (фиолетовая разреженная штриховка; читается как “правовой режим”)
    if _contains_any(low, ("публичный сервитут", "публичного сервитута", "сервитут")):
        return ZouitStyle(
            pen_width=2, pen_pattern=2, pen_color=COLOR_PURPLE,
            brush_pattern=_pattern_from_density("hatch", 2), brush_color=COLOR_PURPLE_FILL
        )

    # 11) Зоны санитарной охраны водозаборов (ЗСО) — отдельный бирюзовый, плотность по поясам
    if _contains_any(low, ("зона санитарной охраны", "зоны санитарной охраны", "зсо", "водозабор", "водозаборн", "скважин")) and ("пояс" in low):
        d = _zso_density(name)
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_TEAL,
            brush_pattern=_pattern_from_density("hatch", d), brush_color=COLOR_TEAL_FILL
        )

    # 2) Приаэродромные территории (серые точки, плотность по подзоне)
    if _contains_any(low, ("приаэродром", "аэродром")):
        d = _aerodrome_density(name)
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_GRAY,
            brush_pattern=_pattern_from_density("dots", d), brush_color=COLOR_GRAY_FILL
        )

    # 4) Подтопление/затопление (голубые точки, плотность по степени)
    if _contains_any(low, ("подтоплен", "затоплен")):
        d = _flood_density(name)
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_BLUE,
            brush_pattern=_pattern_from_density("dots", d), brush_color=COLOR_BLUE_FILL
        )

    # 5) Водоохранная/прибрежная/береговая (голубая штриховка, плотность по типу)
    if _contains_any(low, ("водоохран", "прибрежн", "берегов")):
        d = _water_density(name)
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_BLUE,
            brush_pattern=_pattern_from_density("hatch", d), brush_color=COLOR_BLUE_FILL
        )

    # 7) Газ (голубая крестовая штриховка)
    if _contains_any(low, ("газопровод", "газораспредел", "грс", "газ ")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_BLUE,
            brush_pattern=_pattern_from_density("cross", 3), brush_color=COLOR_BLUE_FILL
        )

    # 12) Теплоснабжение/пар/теплотрассы (оранжевый крест — как “тепло/энергия”, но не путать с ЛЭП)
    if _contains_any(low, ("теплотрасс", "теплосет", "теплопровод", "паротрасс", "тэц", "котельн")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_ORANGE,
            brush_pattern=_pattern_from_density("cross", 2), brush_color=COLOR_ORANGE_FILL
        )

    # 6) Связь (жёлтая штриховка)
    if _contains_any(low, ("волс", "связ", "оптическ", "кабель связ")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_YELLOW,
            brush_pattern=_pattern_from_density("hatch", 3), brush_color=COLOR_YELLOW_FILL
        )

    # 1) Электричество (зелёный штрих) — ниже связи/газа/тепла, чтобы меньше ложных совпадений по “кабель”
    if _contains_any(low, ("лэп", "вл ", "вл-", "кл ", "кл-", "квл", "пс", "подстанц", "электро", "кв")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_GREEN,
            brush_pattern=_pattern_from_density("hatch", 3), brush_color=COLOR_GREEN_FILL
        )

    # 3) СЗЗ (серая штриховка)
    if _contains_any(low, ("сзз", "санитарно-защит", "санитарно защит", "санитарн")) and ("охраны" not in low):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_GRAY,
            brush_pattern=_pattern_from_density("hatch", 2), brush_color=COLOR_GRAY_FILL
        )

    # 13) Горные работы/уголь (шахта/разрез/карьер) — коричневый штрих (как “земля/горные”)
    if _contains_any(low, ("шахт", "разрез", "карьер", "уголь", "горн")):
        return ZouitStyle(
            pen_width=2, pen_pattern=1, pen_color=COLOR_BROWN,
            brush_pattern=_pattern_from_density("hatch", 3), brush_color=COLOR_BROWN_FILL
        )

    # Дефолт (нейтральный, чтобы не “заливать” карту)
    return ZouitStyle(
        pen_width=1, pen_pattern=1, pen_color=rgb(0, 0, 0),
        brush_pattern=_pattern_from_density("hatch", 1), brush_color=rgb(245, 245, 245)
    )


# --------------------------------------
# Утилиты для встраивания в WOR
# --------------------------------------

def style_to_layer_global(style: ZouitStyle) -> str:
    """Фрагмент WOR для Display Global: Global Pen (...) Brush (...)"""
    return f"Global {style.wor_pen()} {style.wor_brush()}"

def style_to_legend_rect(style: ZouitStyle) -> tuple[str, str]:
    """(pen_line, brush_line) для Create Rect в легенде."""
    return style.wor_pen(), style.wor_brush()
