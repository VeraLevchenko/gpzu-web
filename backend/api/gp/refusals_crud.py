# backend/api/gp/refusals_crud.py
"""
CRUD API для работы с журналом отказов.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, String
from typing import Optional
from pathlib import Path
from pydantic import BaseModel
import shutil
import io

from database import get_db
from models.refusal import Refusal
from models.application import Application

router = APIRouter(prefix="/api/gp/refusals", tags=["refusals"])
ATTACHMENTS_DIR = Path("./uploads/attachments/refusals")


class RefusalUpdate(BaseModel):
    out_number: Optional[int] = None
    out_date: Optional[str] = None
    out_year: Optional[int] = None
    reason_code: Optional[str] = None
    reason_text: Optional[str] = None
    application_id: Optional[int] = None


@router.get("/")
async def get_refusals(
    page: int = 1, 
    page_size: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получить список отказов с поиском по всем полям"""
    query = db.query(Refusal).join(Application, Refusal.application_id == Application.id).options(joinedload(Refusal.application))
    
    # Если есть поисковый запрос, фильтруем
    if search:
        search_filter = or_(
            Refusal.out_number.cast(String).ilike(f"%{search}%"),
            Refusal.out_date.ilike(f"%{search}%"),
            Application.number.ilike(f"%{search}%"),
            Application.date.ilike(f"%{search}%"),
            Application.applicant.ilike(f"%{search}%"),
            Application.address.ilike(f"%{search}%"),
            Application.cadnum.ilike(f"%{search}%"),
            Refusal.reason_code.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)
    
    total = query.count()
    refusals = query.order_by(Refusal.out_number.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return {
        "success": True,
        "data": [r.to_dict() for r in refusals],
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    }


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
    
    # === НОВАЯ ПРОВЕРКА: application_id === #
    if 'application_id' in update_data:
        new_application_id = update_data['application_id']
        if new_application_id != refusal.application_id:
            # Проверяем, нет ли уже отказа для этого заявления
            existing = db.query(Refusal).filter(
                Refusal.application_id == new_application_id,
                Refusal.id != refusal_id
            ).first()
            
            if existing:
                raise HTTPException(
                    status_code=400, 
                    detail=f"К заявлению уже привязан другой отказ (ID: {existing.id}, исх. №{existing.out_number})"
                )
    
    # Проверка уникальности номера если изменяется
    if 'out_number' in update_data or 'out_year' in update_data:
        new_number = update_data.get('out_number', refusal.out_number)
        new_year = update_data.get('out_year', refusal.out_year)
        
        existing = db.query(Refusal).filter(
            Refusal.out_number == new_number,
            Refusal.out_year == new_year,
            Refusal.id != refusal_id
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Отказ с номером {new_number} за {new_year} год уже существует")
    
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
    ws.title = f"Otkazy {year}"
    
    # Заголовки как в журнале
    headers = [
        "Исх. №",
        "Исх. дата", 
        "Номер заявления",
        "Дата заявления",
        "Заявитель",
        "Адрес",
        "Кадастровый номер",
        "Причина отказа"
    ]
    ws.append(headers)
    
    # Маппинг кодов причин на русские названия
    reason_labels = {
        'NO_RIGHTS': 'Нет прав на участок',
        'NO_BORDERS': 'Границы не установлены',
        'NOT_IN_CITY': 'Не в городе',
        'OBJECT_NOT_EXISTS': 'Объект не существует',
        'HAS_ACTIVE_GP': 'Есть действующий ГП',
    }
    
    # Заполняем данные
    for r in refusals:
        app = r.application
        ws.append([
            r.out_number,
            r.out_date,
            app.number if app else "—",
            app.date if app else "—",
            app.applicant if app else "—",
            app.address if app else "—",
            app.cadnum if app else "—",
            reason_labels.get(r.reason_code, r.reason_code)
        ])
    
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    
    filename = f"Refusals_{year}.xlsx"
    return StreamingResponse(
        excel_buffer, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{refusal_id}/download")
async def download_refusal_attachment(refusal_id: int, db: Session = Depends(get_db)):
    """Скачать вложение отказа"""
    refusal = db.query(Refusal).filter(Refusal.id == refusal_id).first()
    if not refusal:
        raise HTTPException(status_code=404, detail="Отказ не найден")
    if not refusal.attachment:
        raise HTTPException(status_code=404, detail="Вложение отсутствует")
    
    attachment_path = Path(refusal.attachment)
    if not attachment_path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден на сервере")
    
    # Формируем имя файла для скачивания
    app = refusal.application
    cadnum_safe = app.cadnum.replace(":", "_") if app else "unknown"
    filename = f"Otkaz_{cadnum_safe}_{refusal.out_date.replace('.', '-')}.docx"
    
    return FileResponse(
        path=str(attachment_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )