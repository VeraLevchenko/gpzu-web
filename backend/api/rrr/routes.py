# backend/api/rrr/routes.py
"""
API роутер модуля РРР (Разрешение на Размещение Ресурсов).
12 эндпойнтов для работы с разрешениями на размещение объектов.
"""

import logging
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from database import get_db
from models.placement_permit import PlacementPermit
from api.rrr.schemas import (
    PlacementPermitCreate,
    PlacementPermitUpdate,
    SpatialAnalysisRequest,
    KaitenCreateRequest,
    MapInfoAddRequest,
    DecisionGenerateRequest,
)

logger = logging.getLogger("gpzu-web.rrr")

router = APIRouter(prefix="/api/rrr", tags=["rrr"])


# ========================================================================
# СПРАВОЧНИКИ (до /{permit_id}, чтобы не перехватывался)
# ========================================================================

@router.get("/object-types")
async def get_object_types():
    """Справочник видов объектов (38 пунктов Постановления 1300)."""
    try:
        from utils.rrr_deadline import get_object_types
        return {"success": True, "data": get_object_types()}
    except Exception as ex:
        logger.error(f"Ошибка загрузки справочника: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка: {str(ex)}")


# ========================================================================
# CRUD
# ========================================================================

@router.get("/list")
async def get_permits_list(
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Список разрешений с пагинацией, поиском и фильтрами."""
    query = db.query(PlacementPermit)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (PlacementPermit.app_number.ilike(search_filter))
            | (PlacementPermit.org_name.ilike(search_filter))
            | (PlacementPermit.person_name.ilike(search_filter))
        )

    if status:
        query = query.filter(PlacementPermit.status == status)

    total = query.count()
    items = query.order_by(PlacementPermit.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "total": total,
        "items": [item.to_dict() for item in items],
        "skip": skip,
        "limit": limit,
    }


@router.post("/create")
async def create_permit(
    data: PlacementPermitCreate,
    db: Session = Depends(get_db),
):
    """Создать новое разрешение на размещение."""
    app_date_parsed = _parse_date(data.app_date)
    deadline_days = data.service_deadline_days
    deadline_date = _parse_date(data.service_deadline_date)

    # Автоматический расчёт даты окончания срока оказания услуги
    if not deadline_date and app_date_parsed and deadline_days:
        try:
            from parsers.application_parser import add_working_days
            deadline_date = add_working_days(app_date_parsed, deadline_days)
        except Exception:
            pass

    permit = PlacementPermit(
        status=data.status or "зарегистрировано",
        org_name=data.org_name,
        org_inn=data.org_inn,
        org_ogrn=data.org_ogrn,
        org_address=data.org_address,
        applicant_type=data.applicant_type,
        submission_method=data.submission_method,
        person_name=data.person_name,
        person_passport=data.person_passport,
        person_address=data.person_address,
        app_number=data.app_number,
        app_date=app_date_parsed,
        object_type=data.object_type,
        object_name=data.object_name,
        term_months=data.term_months,
        service_deadline_days=deadline_days,
        service_deadline_date=deadline_date,
        decision_number=data.decision_number,
        decision_date=_parse_date(data.decision_date),
        end_date=_parse_date(data.end_date),
        area=data.area,
        location=data.location,
        coordinates=data.coordinates,
        has_payment=data.has_payment,
        payment_amount=data.payment_amount,
        proezd_agreement=data.proezd_agreement,
        notes=data.notes,
    )

    db.add(permit)
    db.commit()
    db.refresh(permit)

    return {"success": True, "data": permit.to_dict()}


@router.get("/{permit_id}")
async def get_permit(permit_id: int, db: Session = Depends(get_db)):
    """Получить карточку разрешения по ID."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")
    return permit.to_dict()


@router.put("/{permit_id}/update")
async def update_permit(
    permit_id: int,
    data: PlacementPermitUpdate,
    db: Session = Depends(get_db),
):
    """Обновить поля разрешения."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")

    update_data = data.dict(exclude_unset=True)

    # Обработка дат
    date_fields = ["app_date", "service_deadline_date", "decision_date", "end_date"]
    for field in date_fields:
        if field in update_data and update_data[field] is not None:
            update_data[field] = _parse_date(update_data[field])

    for field, value in update_data.items():
        setattr(permit, field, value)

    db.commit()
    db.refresh(permit)

    return {"success": True, "data": permit.to_dict()}


@router.delete("/{permit_id}/delete")
async def delete_permit(permit_id: int, db: Session = Depends(get_db)):
    """Удалить разрешение."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")

    db.delete(permit)
    db.commit()

    return {"success": True, "message": f"Разрешение #{permit_id} удалено"}


# ========================================================================
# ПАРСЕРЫ
# ========================================================================

@router.post("/parse-application")
async def parse_application(file: UploadFile = File(...)):
    """Парсинг заявления DOCX для РРР."""
    if not file.filename.lower().endswith((".docx", ".doc")):
        raise HTTPException(status_code=400, detail="Ожидается файл DOCX")

    content = await file.read()

    try:
        from parsers.rrr_application_parser import parse_rrr_application_docx
        result = parse_rrr_application_docx(content)

        return {
            "success": True,
            "data": {
                "org_name": result.org_name,
                "inn": result.inn,
                "ogrn": result.ogrn,
                "org_address": result.org_address,
                "person_name": result.person_name,
                "person_passport": result.person_passport,
                "person_address": result.person_address,
                "app_number": result.app_number,
                "app_date": result.app_date.isoformat() if result.app_date else None,
                "app_date_text": result.app_date_text,
                "term_months": result.term_months,
            },
        }
    except Exception as ex:
        logger.error(f"Ошибка парсинга заявления: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(ex)}")


@router.post("/parse-xml")
async def parse_xml(file: UploadFile = File(...)):
    """Парсинг XML схемы границ."""
    content = await file.read()

    try:
        from parsers.rrr_xml_parser import parse_rrr_xml
        result = parse_rrr_xml(content)

        return {
            "success": True,
            "data": {
                "cadastral_block": result.cadastral_block,
                "note": result.note,
                "area": result.area,
                "has_coords": result.has_coords,
                "coordinates_count": len(result.coordinates),
                "coordinates": [
                    {"num": c.num, "x": c.x, "y": c.y}
                    for c in result.coordinates
                ],
            },
        }
    except Exception as ex:
        logger.error(f"Ошибка парсинга XML: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(ex)}")


# ========================================================================
# ПРОСТРАНСТВЕННЫЙ АНАЛИЗ
# ========================================================================

@router.post("/spatial-analysis")
async def spatial_analysis(
    data: SpatialAnalysisRequest,
    db: Session = Depends(get_db),
):
    """Выполнить пространственный анализ (по ID или координатам)."""
    coordinates = data.coordinates

    # Если передан permit_id — берём координаты из БД
    if data.permit_id and not coordinates:
        permit = db.query(PlacementPermit).filter(PlacementPermit.id == data.permit_id).first()
        if not permit:
            raise HTTPException(status_code=404, detail="Разрешение не найдено")
        coordinates = permit.coordinates

    if not coordinates:
        raise HTTPException(status_code=400, detail="Координаты не указаны")

    try:
        from utils.spatial_rrr import perform_rrr_spatial_analysis
        result = perform_rrr_spatial_analysis(coordinates)

        # Если передан permit_id — сохраняем результат в БД
        if data.permit_id:
            permit = db.query(PlacementPermit).filter(PlacementPermit.id == data.permit_id).first()
            if permit:
                permit.quarters = result.get("quarters")
                permit.capital_objects = result.get("capital_objects")
                permit.zouit = result.get("zouit")
                permit.red_lines_inside_area = result.get("red_lines_inside_area")
                permit.red_lines_outside_area = result.get("red_lines_outside_area")
                permit.red_lines_description = result.get("red_lines_description")
                permit.ppipm = result.get("ppipm")
                permit.rrr = result.get("rrr")
                permit.preliminary_approval = result.get("preliminary_approval")
                permit.preliminary_approval_kumi = result.get("preliminary_approval_kumi")
                permit.scheme_location = result.get("scheme_location")
                permit.scheme_location_kumi = result.get("scheme_location_kumi")
                permit.scheme_nto = result.get("scheme_nto")
                permit.advertising = result.get("advertising")
                permit.land_bank = result.get("land_bank")
                permit.sheets_500 = result.get("sheets_500")
                permit.warnings = result.get("warnings")
                db.commit()
                db.refresh(permit)

        return {"success": True, "data": result}

    except Exception as ex:
        logger.error(f"Ошибка пространственного анализа: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка анализа: {str(ex)}")


# ========================================================================
# ИНТЕГРАЦИИ
# ========================================================================

@router.post("/kaiten/create")
async def create_kaiten_card(
    data: KaitenCreateRequest,
    db: Session = Depends(get_db),
):
    """Создать карточку в Kaiten для разрешения."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == data.permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")

    applicant = permit.org_name or permit.person_name or "Неизвестен"
    title = f"{permit.app_number or '?'} {applicant}"

    description_parts = []
    if permit.object_name:
        description_parts.append(f"Объект: {permit.object_name}")
    if permit.app_date:
        description_parts.append(f"Дата заявления: {permit.app_date.strftime('%d.%m.%Y')}")
    if permit.service_deadline_date:
        description_parts.append(f"Срок оказания: {permit.service_deadline_date.strftime('%d.%m.%Y')}")
    description = "\n".join(description_parts)

    due_date = None
    if permit.service_deadline_date:
        due_date = permit.service_deadline_date.isoformat()

    try:
        from utils.kaiten_service import create_card, add_card_member
        from core.config import (
            KAITEN_DOMAIN, KAITEN_SPACE_ID,
            KAITEN_RRR_BOARD_ID, KAITEN_RRR_COLUMN_ID, KAITEN_RRR_LANE_ID,
            KAITEN_RRR_TYPE_ID, KAITEN_RRR_MEMBER_ID,
            KAITEN_FIELD_INCOMING_NUMBER, KAITEN_FIELD_INCOMING_DATE,
            KAITEN_FIELD_PERSON_TYPE, KAITEN_FIELD_SUBMIT_METHOD,
            KAITEN_FIELD_OBJECT_TYPE,
            KAITEN_PERSON_TYPE_UL, KAITEN_PERSON_TYPE_FL,
            KAITEN_SUBMIT_METHOD_RRR_EPGU, KAITEN_SUBMIT_METHOD_RRR_MFC, KAITEN_SUBMIT_METHOD_RRR_PERSONAL,
        )

        # Формируем properties
        properties = {}

        logger.info(f"РРР Kaiten: applicant_type={permit.applicant_type}, submission_method={permit.submission_method}")

        if permit.app_number:
            properties[KAITEN_FIELD_INCOMING_NUMBER] = permit.app_number

        if permit.app_date:
            properties[KAITEN_FIELD_INCOMING_DATE] = {
                "date": permit.app_date.isoformat(),
                "time": None,
                "tzOffset": None,
            }

        if permit.applicant_type:
            person_type_value = KAITEN_PERSON_TYPE_UL if permit.applicant_type == "ЮЛ" else KAITEN_PERSON_TYPE_FL
            properties[KAITEN_FIELD_PERSON_TYPE] = [person_type_value]

        if permit.submission_method:
            submit_map = {
                "ЕПГУ": KAITEN_SUBMIT_METHOD_RRR_EPGU,
                "МФЦ": KAITEN_SUBMIT_METHOD_RRR_MFC,
                "Личный прием": KAITEN_SUBMIT_METHOD_RRR_PERSONAL,
            }
            submit_value = submit_map.get(permit.submission_method)
            if submit_value:
                properties[KAITEN_FIELD_SUBMIT_METHOD] = [submit_value]

        if permit.object_type:
            properties[KAITEN_FIELD_OBJECT_TYPE] = permit.object_type

        card_id = await create_card(
            title=title,
            description=description,
            due_date=due_date,
            board_id=KAITEN_RRR_BOARD_ID,
            column_id=KAITEN_RRR_COLUMN_ID,
            lane_id=KAITEN_RRR_LANE_ID,
            type_id=KAITEN_RRR_TYPE_ID if KAITEN_RRR_TYPE_ID else None,
            properties=properties or None,
        )

        if card_id:
            # Назначаем исполнителя
            if KAITEN_RRR_MEMBER_ID:
                await add_card_member(card_id, KAITEN_RRR_MEMBER_ID, member_type=2)

            # Обновляем статус и сохраняем ID карточки в БД
            permit.kaiten_card_id = card_id
            permit.status = "в работе"
            db.commit()

            card_url = f"https://{KAITEN_DOMAIN}/space/{KAITEN_SPACE_ID}/card/{card_id}"
            return {"success": True, "card_id": card_id, "card_url": card_url}
        else:
            raise HTTPException(status_code=500, detail="Не удалось создать карточку Kaiten")

    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Ошибка создания карточки Kaiten: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка Kaiten: {str(ex)}")


@router.post("/mapinfo/add")
async def add_to_mapinfo(
    data: MapInfoAddRequest,
    db: Session = Depends(get_db),
):
    """Добавить разрешение в слой MapInfo."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == data.permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")

    # Серверная валидация обязательных полей
    missing_fields = []
    if not permit.org_name and not permit.person_name:
        missing_fields.append("Заявитель")
    if not permit.area:
        missing_fields.append("Площадь")
    if not permit.object_type:
        missing_fields.append("Вид объекта")
    if not permit.object_name:
        missing_fields.append("Наименование")
    if not permit.app_number:
        missing_fields.append("Входящий номер")
    if not permit.app_date:
        missing_fields.append("Входящая дата")
    if not permit.coordinates or len(permit.coordinates) < 3:
        missing_fields.append("Координаты (минимум 3 точки)")

    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Не заполнены обязательные поля: {', '.join(missing_fields)}",
        )

    try:
        from generator.rrr_mapinfo import add_permit_to_mapinfo
        add_permit_to_mapinfo(permit)
        return {"success": True, "message": "Объект добавлен в слой MapInfo"}

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        logger.error(f"Ошибка merge MapInfo: {re}")
        raise HTTPException(status_code=500, detail=str(re))
    except HTTPException:
        raise
    except Exception as ex:
        logger.error(f"Ошибка добавления в MapInfo: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка MapInfo: {str(ex)}")


# ========================================================================
# ГЕНЕРАЦИЯ ДОКУМЕНТОВ
# ========================================================================

@router.post("/decision/generate")
async def generate_decision(
    data: DecisionGenerateRequest,
    db: Session = Depends(get_db),
):
    """Сгенерировать решение о разрешении размещения (DOCX)."""
    permit = db.query(PlacementPermit).filter(PlacementPermit.id == data.permit_id).first()
    if not permit:
        raise HTTPException(status_code=404, detail="Разрешение не найдено")

    try:
        from generator.rrr_decision_builder import generate_rrr_decision

        # Формируем имя файла
        applicant = permit.org_name or permit.person_name or "unknown"
        safe_name = applicant[:30].replace(" ", "_").replace('"', "")
        filename = f"Решение_РРР_{permit.app_number or permit.id}_{safe_name}.docx"

        output_dir = Path(__file__).resolve().parent.parent.parent / "uploads" / "rrr_decisions"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / filename

        generate_rrr_decision(permit, str(output_path))

        return FileResponse(
            path=str(output_path),
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    except FileNotFoundError as ex:
        raise HTTPException(status_code=500, detail=str(ex))
    except Exception as ex:
        import traceback; traceback.print_exc(); logger.error(f"Ошибка генерации решения: {ex}")
        raise HTTPException(status_code=500, detail=f"Ошибка генерации: {str(ex)}")


# ========================================================================
# УТИЛИТЫ
# ========================================================================

def _parse_date(date_str: Optional[str]) -> Optional[date]:
    """Парсинг строки даты в объект date."""
    if not date_str:
        return None

    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue

    return None
