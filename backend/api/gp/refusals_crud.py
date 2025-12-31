# backend/api/gp/refusals_crud.py
"""
CRUD API для работы с журналом отказов.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
import shutil
import io

from database import get_db
from models.refusal import Refusal

router = APIRouter(prefix="/api/gp/refusals", tags=["refusals"])
ATTACHMENTS_DIR = Path("./uploads/attachments/refusals")


class RefusalUpdate(BaseModel):
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None


@router.get("")
async def get_refusals(
    skip: int = 0,
    limit: int = 100,
    year: Optional[int] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Refusal)
    if year:
        query = query.filter(Refusal.out_year == year)
    total = query.count()
    items = query.order_by(Refusal.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [item.to_dict() for item in items], "skip": skip, "limit": limit}


@router.get("/{refusal_id}")
async def get_refusal(refusal_id: int, db: Session = Depends(get_db)):
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    result = refusal.to_dict()
    if refusal.application:
        result["application"] = refusal.application.to_dict()
    return result


@router.put("/{refusal_id}")
async def update_refusal(refusal_id: int, data: RefusalUpdate, db: Session = Depends(get_db)):
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(refusal, field, value)
    db.commit()
    db.refresh(refusal)
    return {"success": True, "data": refusal.to_dict()}


@router.delete("/{refusal_id}")
async def delete_refusal(refusal_id: int, db: Session = Depends(get_db)):
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    if refusal.attachment:
        attachment_path = Path(refusal.attachment)
        if attachment_path.exists():
            attachment_path.unlink()
    out_number = refusal.out_number
    db.delete(refusal)
    db.commit()
    return {"success": True, "message": f"Отказ №{out_number} удален"}


@router.post("/{refusal_id}/attachment")
async def upload_attachment(refusal_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Файл должен быть DOCX")
    if refusal.attachment:
        old_path = Path(refusal.attachment)
        if old_path.exists():
            old_path.unlink()
    app = refusal.application
    cadnum_safe = app.cadnum.replace(":", "_") if app else "unknown"
    filename = f"otkaz_{refusal.out_number}_{cadnum_safe}.docx"
    file_path = ATTACHMENTS_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    refusal.attachment = str(file_path)
    db.commit()
    return {"success": True, "attachment": str(file_path)}


@router.delete("/{refusal_id}/attachment")
async def delete_attachment(refusal_id: int, db: Session = Depends(get_db)):
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    if not refusal.attachment:
        raise HTTPException(status_code=404, detail="Вложение отсутствует")
    attachment_path = Path(refusal.attachment)
    if attachment_path.exists():
        attachment_path.unlink()
    refusal.attachment = None
    db.commit()
    return {"success": True, "message": "Вложение удалено"}


@router.get("/export/excel")
async def export_to_excel(year: Optional[int] = None, db: Session = Depends(get_db)):
    from datetime import datetime
    from openpyxl import Workbook
    if year is None:
        year = datetime.now().year
    refusals = db.query(Refusal).filter(Refusal.out_year == year).order_by(Refusal.out_number).all()
    wb = Workbook()
    ws = wb.active
    ws.title = f"Отказы {year}"
    headers = ["Исходящий номер", "Исходящая дата", "Номер заявления", "Заявитель", "Кадастровый номер", "Причина"]
    ws.append(headers)
    for r in refusals:
        app = r.application
        ws.append([r.out_number, r.out_date, app.number if app else "", app.applicant if app else "", app.cadnum if app else "", r.reason_code])
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    filename = f"Журнал_отказов_{year}.xlsx"
    return StreamingResponse(excel_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})