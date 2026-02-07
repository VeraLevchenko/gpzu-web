# backend/generator/rrr_mapinfo.py
"""
Интеграция с MapInfo для модуля РРР.
Создание MIF/MID и добавление в слой.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from generator.mif_writer import (
    MSK42_COORDSYS,
    escape_mif_string,
    safe_encode_cp1251,
    format_mif_number,
)
from core.layers_config import LayerPaths

logger = logging.getLogger("gpzu-web.rrr_mapinfo")


def add_permit_to_mapinfo(permit: Any) -> bool:
    """
    Добавить разрешение на размещение в слой MapInfo.

    Args:
        permit: Объект PlacementPermit (или dict с to_dict())

    Returns:
        True если успешно
    """
    data = permit if isinstance(permit, dict) else permit.to_dict()

    coordinates = data.get("coordinates")
    if not coordinates or len(coordinates) < 3:
        logger.error("Недостаточно координат для добавления в MapInfo")
        return False

    # Создаём временную директорию для MIF/MID
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        mif_path = tmpdir_path / "rrr_permit.MIF"
        mid_path = tmpdir_path / "rrr_permit.MID"

        try:
            _create_permit_mif(data, mif_path, mid_path)
            logger.info(f"MIF/MID созданы: {mif_path}")

            # Пытаемся конвертировать MIF в TAB и добавить в слой
            output_layer = LayerPaths.RRR_OUTPUT
            if output_layer.exists():
                _append_to_tab_layer(mif_path, output_layer)
            else:
                logger.warning(f"Выходной слой не найден: {output_layer}. MIF/MID созданы, но не добавлены в слой.")

            return True

        except Exception as ex:
            logger.error(f"Ошибка добавления в MapInfo: {ex}")
            return False


def _create_permit_mif(data: dict, mif_path: Path, mid_path: Path):
    """Создать MIF/MID файлы разрешения."""
    coordinates = data.get("coordinates", [])

    # Парсим координаты
    coords = []
    for coord in coordinates:
        try:
            x = float(str(coord.get("x", "")).replace(",", ".").replace(" ", ""))
            y = float(str(coord.get("y", "")).replace(",", ".").replace(" ", ""))
            coords.append((x, y))
        except (ValueError, AttributeError):
            continue

    if len(coords) < 3:
        raise ValueError("Недостаточно координат для полигона")

    # MIF
    with open(mif_path, "wb") as f:
        def w(text: str):
            f.write(text.encode("cp1251"))

        w("Version   450\n")
        w('Charset "WindowsCyrillic"\n')
        w('Delimiter ","\n')
        w(f"{MSK42_COORDSYS}\n")
        w("Columns 12\n")
        w("  ID Integer\n")
        w("  Заявитель Char(254)\n")
        w("  Номер_решения Char(100)\n")
        w("  Дата_Решения Char(20)\n")
        w("  Площадь Float\n")
        w("  Дата_окончания Char(20)\n")
        w("  Вид_объекта Char(254)\n")
        w("  Наименование Char(254)\n")
        w("  Местоположение Char(200)\n")
        w("  Примечание Char(254)\n")
        w("  Кадастровый_номер Char(50)\n")
        w("  ДатаЗанесения Char(20)\n")
        w("Data\n\n")

        w("Region  1\n")
        w(f"  {len(coords)}\n")
        for x, y in coords:
            w(f"{x} {y}\n")
        w("    Pen (1,2,0)\n")
        w("    Brush (1,0,16777215)\n")

    # MID
    with open(mid_path, "wb") as f:
        applicant = data.get("org_name") or data.get("person_name") or ""
        decision_number = data.get("decision_number") or ""
        decision_date = data.get("decision_date") or ""
        area = format_mif_number(data.get("area"))
        end_date = data.get("end_date") or ""
        object_type = data.get("object_type") or ""
        object_name = data.get("object_name") or ""
        location = data.get("location") or ""
        notes = data.get("notes") or ""
        cadnum = data.get("location") or ""

        from datetime import datetime
        today = datetime.now().strftime("%d.%m.%Y")

        fields = [
            str(data.get("id", 0)),
            escape_mif_string(safe_encode_cp1251(applicant)),
            escape_mif_string(safe_encode_cp1251(decision_number)),
            escape_mif_string(safe_encode_cp1251(decision_date)),
            area,
            escape_mif_string(safe_encode_cp1251(end_date)),
            escape_mif_string(safe_encode_cp1251(object_type)),
            escape_mif_string(safe_encode_cp1251(object_name)),
            escape_mif_string(safe_encode_cp1251(location)),
            escape_mif_string(safe_encode_cp1251(notes)),
            escape_mif_string(safe_encode_cp1251(cadnum)),
            escape_mif_string(safe_encode_cp1251(today)),
        ]

        line = ",".join(fields) + "\n"
        f.write(line.encode("cp1251"))


def _append_to_tab_layer(mif_path: Path, tab_layer_path: Path):
    """
    Попытка добавить MIF данные в существующий TAB слой.
    Использует ogr2ogr если доступен.
    """
    try:
        result = subprocess.run(
            [
                "ogr2ogr",
                "-f", "MapInfo File",
                "-append",
                str(tab_layer_path),
                str(mif_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            logger.info(f"Объект добавлен в слой: {tab_layer_path}")
        else:
            logger.warning(f"ogr2ogr вернул код {result.returncode}: {result.stderr}")
    except FileNotFoundError:
        logger.warning("ogr2ogr не найден. MIF/MID созданы, но не добавлены в TAB.")
    except Exception as ex:
        logger.warning(f"Ошибка добавления в TAB: {ex}")
