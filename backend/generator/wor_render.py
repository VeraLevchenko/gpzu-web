# -*- coding: utf-8 -*-
from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping


def _to_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v)


def render_template(text: str, ctx: Mapping[str, Any]) -> str:
    """
    Подставляет значения по ключам {{KEY}} в текст WOR-шаблона.
    """
    out = text
    for k, v in ctx.items():
        out = out.replace("{{" + str(k) + "}}", _to_str(v))
    return out


def ensure_endswith_newline(text: str) -> str:
    return text if text.endswith("\n") else (text + "\n")


def build_ctx_from_workspace(
    workspace: Any,
    *,
    specialist_name: str = "",
) -> dict[str, str]:
    """
    Делает ctx для Layout-шаблонов из объекта WorkspaceData.
    Нужные поля:
      workspace.parcel.cadnum
      workspace.parcel.address
      workspace.created_at (isoformat str или None)
    """
    created_at = getattr(workspace, "created_at", None)
    if created_at:
        try:
            dt = datetime.fromisoformat(created_at)
        except Exception:
            dt = datetime.now()
    else:
        dt = datetime.now()

    parcel = getattr(workspace, "parcel", None)
    cadnum = getattr(parcel, "cadnum", "") if parcel else ""
    address = getattr(parcel, "address", "") if parcel else ""

    return {
        "CADNUM": cadnum or "",
        "ADDRESS": address or "",
        "DATE_DDMMYYYY": dt.strftime("%d.%m.%Y"),
        "SPECIALIST": specialist_name or "",
    }
