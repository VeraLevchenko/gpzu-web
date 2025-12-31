# backend/models/application.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Application(Base):
    """Заявления на выдачу ГПЗУ"""
    
    __tablename__ = "applications"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Реквизиты заявления
    number = Column(String(50), nullable=False, unique=True, index=True)
    date = Column(String(50), nullable=False)
    
    # Заявитель
    applicant = Column(String(500), nullable=False)
    phone = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    
    # Земельный участок
    cadnum = Column(String(50), nullable=False, index=True)
    address = Column(Text, nullable=False)
    area = Column(Float, nullable=True)
    permitted_use = Column(Text, nullable=True)
    
    # Статус
    status = Column(String(20), nullable=False, default="in_progress")
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    gp = relationship("GP", back_populates="application", uselist=False, cascade="all, delete-orphan")
    refusal = relationship("Refusal", back_populates="application", uselist=False, cascade="all, delete-orphan")
    tu_requests = relationship("TuRequest", back_populates="application", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "date": self.date,
            "applicant": self.applicant,
            "phone": self.phone,
            "email": self.email,
            "cadnum": self.cadnum,
            "address": self.address,
            "area": self.area,
            "permitted_use": self.permitted_use,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
