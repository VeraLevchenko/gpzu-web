# backend/api/gp/tu_requests_crud.py
"""
CRUD API для работы с журналом запросов ТУ.
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
from models.tu_request import TuRequest, RSO_TYPES

router = APIRouter(prefix="/api/gp/tu-requests", tags=["tu-requests"])
ATTACHMENTS_DIR = Path("./uploads/attachments/tu")


class TuRequestUpdate(BaseModel):
    rso_type: Optional[str] = None
    rso_name: Optional[str] = None


@router.get("")
async def get_tu_requests(skip: int = 0, limit: int = 100, year: Optional[int] = None, rso_type: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(TuRequest)
    if year:
        query = query.filter(TuRequest.out_year == year)
    if rso_type:
        query = query.filter(TuRequest.rso_type == rso_type)
    total = query.count()
    items = query.order_by(TuRequest.created_at.desc()).offset(skip).limit(limit).all()
    return {"total": total, "items": [item.to_dict() for item in items], "skip": skip, "limit": limit}


@router.get("/{request_id}")
async def get_tu_request(request_id: int, db: Session = Depends(get_db)):
    tu_request = db.query(TuRequest).filter(TuRequest.id == request_id).first()
    if not tu_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    result = tu_request.to_dict()
    if tu_request.application:
        result["application"] = tu_request.application.to_dict()
    return result


@router.put("/{request_id}")
async def update_tu_request(request_id: int, data: TuRequestUpdate, db: Session = Depends(get_db)):
    tu_request = db.query(TuRequest).filter(TuRequest.id == request_id).first()
    if not tu_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tu_request, field, value)
    db.commit()
    db.refresh(tu_request)
    return {"success": True, "data": tu_request.to_dict()}


@router.delete("/{request_id}")
async def delete_tu_request(request_id: int, db: Session = Depends(get_db)):
    tu_request = db.query(TuRequest).filter(TuRequest.id == request_id).first()
    if not tu_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if tu_request.attachment:
        attachment_path = Path(tu_request.attachment)
        if attachment_path.exists():
            attachment_path.unlink()
    out_number = tu_request.out_number
    db.delete(tu_request)
    db.commit()
    return {"success": True, "message": f"Запрос ТУ №{out_number} удален"}


@router.post("/{request_id}/attachment")
async def upload_attachment(request_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    tu_request = db.query(TuRequest).filter(TuRequest.id == request_id).first()
    if not tu_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Файл должен быть DOCX")
    if tu_request.attachment:
        old_path = Path(tu_request.attachment)
        if old_path.exists():
            old_path.unlink()
    app = tu_request.application
    cadnum_safe = app.cadnum.replace(":", "_") if app else "unknown"
    filename = f"tu_{tu_request.out_number}_{tu_request.rso_type}_{cadnum_safe}.docx"
    file_path = ATTACHMENTS_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    tu_request.attachment = str(file_path)
    db.commit()
    return {"success": True, "attachment": str(file_path)}


@router.delete("/{request_id}/attachment")
async def delete_attachment(request_id: int, db: Session = Depends(get_db)):
    tu_request = db.query(TuRequest).filter(TuRequest.id == request_id).first()
    if not tu_request:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    if not tu_request.attachment:
        raise HTTPException(status_code=404, detail="Вложение отсутствует")
    attachment_path = Path(tu_request.attachment)
    if attachment_path.exists():
        attachment_path.unlink()
    tu_request.attachment = None
    db.commit()
    return {"success": True, "message": "Вложение удалено"}


@router.get("/export/excel")
async def export_to_excel(year: Optional[int] = None, db: Session = Depends(get_db)):
    from datetime import datetime
    from openpyxl import Workbook
    if year is None:
        year = datetime.now().year
    requests = db.query(TuRequest).filter(TuRequest.out_year == year).order_by(TuRequest.out_number).all()
    wb = Workbook()
    ws = wb.active
    ws.title = f"Запросы ТУ {year}"
    headers = ["Исходящий номер", "Исходящая дата", "Номер заявления", "Заявитель", "Кадастровый номер", "РСО"]
    ws.append(headers)
    for r in requests:
        app = r.application
        ws.append([r.out_number, r.out_date, app.number if app else "", app.applicant if app else "", app.cadnum if app else "", r.rso_name or RSO_TYPES.get(r.rso_type, {}).get('name', r.rso_type)])
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    filename = f"Журнал_запросов_ТУ_{year}.xlsx"
    return StreamingResponse(excel_buffer, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/rso-types")
async def get_rso_types():
    return RSO_TYPES