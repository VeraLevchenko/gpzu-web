# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path


def _templates_dir() -> Path:
    """
    Возвращает каталог с WOR-layout шаблонами:
    backend/templates/wor/layouts/
    """
    backend_dir = Path(__file__).resolve().parents[1]  # .../backend
    return backend_dir / "templates" / "wor" / "layouts"


def load_layout_template(filename: str) -> str:
    """
    Загружает шаблон из templates/wor/layouts по имени файла.
    """
    path = _templates_dir() / filename
    if not path.exists():
        raise FileNotFoundError(f"Не найден WOR-шаблон: {path}")
    return path.read_text(encoding="utf-8", errors="strict")


def load_map1_a3_landscape() -> str:
    return load_layout_template("map1_a3_landscape.wor.txt")


def load_map1_a2_landscape() -> str:
    return load_layout_template("map1_a2_landscape.wor.txt")


def load_map2_a4_landscape() -> str:
    return load_layout_template("map2_a4_landscape.wor.txt")
