# backend/generator/rrr_mapinfo.py
"""
Интеграция с MapInfo для модуля РРР.
Создание MIF/MID и добавление в слой РэРэРэ.TAB.

Схема слоя (13 полей, НЕ МЕНЯТЬ):
  ID Char(4), Заявитель Char(60), Номер_Решения Char(10),
  Дата_Решения Date, Площадь Char(100), Дата_окончания Char(100),
  Вид_Объекта Char(100), Наименование Char(200),
  Местоположение Char(150), ЗОУИТ Char(150), Примечание Char(200),
  Входящий_номер Char(100), Входящая_дата Date
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

from generator.mif_writer import (
    MSK42_COORDSYS,
    escape_mif_string,
    safe_encode_cp1251,
)
from core.layers_config import LayerPaths

logger = logging.getLogger("gpzu-web.rrr_mapinfo")


# ────────────────────────────────────────────────────────────
# Публичный API
# ────────────────────────────────────────────────────────────

def add_permit_to_mapinfo(permit: Any) -> bool:
    """
    Добавить разрешение на размещение в слой MapInfo.

    Raises:
        ValueError  — не заполнены обязательные поля или координаты
        RuntimeError — ошибка merge / ogr2ogr
    """
    data = permit if isinstance(permit, dict) else permit.to_dict()

    # --- валидация обязательных полей ---
    _validate_required_fields(data)

    # --- парсинг координат ---
    coords = _parse_coordinates(data.get("coordinates", []))

    # --- формирование MIF/MID и merge ---
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        mif_path = tmpdir_path / "rrr_permit.MIF"
        mid_path = tmpdir_path / "rrr_permit.MID"

        _create_permit_mif(data, coords, mif_path, mid_path)
        logger.info("MIF/MID созданы: %s", mif_path)

        output_layer = LayerPaths.RRR_OUTPUT
        if not output_layer.exists():
            raise RuntimeError(
                f"Выходной слой не найден: {output_layer}"
            )

        _merge_to_tab_layer(mif_path, tmpdir_path, output_layer)

    return True


# ────────────────────────────────────────────────────────────
# Валидация
# ────────────────────────────────────────────────────────────

def _validate_required_fields(data: dict) -> None:
    """Проверить обязательные поля. Raise ValueError если чего-то не хватает."""
    checks = {
        "Заявитель": data.get("org_name") or data.get("person_name"),
        "Площадь": data.get("area"),
        "Вид объекта": data.get("object_type"),
        "Наименование": data.get("object_name"),
        "Входящий номер": data.get("app_number"),
        "Входящая дата": data.get("app_date"),
    }
    missing = [name for name, val in checks.items() if not val]

    coordinates = data.get("coordinates")
    if not coordinates or len(coordinates) < 3:
        missing.append("Координаты (минимум 3 точки)")

    if missing:
        raise ValueError(
            "Не заполнены обязательные поля: " + ", ".join(missing)
        )


# ────────────────────────────────────────────────────────────
# Координаты и контуры
# ────────────────────────────────────────────────────────────

def _parse_coordinates(coordinates: list) -> list[tuple[float, float]]:
    """Парсинг координат из JSONB-списка {x, y, num} → [(x, y), ...]."""
    coords: list[tuple[float, float]] = []
    for coord in coordinates:
        try:
            x = float(str(coord.get("x", "")).replace(",", ".").replace(" ", ""))
            y = float(str(coord.get("y", "")).replace(",", ".").replace(" ", ""))
            coords.append((x, y))
        except (ValueError, AttributeError):
            continue

    if len(coords) < 3:
        raise ValueError("Недостаточно координат для полигона")
    return coords


def _split_contours_by_closure(
    points: list[tuple[float, float]],
) -> list[list[tuple[float, float]]]:
    """
    Разбить плоский список точек на контуры по замыканию.
    Контур замкнут, когда последняя точка совпадает с первой.
    Поддержка multipart-полигонов и отверстий (holes).
    """
    if not points:
        return []

    contours: list[list[tuple[float, float]]] = []
    current: list[tuple[float, float]] = []
    first = None

    for pt in points:
        if first is None:
            first = pt
        current.append(pt)

        if len(current) >= 4 and current[-1] == first:
            contours.append(current)
            current = []
            first = None

    if current:
        contours.append(current)

    return [c for c in contours if len(c) >= 3]


# ────────────────────────────────────────────────────────────
# MIF / MID
# ────────────────────────────────────────────────────────────

def _format_date_for_mif(value) -> str:
    """
    Форматирование даты для MIF Date-поля: YYYYMMDD.
    Принимает date, datetime, ISO-строку или dd.mm.yyyy.
    Пустое значение → пустая строка.
    """
    if not value:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y%m%d")
    s = str(value).strip()
    if not s:
        return ""
    # ISO формат: 2024-01-15 или 2024-01-15T...
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y"):
        try:
            return datetime.strptime(s.split("T")[0] if "T" in s else s, fmt.split("T")[0]).strftime("%Y%m%d")
        except ValueError:
            continue
    return ""


def _create_permit_mif(
    data: dict,
    coords: list[tuple[float, float]],
    mif_path: Path,
    mid_path: Path,
) -> None:
    """
    Создать MIF/MID файлы разрешения.
    Схема строго соответствует РэРэРэ.TAB (13 полей).
    ВСЕ поля всегда записываются.
    """

    # ── MIF (геометрия + заголовок) ──
    with open(mif_path, "wb") as f:
        def w(text: str):
            f.write(text.encode("cp1251"))

        w("Version   450\n")
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f"{MSK42_COORDSYS}\n")

        # Колонки строго по схеме TAB
        w("Columns 13\n")
        w("  ID Char(4)\n")
        w("  Заявитель Char(60)\n")
        w("  Номер_Решения Char(10)\n")
        w("  Дата_Решения Date\n")
        w("  Площадь Char(100)\n")
        w("  Дата_окончания Char(100)\n")
        w("  Вид_Объекта Char(100)\n")
        w("  Наименование Char(200)\n")
        w("  Местоположение Char(150)\n")
        w("  ЗОУИТ Char(150)\n")
        w("  Примечание Char(200)\n")
        w("  Входящий_номер Char(100)\n")
        w("  Входящая_дата Date\n")
        w("Data\n\n")

        # Геометрия: поддержка multipart и holes
        contours = _split_contours_by_closure(coords)

        if len(contours) <= 1:
            w("Region  1\n")
            w(f"  {len(coords)}\n")
            for x, y in coords:
                w(f"{x} {y}\n")
        else:
            w(f"Region  {len(contours)}\n")
            for c in contours:
                w(f"  {len(c)}\n")
                for x, y in c:
                    w(f"{x} {y}\n")

        w("    Pen (1,2,0)\n")
        w("    Brush (1,0,16777215)\n")

    # ── MID (атрибуты — строго 13 полей, все заполнены) ──
    with open(mid_path, "wb") as f:
        # Обязательные поля — из карточки
        applicant = data.get("org_name") or data.get("person_name") or ""
        object_type = data.get("object_type") or ""
        object_name = data.get("object_name") or ""
        app_number = data.get("app_number") or ""
        area_val = data.get("area")
        area_str = str(area_val) if area_val is not None else ""

        # Необязательные — из карточки или пустые
        decision_number = data.get("decision_number") or ""
        end_date = data.get("end_date") or ""
        location = data.get("location") or ""
        notes = data.get("notes") or ""

        # ЗОУИТ — из JSONB: реестровые номера через ;
        zouit_raw = data.get("zouit") or []
        zouit_parts = []
        if isinstance(zouit_raw, list):
            for z in zouit_raw:
                if isinstance(z, dict):
                    rn = z.get("registry_number") or z.get("name") or ""
                    if rn:
                        zouit_parts.append(str(rn))
        zouit_text = "; ".join(zouit_parts) if zouit_parts else ""

        # Date-поля: формат YYYYMMDD
        decision_date_mif = _format_date_for_mif(data.get("decision_date"))
        app_date_mif = _format_date_for_mif(data.get("app_date"))

        # ID — Char(4)
        permit_id = str(data.get("id", ""))[:4]

        # Строго 13 полей в порядке TAB-схемы
        fields = [
            escape_mif_string(safe_encode_cp1251(permit_id)),           # ID
            escape_mif_string(safe_encode_cp1251(applicant[:60])),      # Заявитель
            escape_mif_string(safe_encode_cp1251(decision_number[:10])),# Номер_Решения
            decision_date_mif,                                          # Дата_Решения (Date)
            escape_mif_string(safe_encode_cp1251(area_str[:100])),      # Площадь
            escape_mif_string(safe_encode_cp1251(str(end_date)[:100])), # Дата_окончания
            escape_mif_string(safe_encode_cp1251(object_type[:100])),   # Вид_Объекта
            escape_mif_string(safe_encode_cp1251(object_name[:200])),   # Наименование
            escape_mif_string(safe_encode_cp1251(location[:150])),      # Местоположение
            escape_mif_string(safe_encode_cp1251(zouit_text[:150])),    # ЗОУИТ
            escape_mif_string(safe_encode_cp1251(notes[:200])),         # Примечание
            escape_mif_string(safe_encode_cp1251(app_number[:100])),    # Входящий_номер
            app_date_mif,                                               # Входящая_дата (Date)
        ]

        line = ",".join(fields) + "\n"
        f.write(line.encode("cp1251"))


# ────────────────────────────────────────────────────────────
# Merge в основной слой
# ────────────────────────────────────────────────────────────

def _merge_to_tab_layer(
    mif_path: Path,
    tmpdir: Path,
    tab_layer_path: Path,
) -> None:
    """
    Merge: MIF → временный TAB → append в основной слой.
    Использует ogr2ogr для конвертации и append.
    """
    # ogr2ogr создаёт файлы с lowercase расширением (.tab)
    tmp_tab = tmpdir / "rrr_permit.tab"

    # Шаг 1: конвертация MIF → временный TAB
    _run_ogr2ogr(
        [
            "ogr2ogr",
            "-f", "MapInfo File",
            "-lco", "ENCODING=CP1251",
            str(tmp_tab),
            str(mif_path),
        ],
        error_context="Ошибка конвертации MIF в TAB",
    )
    logger.info("Временный TAB создан: %s", tmp_tab)

    # Шаг 2: append временного TAB в основной слой
    # -nln указывает имя слоя в целевом TAB (берём из имени файла без расширения)
    layer_name = tab_layer_path.stem
    _run_ogr2ogr(
        [
            "ogr2ogr",
            "-f", "MapInfo File",
            "-append",
            "-nln", layer_name,
            "-lco", "ENCODING=CP1251",
            str(tab_layer_path),
            str(tmp_tab),
        ],
        error_context="Ошибка добавления в основной слой",
    )
    logger.info("Объект добавлен в слой: %s", tab_layer_path)


def _run_ogr2ogr(cmd: list[str], error_context: str) -> None:
    """Запуск ogr2ogr с проверкой результата."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "Утилита ogr2ogr не найдена. "
            "Установите GDAL: apt-get install gdal-bin"
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"{error_context}: превышено время ожидания (60 сек). "
            "Возможно, слой заблокирован другим процессом."
        )

    if result.returncode != 0:
        stderr = result.stderr.strip() if result.stderr else "нет деталей"
        raise RuntimeError(f"{error_context}: {stderr}")
