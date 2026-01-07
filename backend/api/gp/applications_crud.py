# backend/api/gp/applications_crud.py
"""
CRUD API для работы с заявлениями.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from database import get_db
from models.application import Application

router = APIRouter(prefix="/api/gp/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    """Схема для создания заявления"""
    number: str
    date: str
    applicant: str
    phone: str
    email: str
    cadnum: str
    address: str
    area: Optional[float] = None
    permitted_use: Optional[str] = None


class ApplicationUpdate(BaseModel):
    """Схема для обновления заявления"""
    date: Optional[str] = None
    applicant: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    area: Optional[float] = None
    permitted_use: Optional[str] = None
    status: Optional[str] = None


@router.get("")
async def get_applications(
    skip: int = 0,
    limit: int = 100,
    cadnum: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Получить список заявлений"""
    query = db.query(Application)
    
    if cadnum:
        query = query.filter(Application.cadnum.contains(cadnum))
    if status:
        query = query.filter(Application.status == status)
    
    total = query.count()
    items = query.order_by(Application.created_at.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "items": [item.to_dict() for item in items],
        "skip": skip,
        "limit": limit,
    }


@router.get("/{application_id}")
async def get_application(application_id: int, db: Session = Depends(get_db)):
    """Получить детали заявления"""
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Заявление не найдено")
    
    return app.to_dict()


@router.post("")
async def create_application(data: ApplicationCreate, db: Session = Depends(get_db)):
    """Создать новое заявление"""
    
    # Проверяем уникальность номера
    existing = db.query(Application).filter(Application.number == data.number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Заявление с таким номером уже существует")
    
    app = Application(
        number=data.number,
        date=data.date,
        applicant=data.applicant,
        phone=data.phone,
        email=data.email,
        cadnum=data.cadnum,
        address=data.address,
        area=data.area,
        permitted_use=data.permitted_use,
        status="in_progress"
    )
    
    db.add(app)
    db.commit()
    db.refresh(app)
    
    return {"success": True, "data": app.to_dict()}


@router.put("/{application_id}")
async def update_application(
    application_id: int,
    data: ApplicationUpdate,
    db: Session = Depends(get_db)
):
    """Обновить заявление"""
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Заявление не найдено")
    
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(app, field, value)
    
    db.commit()
    db.refresh(app)
    
    return {"success": True, "data": app.to_dict()}


@router.delete("/{application_id}")
async def delete_application(application_id: int, db: Session = Depends(get_db)):
    """Удалить заявление (каскадно удалятся GP, Refusal, TuRequest)"""
    app = db.query(Application).filter(Application.id == application_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Заявление не найдено")
    
    number = app.number
    db.delete(app)
    db.commit()
    
    return {"success": True, "message": f"Заявление {number} удалено"}
