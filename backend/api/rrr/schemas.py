# backend/api/rrr/schemas.py
"""
Pydantic схемы для модуля РРР.
"""

from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import date


class PlacementPermitCreate(BaseModel):
    """Схема для создания разрешения на размещение."""
    # Заявитель (юрлицо)
    org_name: Optional[str] = None
    org_inn: Optional[str] = None
    org_ogrn: Optional[str] = None
    org_address: Optional[str] = None
    # Заявитель (физлицо)
    person_name: Optional[str] = None
    person_passport: Optional[str] = None
    person_address: Optional[str] = None
    # Тип заявителя и способ подачи
    applicant_type: Optional[str] = None  # "ЮЛ" / "ФЛ"
    submission_method: Optional[str] = None  # "ЕПГУ" / "Бумажное"
    # Заявление
    app_number: Optional[str] = None
    app_date: Optional[str] = None
    # Объект
    object_type: Optional[str] = None
    object_name: Optional[str] = None
    term_months: Optional[int] = None
    service_deadline_days: Optional[int] = None
    service_deadline_date: Optional[str] = None
    # Решение
    decision_number: Optional[str] = None
    decision_date: Optional[str] = None
    end_date: Optional[str] = None
    # Геоданные
    area: Optional[float] = None
    location: Optional[str] = None
    coordinates: Optional[Any] = None
    # Дополнительно
    notes: Optional[str] = None
    status: Optional[str] = "зарегистрировано"


class PlacementPermitUpdate(BaseModel):
    """Схема для обновления разрешения на размещение."""
    status: Optional[str] = None
    # Заявитель (юрлицо)
    org_name: Optional[str] = None
    org_inn: Optional[str] = None
    org_ogrn: Optional[str] = None
    org_address: Optional[str] = None
    # Заявитель (физлицо)
    person_name: Optional[str] = None
    person_passport: Optional[str] = None
    person_address: Optional[str] = None
    # Тип заявителя и способ подачи
    applicant_type: Optional[str] = None  # "ЮЛ" / "ФЛ"
    submission_method: Optional[str] = None  # "ЕПГУ" / "Бумажное"
    # Заявление
    app_number: Optional[str] = None
    app_date: Optional[str] = None
    # Объект
    object_type: Optional[str] = None
    object_name: Optional[str] = None
    term_months: Optional[int] = None
    service_deadline_days: Optional[int] = None
    service_deadline_date: Optional[str] = None
    # Решение
    decision_number: Optional[str] = None
    decision_date: Optional[str] = None
    end_date: Optional[str] = None
    # Геоданные
    area: Optional[float] = None
    location: Optional[str] = None
    coordinates: Optional[Any] = None
    # Пространственный анализ
    quarters: Optional[str] = None
    red_lines_inside_area: Optional[float] = None
    red_lines_outside_area: Optional[float] = None
    red_lines_description: Optional[str] = None
    capital_objects: Optional[Any] = None
    zouit: Optional[Any] = None
    rrr: Optional[Any] = None
    ppipm: Optional[Any] = None
    preliminary_approval: Optional[Any] = None
    preliminary_approval_kumi: Optional[Any] = None
    scheme_location: Optional[Any] = None
    scheme_location_kumi: Optional[Any] = None
    scheme_nto: Optional[Any] = None
    advertising: Optional[Any] = None
    land_bank: Optional[Any] = None
    # Дополнительно
    notes: Optional[str] = None
    warnings: Optional[str] = None


class SpatialAnalysisRequest(BaseModel):
    """Запрос на пространственный анализ."""
    permit_id: Optional[int] = None
    coordinates: Optional[List[dict]] = None


class KaitenCreateRequest(BaseModel):
    """Запрос на создание карточки Kaiten."""
    permit_id: int


class MapInfoAddRequest(BaseModel):
    """Запрос на добавление в MapInfo."""
    permit_id: int


class DecisionGenerateRequest(BaseModel):
    """Запрос на генерацию решения."""
    permit_id: int
