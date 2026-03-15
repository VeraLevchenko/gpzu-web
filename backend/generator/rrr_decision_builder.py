# backend/generator/rrr_decision_builder.py
"""
Генератор решения о разрешении размещения объектов (DOCX).
Динамический шаблон с Jinja2-условиями: правовые основания, оплата,
условия размещения, прекращение — всё определяется видом объекта.
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from docxtpl import DocxTemplate

logger = logging.getLogger("gpzu-web.rrr_decision_builder")

TEMPLATE_PATH = Path(__file__).resolve().parent.parent / "templates" / "rrr" / "decision_template.docx"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

# Паттерны для автоопределения платности (работают в любом падеже и регистре)
_PARKING_RE = re.compile(r"парковк|стоянк|автостоянк", re.IGNORECASE)
_OIL_RE = re.compile(r"нефтепровод", re.IGNORECASE)
_CAFE_RE = re.compile(r"кафе|общественн\w*\s+питани\w*|питани\w*\s+общественн", re.IGNORECASE)


# ========================================================================
# Загрузка конфигурации
# ========================================================================

def _load_object_types() -> list:
    path = CONFIG_DIR / "object_types.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_payment_config() -> dict:
    path = CONFIG_DIR / "payment_config.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _find_object_type_config(object_type_str: str, types_list: list) -> Optional[dict]:
    """Найти конфигурацию типа объекта по строке вида 'п.6 — Нефтепроводы...'"""
    if not object_type_str:
        return None

    # Извлекаем номер пункта из строки: «п.6 — ...», «пп.4 ...», «5. ...», «6 ...»
    m = re.match(r"^(?:п+\.?\s*)?(\d+(?:\.\d+)?)", object_type_str.strip())
    if m:
        number = m.group(1)
        for t in types_list:
            if t["number"] == number:
                return t

    # Фолбэк: ищем по short_name
    for t in types_list:
        if t["short_name"] and t["short_name"].lower() in object_type_str.lower():
            return t

    return None


# ========================================================================
# Числа прописью (русский язык)
# ========================================================================

_ONES = [
    "", "один", "два", "три", "четыре", "пять",
    "шесть", "семь", "восемь", "девять",
]
_ONES_F = [
    "", "одна", "две", "три", "четыре", "пять",
    "шесть", "семь", "восемь", "девять",
]
_TEENS = [
    "десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать",
    "пятнадцать", "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать",
]
_TENS = [
    "", "", "двадцать", "тридцать", "сорок", "пятьдесят",
    "шестьдесят", "семьдесят", "восемьдесят", "девяносто",
]
_HUNDREDS = [
    "", "сто", "двести", "триста", "четыреста", "пятьсот",
    "шестьсот", "семьсот", "восемьсот", "девятьсот",
]


def _int_to_words(n: int, feminine: bool = False) -> str:
    """Число прописью (0..999999). Для месяцев feminine=False."""
    if n == 0:
        return "ноль"

    parts = []
    ones_list = _ONES_F if feminine else _ONES

    if n >= 1000:
        thousands = n // 1000
        n %= 1000
        # Тысячи — женский род
        t_h = thousands // 100
        t_rest = thousands % 100
        if t_h:
            parts.append(_HUNDREDS[t_h])
        if 10 <= t_rest <= 19:
            parts.append(_TEENS[t_rest - 10])
        else:
            t_tens = t_rest // 10
            t_ones = t_rest % 10
            if t_tens:
                parts.append(_TENS[t_tens])
            if t_ones:
                parts.append(_ONES_F[t_ones])

        # Склонение "тысяча"
        last_two = thousands % 100
        last_one = thousands % 10
        if 11 <= last_two <= 19:
            parts.append("тысяч")
        elif last_one == 1:
            parts.append("тысяча")
        elif 2 <= last_one <= 4:
            parts.append("тысячи")
        else:
            parts.append("тысяч")

    h = n // 100
    rest = n % 100
    if h:
        parts.append(_HUNDREDS[h])
    if 10 <= rest <= 19:
        parts.append(_TEENS[rest - 10])
    else:
        t = rest // 10
        o = rest % 10
        if t:
            parts.append(_TENS[t])
        if o:
            parts.append(ones_list[o])

    return " ".join(parts)


def _term_months_text(months: int) -> str:
    """Форматирует срок: '36 (тридцать шесть) месяцев'"""
    words = _int_to_words(months)

    last_two = months % 100
    last_one = months % 10
    if 11 <= last_two <= 19:
        unit = "месяцев"
    elif last_one == 1:
        unit = "месяц"
    elif 2 <= last_one <= 4:
        unit = "месяца"
    else:
        unit = "месяцев"

    return f"{months} ({words}) {unit}"


# ========================================================================
# Расчёт платы
# ========================================================================

def _calculate_payment(
    area: float,
    decision_date: date,
    end_date: date,
    payment_formula: str,
    payment_config: dict,
) -> Tuple[float, float, int, float]:
    """
    Рассчитать плату.

    Returns:
        (payment_yearly, payment_total, period_days, daily_rate)
    """
    delta = (end_date - decision_date).days
    if delta <= 0:
        delta = 1

    if payment_formula == "lep":
        cfg = payment_config["lep"]
        yearly = cfg["base_rate"] * area * cfg["ki"]
    else:
        cfg = payment_config["standard"]
        yearly = cfg["su"] * cfg["nst"] * area

    total = yearly * (delta / 365)

    return (
        round(yearly, 2),
        round(total, 2),
        delta,
        round(yearly / 365, 2),
    )


def _format_money(amount: float) -> str:
    """Форматирует сумму: 12345.67 -> '12 345,67'"""
    rub = int(amount)
    kop = round((amount - rub) * 100)
    rub_str = f"{rub:,}".replace(",", " ")
    return f"{rub_str},{kop:02d}"


def _money_to_words(amount: float) -> str:
    """Сумма прописью: 12345.67 -> 'двенадцать тысяч триста сорок пять рублей 67 копеек'"""
    rub = int(amount)
    kop = round((amount - rub) * 100)

    rub_words = _int_to_words(rub)

    last_two = rub % 100
    last_one = rub % 10
    if 11 <= last_two <= 19:
        rub_unit = "рублей"
    elif last_one == 1:
        rub_unit = "рубль"
    elif 2 <= last_one <= 4:
        rub_unit = "рубля"
    else:
        rub_unit = "рублей"

    last_two_k = kop % 100
    last_one_k = kop % 10
    if 11 <= last_two_k <= 19:
        kop_unit = "копеек"
    elif last_one_k == 1:
        kop_unit = "копейка"
    elif 2 <= last_one_k <= 4:
        kop_unit = "копейки"
    else:
        kop_unit = "копеек"

    return f"{rub_words} {rub_unit} {kop:02d} {kop_unit}"


# ========================================================================
# Определение платности
# ========================================================================

def _determine_has_payment(
    type_config: Optional[dict],
    object_name: str,
    has_payment_override: Optional[bool],
) -> bool:
    """
    Определить, платный ли объект.
    has_payment_override — ручное переопределение пользователем.
    """
    if has_payment_override is not None:
        return has_payment_override

    if type_config is None:
        return True  # По умолчанию платный

    # Дефолтное значение из конфига
    default = type_config.get("has_payment_default", True)

    number = type_config.get("number", "")

    # п.4 — платно только если «парковка», «стоянка», «автостоянка» (любой падеж)
    if number == "4" and type_config.get("payment_by_name"):
        return bool(_PARKING_RE.search(object_name or ""))

    # п.6 — бесплатно кроме нефтепроводов (нефтепроводы — платно)
    if number == "6" and type_config.get("payment_by_name_oil"):
        return bool(_OIL_RE.search(object_name or ""))

    # п.19 — платно если «кафе» или «общественное питание» (любой падеж)
    if number == "19" and type_config.get("payment_by_name_cafe"):
        return bool(_CAFE_RE.search(object_name or ""))

    return default


# ========================================================================
# Форматирование
# ========================================================================

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


def _format_date_ru(d) -> str:
    """Дата в формате '10.01.2026'"""
    if d is None:
        return "___"
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                d = datetime.strptime(d, fmt).date()
                break
            except ValueError:
                continue
        else:
            return d
    if isinstance(d, (date, datetime)):
        return d.strftime("%d.%m.%Y")
    return str(d)


def _format_date_long(d) -> str:
    """Дата в формате '10 января 2026 г.'"""
    if d is None:
        return "«___» ________ 20__ г."
    if isinstance(d, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                d = datetime.strptime(d, fmt).date()
                break
            except ValueError:
                continue
        else:
            return d

    months = [
        "", "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря",
    ]

    if isinstance(d, (date, datetime)):
        return f"{d.day} {months[d.month]} {d.year} г."
    return str(d)


def _parse_date_value(val) -> Optional[date]:
    """Преобразует значение в объект date."""
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
    return None


# ========================================================================
# Основная функция генерации
# ========================================================================

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

    # Загружаем конфиги
    object_types = _load_object_types()
    payment_config = _load_payment_config()

    # Определяем тип объекта
    type_config = _find_object_type_config(data.get("object_type", ""), object_types)

    # Флаги из конфига типа
    is_linear = type_config.get("is_linear", False) if type_config else False
    is_nto = type_config.get("is_nto", False) if type_config else False
    is_attrac = type_config.get("is_attrac", False) if type_config else False
    max_term_years = type_config.get("max_term_years", 3) if type_config else 3
    payment_formula = type_config.get("payment_formula", "standard") if type_config else "standard"
    object_number = type_config.get("number", "") if type_config else ""

    # Определяем платность
    has_payment = _determine_has_payment(
        type_config,
        data.get("object_name", ""),
        data.get("has_payment"),
    )

    # Подпункты блока «Прекращение» (динамические)
    _term = 5
    n_term_payment = _term if has_payment else 0
    if has_payment:
        _term += 1
    n_term_nto = _term if is_attrac else 0
    if is_attrac:
        _term += 1

    # Ранее выданные решения РРР
    _prev_raw = data.get("prev_decisions") or []
    prev_decisions = [
        {
            "object_type":     item.get("object_type") or "",
            "decision_number": item.get("decision_number") or "",
            "decision_date":   _format_date_ru(item.get("decision_date")),
            "end_date":        _format_date_ru(item.get("end_date")),
            "applicant":       item.get("applicant") or "",
        }
        for item in _prev_raw
    ]
    has_prev_decisions = bool(prev_decisions)

    # Нумерация пунктов решения (динамическая)
    _n = 3
    n_payment = 3 if has_payment else 0
    if has_payment:
        _n += 1                                # п.3 = оплата
    n_attrac = _n if is_attrac else 0
    if is_attrac:
        _n += 1                                # п. об аттракционе
    n_termination = _n; _n += 1               # Прекращение действия
    n_liquidation = _n; _n += 1               # В случае ликвидации
    n_earthworks = _n; _n += 1                # Земляные работы
    n_geodesy = _n; _n += 1                   # Геодезическая съёмка
    n_rso = _n; _n += 1                       # Согласования РСО
    n_third_parties = _n; _n += 1             # Права третьих лиц
    n_prev_decisions = _n if has_prev_decisions else 0  # Ранее выданные РРР (условно)
    if has_prev_decisions:
        _n += 1
    n_vegetation = _n; _n += 1                # Вырубка насаждений
    n_cleanup = _n; _n += 1                   # Очистка от деревьев
    n_liner = _n if is_linear else 0
    if is_linear:
        _n += 1                                # Абзац для линейных объектов
    n_end_term = _n; _n += 1                  # По окончании срока
    n_maintenance = _n; _n += 1               # Содержание территории
    n_pavement = _n; _n += 1                  # Восстановление покрытия
    n_control = _n                             # Контроль

    # Согласование примыкания (п.9)
    proezd_agreement = data.get("proezd_agreement") or ""

    # Срок действия
    term_months = data.get("term_months")

    # Парсим даты
    decision_date = _parse_date_value(data.get("decision_date"))
    # end_date всегда рассчитывается как decision_date + term_months
    if decision_date and term_months:
        end_date = decision_date + relativedelta(months=term_months) - relativedelta(days=1)
    else:
        end_date = _parse_date_value(data.get("end_date"))

    # Расчёт платы
    payment_yearly = 0.0
    payment_total = 0.0
    period_days = 0
    if has_payment and data.get("area") and decision_date and end_date:
        payment_yearly, payment_total, period_days, _ = _calculate_payment(
            area=float(data["area"]),
            decision_date=decision_date,
            end_date=end_date,
            payment_formula=payment_formula,
            payment_config=payment_config,
        )
    term_text = _term_months_text(term_months) if term_months else "___"
    max_term_months = max_term_years * 12

    # Определяем заявителя
    applicant_type = data.get("applicant_type", "")
    is_legal = applicant_type == "ЮЛ"

    if is_legal:
        applicant_block = data.get("org_name") or "___"
        applicant_details = ""
        inn = data.get("org_inn") or ""
        ogrn = data.get("org_ogrn") or ""
        address = data.get("org_address") or ""
        if inn:
            applicant_details += f"ИНН {inn}"
        if ogrn:
            applicant_details += f", ОГРН {ogrn}" if applicant_details else f"ОГРН {ogrn}"
        if address:
            applicant_details += f", {address}" if applicant_details else address
    else:
        applicant_block = data.get("person_name") or data.get("org_name") or "___"
        passport = data.get("person_passport") or ""
        address = data.get("person_address") or data.get("org_address") or ""
        applicant_details = ""
        if passport:
            applicant_details += f"паспорт: {passport}"
        if address:
            applicant_details += f", {address}" if applicant_details else address

    # Красные линии
    red_lines_inside = data.get("red_lines_inside_area")
    has_red_lines = red_lines_inside is not None and float(red_lines_inside or 0) > 0

    # Подпункты внутри п.8 (РСО) — условные
    _sub = 12
    n_sub_liner = _sub if is_linear else 0
    if is_linear:
        _sub += 1
    n_sub_red_lines = _sub if has_red_lines else 0

    # Реквизиты
    requisites = payment_config.get("requisites", {})

    # Параметры формулы для шаблона
    if payment_formula == "lep":
        lep_cfg = payment_config["lep"]
        formula_params = {
            "base_rate": lep_cfg["base_rate"],
            "ki": lep_cfg["ki"],
        }
        SU = 0
        NST_PCT = ""
        BASE_RATE = lep_cfg["base_rate"]
        KI = lep_cfg["ki"]
        KI_FORMULA = lep_cfg.get("ki_formula", "")
    else:
        std_cfg = payment_config["standard"]
        formula_params = {
            "su": std_cfg["su"],
            "nst": std_cfg["nst"],
            "nst_pct": f"{std_cfg['nst'] * 100:g}",
        }
        SU = std_cfg["su"]
        NST_PCT = f"{std_cfg['nst'] * 100:g}"
        BASE_RATE = 0
        KI = 0
        KI_FORMULA = ""

    # Формируем контекст для шаблона
    context = {
        # Решение
        "OUT_NUMBER": data.get("decision_number") or "___",
        "OUT_DATE": _format_date_ru(data.get("decision_date")),
        "OUT_DATE_LONG": _format_date_long(data.get("decision_date")),
        # Заявление
        "APP_NUMBER": data.get("app_number") or "___",
        "APP_DATE": _format_date_ru(data.get("app_date")),
        # Заявитель
        "APPLICANT": applicant_block,
        "APPLICANT_DETAILS": applicant_details,
        "is_legal": is_legal,
        "INN": data.get("org_inn") or "",
        "OGRN": data.get("org_ogrn") or "",
        "PASSPORT": data.get("person_passport") or "",
        "ADDRESS": data.get("org_address") or data.get("person_address") or "",
        # Объект
        "OBJECT_TYPE": data.get("object_type") or "___",
        "OBJECT_TYPE_FULL": type_config.get("full_name", "") if type_config else "",
        "OBJECT_NUMBER": object_number,
        "OBJECT_NAME": data.get("object_name") or "___",
        "AREA": _format_area(data.get("area")),
        "AREA_NUM": data.get("area") or 0,
        "LOCATION": data.get("location") or "___",
        # Срок
        "TERM_MONTHS": term_months or "___",
        "TERM_TEXT": term_text,
        "MAX_TERM_MONTHS": max_term_months,
        "END_DATE": _format_date_ru(end_date),
        "END_DATE_LONG": _format_date_long(end_date),
        # Флаги
        "is_linear": is_linear,
        "is_nto": is_nto,
        "is_attrac": is_attrac,
        "has_payment": has_payment,
        "has_red_lines": has_red_lines,
        "proezd_agreement": proezd_agreement,
        "payment_formula": payment_formula,
        # Оплата
        "N_PAYMENT": n_payment,
        "N_ATTRAC": n_attrac,
        "PAYMENT_YEARLY": _format_money(payment_yearly),
        "PAYMENT_YEARLY_WORDS": _money_to_words(payment_yearly),
        "PAYMENT_TOTAL": _format_money(payment_total),
        "PAYMENT_TOTAL_WORDS": _money_to_words(payment_total),
        "PERIOD_DAYS": period_days,
        "formula_params": formula_params,
        "SU": SU,
        "NST_PCT": NST_PCT,
        "BASE_RATE": BASE_RATE,
        "KI": KI,
        "KI_FORMULA": KI_FORMULA,
        # Реквизиты
        "REQ_RECIPIENT": requisites.get("recipient", ""),
        "REQ_INN": requisites.get("inn", ""),
        "REQ_KPP": requisites.get("kpp", ""),
        "REQ_BANK": requisites.get("bank", ""),
        "REQ_BIK": requisites.get("bik", ""),
        "REQ_ACCOUNT": requisites.get("account", ""),
        "REQ_CORR_ACCOUNT": requisites.get("corr_account", ""),
        "REQ_OKTMO": requisites.get("oktmo", ""),
        "REQ_KBK": requisites.get("kbk", ""),
        "REQ_PURPOSE": requisites.get("purpose", ""),
        # Нумерация пунктов
        "N_TERMINATION": n_termination,
        "N_LIQUIDATION": n_liquidation,
        "N_EARTHWORKS": n_earthworks,
        "N_GEODESY": n_geodesy,
        "N_RSO": n_rso,
        "N_THIRD_PARTIES": n_third_parties,
        "N_PREV_DECISIONS": n_prev_decisions,
        "PREV_DECISIONS":   prev_decisions,
        "N_VEGETATION": n_vegetation,
        "N_CLEANUP": n_cleanup,
        "N_LINER": n_liner,
        "N_SUB_LINER": n_sub_liner,
        "N_SUB_RED_LINES": n_sub_red_lines,
        "N_TERM_PAYMENT": n_term_payment,
        "N_TERM_NTO": n_term_nto,
        "N_END_TERM": n_end_term,
        "N_MAINTENANCE": n_maintenance,
        "N_PAVEMENT": n_pavement,
        "N_CONTROL": n_control,
        "CURRENT_USER": "",
        # Пространственный анализ
        "QUARTERS": data.get("quarters") or "не определены",
        "CAPITAL_OBJECTS_LIST": data.get("capital_objects") or [],
        "ZOUIT_LIST": data.get("zouit") or [],
        "RED_LINES_INSIDE": _format_area(data.get("red_lines_inside_area")),
        "RED_LINES_OUTSIDE": _format_area(data.get("red_lines_outside_area")),
    }

    tpl = DocxTemplate(str(TEMPLATE_PATH))
    tpl.render(context)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    tpl.save(str(out))

    logger.info(f"Решение РРР сгенерировано: {out}")
    return str(out)
