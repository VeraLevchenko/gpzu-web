# backend/models/placement_permit.py
"""
SQLAlchemy модель для разрешений на размещение объектов (РРР).
"""

from sqlalchemy import Column, Integer, String, Text, Date, Float, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from database import Base


class PlacementPermit(Base):
    """Разрешения на размещение объектов (РРР)"""

    __tablename__ = "placement_permits"

    id = Column(Integer, primary_key=True, index=True)

    # Метаданные
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    status = Column(String(50), default="зарегистрировано")
    kaiten_card_id = Column(Integer, nullable=True)  # ID карточки в Kaiten

    # Заявитель (юрлицо)
    org_name = Column(String(500), nullable=True)
    org_inn = Column(String(20), nullable=True)
    org_ogrn = Column(String(20), nullable=True)
    org_address = Column(Text, nullable=True)

    # Заявитель (физлицо)
    person_name = Column(String(500), nullable=True)
    person_passport = Column(String(200), nullable=True)
    person_address = Column(Text, nullable=True)

    # Тип заявителя и способ подачи
    applicant_type = Column(String(20), nullable=True)  # "ЮЛ" / "ФЛ"
    submission_method = Column(String(50), nullable=True)  # "ЕПГУ" / "Бумажное"

    # Заявление
    app_number = Column(String(50), nullable=True, index=True)
    app_date = Column(Date, nullable=True)

    # Объект
    object_type = Column(String(500), nullable=True)
    object_name = Column(String(500), nullable=True)
    term_months = Column(Integer, nullable=True)
    service_deadline_days = Column(Integer, nullable=True)
    service_deadline_date = Column(Date, nullable=True)

    # Решение
    decision_number = Column(String(100), nullable=True)
    decision_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    # Геоданные (из XML)
    area = Column(Float, nullable=True)
    location = Column(String(200), nullable=True)
    coordinates = Column(JSONB, nullable=True)

    # Пространственный анализ (простые)
    quarters = Column(Text, nullable=True)
    red_lines_inside_area = Column(Float, nullable=True)
    red_lines_outside_area = Column(Float, nullable=True)
    red_lines_description = Column(Text, nullable=True)

    # Множественные пересечения (JSON массивы)
    capital_objects = Column(JSONB, nullable=True)
    zouit = Column(JSONB, nullable=True)
    rrr = Column(JSONB, nullable=True)
    ppipm = Column(JSONB, nullable=True)
    preliminary_approval = Column(JSONB, nullable=True)
    preliminary_approval_kumi = Column(JSONB, nullable=True)
    scheme_location = Column(JSONB, nullable=True)
    scheme_location_kumi = Column(JSONB, nullable=True)
    scheme_nto = Column(JSONB, nullable=True)
    advertising = Column(JSONB, nullable=True)
    land_bank = Column(JSONB, nullable=True)

    # Дополнительно
    notes = Column(Text, nullable=True)
    warnings = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "status": self.status,
            "kaiten_card_id": self.kaiten_card_id,
            # Заявитель (юрлицо)
            "org_name": self.org_name,
            "org_inn": self.org_inn,
            "org_ogrn": self.org_ogrn,
            "org_address": self.org_address,
            "applicant_type": self.applicant_type,
            "submission_method": self.submission_method,
            # Заявитель (физлицо)
            "person_name": self.person_name,
            "person_passport": self.person_passport,
            "person_address": self.person_address,
            # Заявление
            "app_number": self.app_number,
            "app_date": self.app_date.isoformat() if self.app_date else None,
            # Объект
            "object_type": self.object_type,
            "object_name": self.object_name,
            "term_months": self.term_months,
            "service_deadline_days": self.service_deadline_days,
            "service_deadline_date": self.service_deadline_date.isoformat() if self.service_deadline_date else None,
            # Решение
            "decision_number": self.decision_number,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            # Геоданные
            "area": self.area,
            "location": self.location,
            "coordinates": self.coordinates,
            # Пространственный анализ
            "quarters": self.quarters,
            "red_lines_inside_area": self.red_lines_inside_area,
            "red_lines_outside_area": self.red_lines_outside_area,
            "red_lines_description": self.red_lines_description,
            # Множественные пересечения
            "capital_objects": self.capital_objects,
            "zouit": self.zouit,
            "rrr": self.rrr,
            "ppipm": self.ppipm,
            "preliminary_approval": self.preliminary_approval,
            "preliminary_approval_kumi": self.preliminary_approval_kumi,
            "scheme_location": self.scheme_location,
            "scheme_location_kumi": self.scheme_location_kumi,
            "scheme_nto": self.scheme_nto,
            "advertising": self.advertising,
            "land_bank": self.land_bank,
            # Дополнительно
            "notes": self.notes,
            "warnings": self.warnings,
        }
