# backend/utils/rrr_deadline.py
"""
Калькулятор сроков оказания услуги для модуля РРР.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Optional

from parsers.application_parser import add_working_days


# Загрузка справочника видов объектов
_OBJECT_TYPES_PATH = Path(__file__).resolve().parent.parent / "config" / "object_types.json"
_OBJECT_TYPES = None


def _load_object_types() -> list:
    global _OBJECT_TYPES
    if _OBJECT_TYPES is None:
        with open(_OBJECT_TYPES_PATH, "r", encoding="utf-8") as f:
            _OBJECT_TYPES = json.load(f)
    return _OBJECT_TYPES


def get_object_types() -> list:
    """Получить справочник видов объектов."""
    return _load_object_types()


def get_deadline_days(object_type_number: str, variant_name: Optional[str] = None) -> int:
    """
    Получить количество рабочих дней для оказания услуги по номеру типа объекта.

    Args:
        object_type_number: Номер пункта Постановления (например "5", "6")
        variant_name: Название варианта для п.6 (например "Нефтепроводы")

    Returns:
        Количество рабочих дней (по умолчанию 30)
    """
    for obj_type in _load_object_types():
        if obj_type["number"] == object_type_number:
            # Проверяем варианты (для п.6)
            if variant_name and "variants" in obj_type:
                for variant in obj_type["variants"]:
                    if variant_name.lower() in variant["name"].lower():
                        return variant["deadline_days"]
            return obj_type["deadline_days"]

    return 30  # по умолчанию


def calculate_service_deadline(app_date: date, object_type_number: str, variant_name: Optional[str] = None) -> date:
    """
    Рассчитать дату окончания срока оказания услуги.

    Args:
        app_date: Дата подачи заявления
        object_type_number: Номер типа объекта из Постановления 1300
        variant_name: Название варианта (для п.6)

    Returns:
        Дата окончания срока оказания услуги
    """
    days = get_deadline_days(object_type_number, variant_name)
    return add_working_days(app_date, days)
