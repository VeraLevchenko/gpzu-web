# generator/refusal_builder.py
"""
Генератор документов отказов в выдаче ГПЗУ.

ОБНОВЛЕНО (31.12.2024):
- ✅ Запись в базу данных PostgreSQL
- ✅ Автоматическое создание Application если не существует
- ✅ Создание записи Refusal с вложением
- ✅ Дублирование в Excel (для переходного периода)
- ✅ Поддержка phone и email
"""

from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
import logging

from docxtpl import DocxTemplate
from openpyxl import load_workbook
from filelock import FileLock, Timeout


# ================ НАСТРОЙКИ ================ #

BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates" / "refusal"
JOURNAL_PATH = BASE_DIR / "Журнал_регистрации_отказов.xlsx"
JOURNAL_LOCK_PATH = BASE_DIR / "Журнал_регистрации_отказов.xlsx.lock"
JOURNAL_SHEET_NAME = "Лист1"

# Директория для вложений
ATTACHMENTS_DIR = BASE_DIR / "uploads" / "attachments" / "refusals"
ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Маппинг причин отказа на файлы шаблонов
REASON_TEMPLATES = {
    "NO_RIGHTS": "refusal_no_rights.docx",
    "NO_BORDERS": "refusal_no_borders.docx",
    "NOT_IN_CITY": "refusal_not_in_city.docx",
    "OBJECT_NOT_EXISTS": "refusal_object_not_exists.docx",
    "HAS_ACTIVE_GP": "refusal_has_active_gp.docx",
}

# Маппинг причин отказа на текст для переменной REASON_TEXT
REASON_TEXTS = {
    "NO_RIGHTS": (
        "В соответствии с пунктом 2 статьи 57.3 Градостроительного кодекса "
        "Российской Федерации градостроительный план земельного участка выдаётся "
        "лицу, обладающему правами на земельный участок.\n\n"
        "В представленных документах отсутствуют сведения, подтверждающие право "
        "на земельный участок."
    ),
    "NO_BORDERS": (
        "В соответствии с пунктом 2 статьи 57.3 Градостроительного кодекса "
        "Российской Федерации градостроительный план земельного участка не может "
        "быть выдан в отношении земельного участка, границы которого не установлены "
        "в соответствии с требованиями земельного законодательства.\n\n"
        "Границы земельного участка не установлены в Едином государственном реестре недвижимости."
    ),
    "NOT_IN_CITY": (
        "В соответствии с пунктом 1 статьи 57.3 Градостроительного кодекса "
        "Российской Федерации подготовка и выдача градостроительного плана земельного "
        "участка осуществляется органом местного самоуправления.\n\n"
        "Земельный участок расположен за пределами границ муниципального образования."
    ),
    "OBJECT_NOT_EXISTS": (
        "В соответствии с пунктом 10 статьи 48 Градостроительного кодекса "
        "Российской Федерации строительство объектов капитального строительства "
        "осуществляется на земельных участках, в отношении которых в Едином "
        "государственном реестре недвижимости внесены сведения об объекте.\n\n"
        "Сведения об объекте капитального строительства в ЕГРН отсутствуют."
    ),
    "HAS_ACTIVE_GP": (
        "В соответствии с пунктом 21 статьи 57.3 Градостроительного кодекса "
        "Российской Федерации градостроительный план земельного участка действует "
        "в течение трех лет.\n\n"
        "Ранее выданный градостроительный план земельного участка не утратил силу."
    ),
}

logger = logging.getLogger("gpzu-web.refusal_builder")


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def convert_date_format(date_str: str) -> str:
    """
    Конвертирует дату из формата «08» декабря 2025 г. в 08.12.2025
    """
    if not date_str:
        return "—"
    
    # Если уже в нужном формате (DD.MM.YYYY)
    if "." in date_str and len(date_str.split(".")) == 3:
        return date_str
    
    # Словарь месяцев
    months = {
        "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
        "мая": "05", "июня": "06", "июля": "07", "августа": "08",
        "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
    }
    
    try:
        day_part = date_str.split("«", 1)[1].split("»", 1)[0].strip()
        day = day_part.zfill(2)
        
        rest = date_str.split("»", 1)[1].strip()
        rest = rest.replace("г.", "").replace("г", "").strip()
        parts = rest.split()
        
        if len(parts) >= 2:
            month_name = parts[0].lower()
            year = parts[1]
            month_num = months.get(month_name)
            
            if month_num and year:
                return f"{day}.{month_num}.{year}"
    
    except Exception as ex:
        logger.warning(f"⚠️ Не удалось конвертировать дату '{date_str}': {ex}")
    
    return date_str


def get_or_create_application(context: Dict[str, Any], db_session) -> int:
    """
    Находит существующее заявление или создает новое.
    
    Args:
        context: Данные заявления
        db_session: Сессия БД
    
    Returns:
        ID заявления (application_id)
    """
    from models.application import Application
    
    app_number = context.get('app_number', '')
    
    # Ищем существующее заявление
    existing = db_session.query(Application).filter(Application.number == app_number).first()
    
    if existing:
        logger.info(f"✅ Найдено существующее заявление #{app_number} (ID: {existing.id})")
        return existing.id
    
    # Создаем новое заявление
    logger.info(f"📝 Создаем новое заявление #{app_number}")
    
    application = Application(
        number=app_number,
        date=convert_date_format(context.get('app_date', '')),
        applicant=context.get('applicant', ''),
        phone=context.get('phone', ''),
        email=context.get('email', ''),
        cadnum=context.get('cadnum', ''),
        address=context.get('address', ''),
        area=float(context.get('area', 0)) if context.get('area') else None,
        permitted_use=context.get('permitted_use', ''),
        status='in_progress'
    )
    
    db_session.add(application)
    db_session.flush()  # Получаем ID без commit
    
    logger.info(f"✅ Заявление создано (ID: {application.id})")
    return application.id


def save_to_database(
    context: Dict[str, Any],
    out_number: int,
    out_date: str,
    attachment_path: str,
    db_session
) -> Optional[int]:
    """
    Сохраняет отказ в базу данных.
    
    Args:
        context: Контекст с данными отказа
        out_number: Исходящий номер
        out_date: Исходящая дата
        attachment_path: Путь к файлу вложения
        db_session: Сессия БД
    
    Returns:
        ID созданной записи Refusal или None при ошибке
    """
    try:
        from models.refusal import Refusal
        
        # Получаем или создаем заявление
        application_id = get_or_create_application(context, db_session)
        
        # Извлекаем год из даты
        try:
            year = int(out_date.split('.')[-1])
        except:
            year = datetime.now().year
        
        # Создаем запись отказа
        refusal = Refusal(
            application_id=application_id,
            out_number=out_number,
            out_date=out_date,
            out_year=year,
            reason_code=context.get('reason_code', 'NO_RIGHTS'),
            reason_text=REASON_TEXTS.get(context.get('reason_code', 'NO_RIGHTS'), ''),
            attachment=attachment_path,
        )
        
        db_session.add(refusal)
        db_session.flush()  # Получаем ID
        
        refusal_id = refusal.id
        
        # Обновляем статус заявления
        from models.application import Application
        app = db_session.query(Application).filter(Application.id == application_id).first()
        if app:
            app.status = 'refused'
        
        db_session.commit()
        
        logger.info(f"✅ Отказ №{out_number} сохранен в БД (ID: {refusal_id}, Application ID: {application_id})")
        return refusal_id
        
    except Exception as ex:
        logger.error(f"❌ Ошибка сохранения в БД: {ex}")
        db_session.rollback()
        return None


def write_to_excel_journal(context: Dict[str, Any], out_number: int, out_date: str) -> bool:
    """
    Дублирует запись в Excel журнал (для переходного периода).
    """
    if not JOURNAL_PATH.exists():
        logger.info("ℹ️ Excel журнал не найден, пропускаем дублирование")
        return False
    
    lock = FileLock(str(JOURNAL_LOCK_PATH), timeout=10)
    
    try:
        with lock:
            wb = load_workbook(JOURNAL_PATH)
            ws = wb[JOURNAL_SHEET_NAME]
            
            headers = {cell.value: cell.column for cell in ws[1] if cell.value}
            
            required_columns = {
                "Исходящий номер": "col_out_num",
                "Исходящая дата": "col_out_date",
                "Номер заявления": "col_app_num",
                "Дата заявления": "col_app_date",
                "Заявитель": "col_applicant",
                "Кадастровый номер": "col_cadnum",
                "Причина отказа": "col_reason",
            }
            
            columns = {}
            for col_name, var_name in required_columns.items():
                col_index = headers.get(col_name)
                if col_index:
                    columns[var_name] = col_index
            
            new_row = ws.max_row + 1
            ws.cell(row=new_row, column=columns.get("col_out_num", 1), value=out_number)
            ws.cell(row=new_row, column=columns.get("col_out_date", 2), value=out_date)
            ws.cell(row=new_row, column=columns.get("col_app_num", 3), value=context.get("app_number", ""))
            ws.cell(row=new_row, column=columns.get("col_app_date", 4), value=convert_date_format(context.get("app_date", "")))
            ws.cell(row=new_row, column=columns.get("col_applicant", 5), value=context.get("applicant", ""))
            ws.cell(row=new_row, column=columns.get("col_cadnum", 6), value=context.get("cadnum", ""))
            ws.cell(row=new_row, column=columns.get("col_reason", 7), value=context.get("reason_code", ""))
            
            wb.save(JOURNAL_PATH)
            logger.info(f"✅ Отказ №{out_number} продублирован в Excel")
            return True
            
    except Exception as ex:
        logger.warning(f"⚠️ Не удалось записать в Excel: {ex}")
        return False


# ================ ОСНОВНАЯ ФУНКЦИЯ ================ #

def build_refusal_document(context: Dict[str, Any]) -> Tuple[bytes, str, str]:
    """
    Формирует документ отказа в выдаче ГПЗУ с регистрацией в БД и Excel.
    
    ОБНОВЛЕНО (31.12.2024): Теперь записывает в БД + создает Application + сохраняет файл.
    
    Args:
        context: Словарь с данными отказа
    
    Returns:
        Tuple[docx_bytes, out_number, out_date] - байты документа, исходящий номер, дата
    
    Raises:
        FileNotFoundError: Если шаблон не найден
        RuntimeError: Проблемы с генерацией
    """
    
    app_number = context.get('app_number', 'б/н')
    reason_code = context.get("reason_code", "NO_RIGHTS")
    
    logger.info(f"📝 Генерация отказа для заявления {app_number}, причина: {reason_code}")
    
    # Проверяем шаблон
    template_filename = REASON_TEMPLATES.get(reason_code, "refusal_no_rights.docx")
    template_path = TEMPLATES_DIR / template_filename
    
    if not template_path.exists():
        available_templates = [f.name for f in TEMPLATES_DIR.glob("*.docx")] if TEMPLATES_DIR.exists() else []
        error_msg = (
            f"❌ ШАБЛОН ОТКАЗА НЕ НАЙДЕН!\n\n"
            f"Причина отказа: {reason_code}\n"
            f"Ожидаемый файл: {template_filename}\n"
            f"Полный путь: {template_path}\n\n"
        )
        if available_templates:
            error_msg += f"Доступные шаблоны в папке:\n"
            for tmpl in available_templates:
                error_msg += f"  • {tmpl}\n"
        else:
            error_msg += f"Папка с шаблонами пуста или не существует: {TEMPLATES_DIR}\n"
        error_msg += (
            f"\n💡 Решение:\n"
            f"1. Убедитесь что файл {template_filename} существует\n"
            f"2. Проверьте путь: {TEMPLATES_DIR}\n"
            f"3. Проверьте права доступа к файлу"
        )
        raise FileNotFoundError(error_msg)
    
    logger.info(f"✅ Используется шаблон: {template_filename}")
    
    # ========== ШАГ 1: ПОЛУЧАЕМ ИСХОДЯЩИЙ НОМЕР ИЗ БД ========== #
    
    from database import SessionLocal
    from models.refusal import get_next_refusal_number
    
    db = SessionLocal()
    
    try:
        current_year = datetime.now().year
        out_number = get_next_refusal_number(db, year=current_year)
        out_date = datetime.now().strftime("%d.%m.%Y")
        
        logger.info(f"📋 Присвоен исходящий номер: {out_number} от {out_date}")
        
        # ========== ШАГ 2: ФОРМИРУЕМ ДОКУМЕНТ ========== #
        
        template_context = {
            "OUT_NUM": str(out_number),
            "OUT_DATE": out_date,
            "APP_NUMBER": context.get("app_number", "—"),
            "APP_DATE": convert_date_format(context.get("app_date", "—")),
            "APPLICANT": context.get("applicant", "—"),
            "PHONE": context.get("phone", "—"),
            "EMAIL": context.get("email", "—"),
            "CADNUM": context.get("cadnum", "—"),
            "ADDRESS": context.get("address", "—"),
            "AREA": context.get("area", "—"),
            "PERMITTED_USE": context.get("permitted_use", "—"),
            "REASON_TEXT": REASON_TEXTS.get(reason_code, "Причина отказа не указана"),
        }
        
        logger.info(
            f"📋 Данные для шаблона: "
            f"заявитель={template_context['APPLICANT']}, "
            f"тел={template_context['PHONE']}, "
            f"email={template_context['EMAIL']}"
        )
        
        tpl = DocxTemplate(str(template_path))
        tpl.render(template_context)
        
        doc_buffer = BytesIO()
        tpl.save(doc_buffer)
        doc_buffer.seek(0)
        docx_bytes = doc_buffer.read()
        
        logger.info(f"📄 Документ сформирован ({len(docx_bytes)} байт)")
        
        # ========== ШАГ 3: СОХРАНЯЕМ ФАЙЛ КАК ВЛОЖЕНИЕ ========== #
        
        cadnum_safe = context.get("cadnum", "unknown").replace(":", "_")
        filename = f"otkaz_{out_number}_{cadnum_safe}.docx"
        file_path = ATTACHMENTS_DIR / filename
        
        with open(file_path, "wb") as f:
            f.write(docx_bytes)
        
        logger.info(f"💾 Файл сохранен: {file_path}")
        
        # ========== ШАГ 4: ЗАПИСЫВАЕМ В БД (Application + Refusal) ========== #
        
        refusal_id = save_to_database(
            context=context,
            out_number=out_number,
            out_date=out_date,
            attachment_path=str(file_path),
            db_session=db
        )
        
        if refusal_id:
            logger.info(f"✅ Запись в БД создана (Refusal ID: {refusal_id})")
        else:
            logger.warning("⚠️ Не удалось создать запись в БД")
        
        # ========== ШАГ 5: ДУБЛИРУЕМ В EXCEL (ОПЦИОНАЛЬНО) ========== #
        
        write_to_excel_journal(context, out_number, out_date)
        
        # ========== ВОЗВРАЩАЕМ РЕЗУЛЬТАТ ========== #
        
        logger.info(f"✅ Документ отказа успешно сформирован (исх. №{out_number})")
        
        return docx_bytes, str(out_number), out_date
        
    except Exception as ex:
        db.rollback()
        raise RuntimeError(f"Ошибка генерации отказа: {ex}")
    finally:
        db.close()


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПРОВЕРКИ ================ #

def validate_templates() -> Dict[str, bool]:
    """Проверяет наличие всех необходимых шаблонов."""
    result = {}
    for reason_code, template_filename in REASON_TEMPLATES.items():
        template_path = TEMPLATES_DIR / template_filename
        result[reason_code] = template_path.exists()
    return result


def get_missing_templates() -> list:
    """Возвращает список отсутствующих шаблонов."""
    missing = []
    for reason_code, template_filename in REASON_TEMPLATES.items():
        template_path = TEMPLATES_DIR / template_filename
        if not template_path.exists():
            missing.append(template_filename)
    return missing


def get_templates_status() -> str:
    """Возвращает текстовый отчёт о статусе шаблонов."""
    lines = []
    lines.append("=" * 60)
    lines.append("СТАТУС ШАБЛОНОВ ОТКАЗОВ")
    lines.append("=" * 60)
    lines.append(f"Папка шаблонов: {TEMPLATES_DIR}")
    lines.append("")
    
    status = validate_templates()
    total = len(status)
    available = sum(1 for exists in status.values() if exists)
    
    lines.append(f"Всего шаблонов: {total}")
    lines.append(f"Доступно: {available}")
    lines.append(f"Отсутствует: {total - available}")
    lines.append("")
    
    for reason_code, exists in status.items():
        template_filename = REASON_TEMPLATES[reason_code]
        status_icon = "✅" if exists else "❌"
        lines.append(f"{status_icon} {reason_code:20} -> {template_filename}")
    
    missing = get_missing_templates()
    if missing:
        lines.append("")
        lines.append("⚠️ ОТСУТСТВУЮЩИЕ ШАБЛОНЫ:")
        for filename in missing:
            lines.append(f"   • {filename}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


if __name__ == "__main__":
    print(get_templates_status())