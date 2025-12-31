# backend/models/gp.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class GP(Base):
    """Градостроительные планы"""
    
    __tablename__ = "gp"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с заявлением
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Исходящие реквизиты
    out_number = Column(Integer, nullable=False, index=True)
    out_date = Column(String(10), nullable=False)
    out_year = Column(Integer, nullable=False, index=True)
    
    # XML данные
    xml_data = Column(Text, nullable=True)
    
    # Вложение
    attachment = Column(String(500), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    application = relationship("Application", back_populates="gp")
    
    __table_args__ = (
        UniqueConstraint('out_year', 'out_number', name='uq_gp_year_number'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "out_number": self.out_number,
            "out_date": self.out_date,
            "out_year": self.out_year,
            "xml_data": self.xml_data,
            "attachment": self.attachment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def get_next_gp_number(db, year=None):
    if year is None:
        year = datetime.now().year
    max_number = db.query(func.max(GP.out_number)).filter(GP.out_year == year).scalar()
    return (max_number or 0) + 1
