# backend/models/refusal.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Refusal(Base):
    """Отказы в выдаче ГПЗУ"""
    
    __tablename__ = "refusals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с заявлением
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Исходящие реквизиты
    out_number = Column(Integer, nullable=False, index=True)
    out_date = Column(String(10), nullable=False)
    out_year = Column(Integer, nullable=False, index=True)
    
    # Причина отказа
    reason_code = Column(String(50), nullable=False)
    reason_text = Column(Text, nullable=True)
    
    # Вложение
    attachment = Column(String(500), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    application = relationship("Application", back_populates="refusal")
    
    __table_args__ = (
        UniqueConstraint('out_year', 'out_number', name='uq_refusal_year_number'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "out_number": self.out_number,
            "out_date": self.out_date,
            "out_year": self.out_year,
            "reason_code": self.reason_code,
            "reason_text": self.reason_text,
            "attachment": self.attachment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def get_next_refusal_number(db, year=None):
    if year is None:
        year = datetime.now().year
    max_number = db.query(func.max(Refusal.out_number)).filter(Refusal.out_year == year).scalar()
    return (max_number or 0) + 1
