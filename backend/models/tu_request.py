# backend/models/tu_request.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class TuRequest(Base):
    """Запросы технических условий в РСО"""
    
    __tablename__ = "tu_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Связь с заявлением
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Исходящие реквизиты
    out_number = Column(Integer, nullable=False, index=True)
    out_date = Column(String(10), nullable=False)
    out_year = Column(Integer, nullable=False, index=True)
    
    # РСО
    rso_type = Column(String(50), nullable=False, index=True)
    rso_name = Column(Text, nullable=True)
    
    # Вложение
    attachment = Column(String(500), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Связи
    application = relationship("Application", back_populates="tu_requests")
    
    __table_args__ = (
        UniqueConstraint('out_year', 'out_number', name='uq_tu_year_number'),
        UniqueConstraint('application_id', 'rso_type', name='uq_tu_application_rso'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "application_id": self.application_id,
            "out_number": self.out_number,
            "out_date": self.out_date,
            "out_year": self.out_year,
            "rso_type": self.rso_type,
            "rso_name": self.rso_name,
            "attachment": self.attachment,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


RSO_TYPES = {
    "vodokanal": {"code": "vodokanal", "name": "ООО «Водоканал»"},
    "gaz": {"code": "gaz", "name": "ООО «Газпром газораспределение Сибирь»"},
    "teplo": {"code": "teplo", "name": "ООО «ЭнергоТранзит», ООО «НТСК»"},
}


def get_next_tu_number(db, year=None):
    if year is None:
        year = datetime.now().year
    max_number = db.query(func.max(TuRequest.out_number)).filter(TuRequest.out_year == year).scalar()
    return (max_number or 0) + 1


def get_rso_info(rso_code):
    return RSO_TYPES.get(rso_code, {"code": rso_code, "name": "Неизвестная РСО"})
