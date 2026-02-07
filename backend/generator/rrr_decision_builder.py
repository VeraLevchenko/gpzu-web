# backend/generator/rrr_decision_builder.py
"""
Генератор решения о разрешении размещения объектов (DOCX).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from docxtpl import DocxTemplate

logger = logging.getLogger("gpzu-web.rrr_decision_builder")

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "rrr" / "decision_template.docx"


def _format_area(area_value) -> str:
    """Форматирует площадь: 1024.46 -> '1 024,46'"""
    if area_value is None:
        return ""
    try:
        num = float(area_value)
        formatted = f"{num:,.2f}"
        formatted = formatted.replace(",", " ").replace(".", ",")
        return formatted
    except (ValueError, TypeError):
        return str(area_value)


def generate_rrr_decision(permit: Any, output_path: str) -> str:
    """
    Сгенерировать решение о разрешении размещения объектов.

    Args:
        permit: Объект PlacementPermit или dict
        output_path: Путь для сохранения документа

    Returns:
        Путь к созданному файлу
    """
    data = permit if isinstance(permit, dict) else permit.to_dict()

    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError(f"Шаблон решения не найден: {TEMPLATE_PATH}")

    logger.info(f"Генерация решения РРР: {output_path}")

    tpl = DocxTemplate(str(TEMPLATE_PATH))

    # Определяем заявителя
    applicant = data.get("org_name") or data.get("person_name") or ""

    # Формируем контекст для шаблона
    context = {
        # Решение
        "OUT_NUMBER": data.get("decision_number") or "___",
        "OUT_DATE": data.get("decision_date") or "___",
        # Заявление
        "APP_NUMBER": data.get("app_number") or "___",
        "APP_DATE": data.get("app_date") or "___",
        "APPLICANT": applicant,
        "INN": data.get("org_inn") or "___",
        "OGRN": data.get("org_ogrn") or "___",
        "PASSPORT": data.get("person_passport") or "",
        "ADDRESS": data.get("org_address") or data.get("person_address") or "",
        # Объект
        "OBJECT_TYPE": data.get("object_type") or "___",
        "OBJECT_NAME": data.get("object_name") or "___",
        "AREA": _format_area(data.get("area")),
        "LOCATION": data.get("location") or "___",
        "TERM_MONTHS": data.get("term_months") or "___",
        "END_DATE": data.get("end_date") or "___",
        # Пространственный анализ
        "QUARTERS": data.get("quarters") or "не определены",
        "CAPITAL_OBJECTS_LIST": data.get("capital_objects") or [],
        "ZOUIT_LIST": data.get("zouit") or [],
        "RED_LINES_INSIDE": _format_area(data.get("red_lines_inside_area")),
        "RED_LINES_OUTSIDE": _format_area(data.get("red_lines_outside_area")),
        # Подпись
        "POSITION": "",
        "SIGNATURE": "",
    }

    tpl.render(context)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(str(out))

    logger.info(f"Решение РРР сгенерировано: {out}")
    return str(out)
