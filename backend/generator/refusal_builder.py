# generator/refusal_builder.py
"""
Генератор документов отказов в выдаче ГПЗУ.

ОБНОВЛЕНО (08.12.2024):
- ✅ Добавлена поддержка phone и email
- ✅ УБРАН STUB - используются ТОЛЬКО готовые шаблоны
- ✅ Улучшена обработка ошибок и логирование
"""

from __future__ import annotations
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Tuple
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
    
    Args:
        date_str: Дата в формате «08» декабря 2025 г.
    
    Returns:
        Дата в формате 08.12.2025
    
    Examples:
        >>> convert_date_format("«15» ноября 2025 г.")
        "15.11.2025"
        >>> convert_date_format("15.11.2025")
        "15.11.2025"
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
        # Извлекаем день из «15»
        day_part = date_str.split("«", 1)[1].split("»", 1)[0].strip()
        day = day_part.zfill(2)  # Добавляем ведущий ноль если нужно
        
        # Извлекаем остальную часть: "ноября 2025 г."
        rest = date_str.split("»", 1)[1].strip()
        
        # Убираем "г." и разбиваем на слова
        rest = rest.replace("г.", "").replace("г", "").strip()
        parts = rest.split()
        
        if len(parts) >= 2:
            month_name = parts[0].lower()
            year = parts[1]
            
            # Получаем номер месяца
            month_num = months.get(month_name)
            
            if month_num and year:
                return f"{day}.{month_num}.{year}"
    
    except Exception as ex:
        logger.warning(f"⚠️ Не удалось конвертировать дату '{date_str}': {ex}")
    
    # Если не удалось распарсить, возвращаем как есть
    return date_str


# ================ ОСНОВНАЯ ФУНКЦИЯ ================ #

def build_refusal_document(context: Dict[str, Any]) -> Tuple[bytes, str, str]:
    """
    Формирует документ отказа в выдаче ГПЗУ с автоматической регистрацией в журнале Excel.
    
    Args:
        context: Словарь с данными:
            - app_number: номер заявления
            - app_date: дата заявления
            - applicant: заявитель (ФИО или название организации)
            - phone: телефон заявителя (НОВОЕ)
            - email: email заявителя (НОВОЕ)
            - cadnum: кадастровый номер земельного участка
            - address: адрес участка
            - area: площадь участка (кв.м)
            - permitted_use: вид разрешённого использования
            - reason_code: код причины отказа (NO_RIGHTS, NO_BORDERS, и т.д.)
    
    Returns:
        Tuple[docx_bytes, out_number, out_date] - байты документа, исходящий номер, дата
    
    Raises:
        FileNotFoundError: Если шаблон или журнал не найден
        RuntimeError: Если журнал открыт в другой программе или проблемы с записью
    """
    
    app_number = context.get('app_number', 'б/н')
    reason_code = context.get("reason_code", "NO_RIGHTS")
    
    logger.info(f"📝 Генерация отказа для заявления {app_number}, причина: {reason_code}")
    
    # Проверяем наличие журнала
    if not JOURNAL_PATH.exists():
        raise FileNotFoundError(
            f"❌ Журнал регистрации отказов не найден: {JOURNAL_PATH}\n"
            f"Создайте Excel файл с колонками: "
            f"Исходящий номер | Исходящая дата | Номер заявления | "
            f"Дата заявления | Заявитель | Кадастровый номер | Причина отказа"
        )
    
    # Определяем шаблон по причине отказа
    template_filename = REASON_TEMPLATES.get(reason_code, "refusal_no_rights.docx")
    template_path = TEMPLATES_DIR / template_filename
    
    # === КРИТИЧНО: Проверяем существование шаблона === #
    if not template_path.exists():
        # Формируем понятное сообщение об ошибке
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
    
    # === РАБОТА С ЖУРНАЛОМ EXCEL === #
    
    lock = FileLock(str(JOURNAL_LOCK_PATH), timeout=10)
    
    try:
        with lock:
            # Открываем журнал
            try:
                wb = load_workbook(JOURNAL_PATH)
            except PermissionError:
                raise RuntimeError(
                    "❌ ЖУРНАЛ ОТКРЫТ В ДРУГОЙ ПРОГРАММЕ!\n\n"
                    "Закройте Excel файл и попробуйте снова."
                )
            
            if JOURNAL_SHEET_NAME not in wb.sheetnames:
                raise RuntimeError(
                    f"❌ Лист '{JOURNAL_SHEET_NAME}' не найден в журнале.\n"
                    f"Доступные листы: {', '.join(wb.sheetnames)}"
                )
            
            ws = wb[JOURNAL_SHEET_NAME]
            
            # Находим столбцы по заголовкам
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
            missing = []
            
            for col_name, var_name in required_columns.items():
                col_index = headers.get(col_name)
                if col_index:
                    columns[var_name] = col_index
                else:
                    missing.append(col_name)
            
            if missing:
                raise RuntimeError(
                    f"❌ В журнале отсутствуют обязательные столбцы:\n"
                    f"{', '.join(missing)}\n\n"
                    f"Найденные столбцы: {', '.join(headers.keys())}"
                )
            
            # Находим максимальный исходящий номер
            max_num = 0
            for row in range(2, ws.max_row + 1):
                val = ws.cell(row=row, column=columns["col_out_num"]).value
                if val is None:
                    continue
                try:
                    n = int(str(val).strip())
                    if n > max_num:
                        max_num = n
                except (ValueError, AttributeError):
                    continue
            
            # Присваиваем новый номер
            out_number = max_num + 1
            out_date = datetime.now().strftime("%d.%m.%Y")
            
            # Добавляем новую строку в журнал
            new_row = ws.max_row + 1
            ws.cell(row=new_row, column=columns["col_out_num"], value=out_number)
            ws.cell(row=new_row, column=columns["col_out_date"], value=out_date)
            ws.cell(row=new_row, column=columns["col_app_num"], value=context.get("app_number", ""))
            ws.cell(row=new_row, column=columns["col_app_date"], value=convert_date_format(context.get("app_date", "")))  # === ИЗМЕНЕНО === #
            ws.cell(row=new_row, column=columns["col_applicant"], value=context.get("applicant", ""))
            ws.cell(row=new_row, column=columns["col_cadnum"], value=context.get("cadnum", ""))
            ws.cell(row=new_row, column=columns["col_reason"], value=reason_code)
            
            # Сохраняем журнал
            try:
                wb.save(JOURNAL_PATH)
                logger.info(f"✅ Отказ зарегистрирован в журнале: исх. №{out_number} от {out_date}")
            except PermissionError:
                raise RuntimeError(
                    "❌ Не удалось сохранить журнал!\n"
                    "Закройте Excel и повторите попытку."
                )
            except OSError as ex:
                raise RuntimeError(f"❌ Ошибка сохранения журнала: {ex}")
    
    except Timeout:
        raise RuntimeError(
            "⏳ ЖУРНАЛ ИСПОЛЬЗУЕТСЯ ДРУГИМ ПРОЦЕССОМ\n\n"
            "Подождите несколько секунд и попробуйте снова."
        )
    
    # === ФОРМИРОВАНИЕ ДОКУМЕНТА ИЗ ШАБЛОНА === #
    
    # Подготавливаем контекст для шаблона
    template_context = {
        "OUT_NUM": str(out_number),
        "OUT_DATE": out_date,
        "APP_NUMBER": context.get("app_number", "—"),
        "APP_DATE": convert_date_format(context.get("app_date", "—")),  # === ИЗМЕНЕНО: конвертируем формат === #
        "APPLICANT": context.get("applicant", "—"),
        "PHONE": context.get("phone", "—"),          # === НОВОЕ ПОЛЕ === #
        "EMAIL": context.get("email", "—"),          # === НОВОЕ ПОЛЕ === #
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
    
    # Рендерим шаблон
    try:
        tpl = DocxTemplate(str(template_path))
        tpl.render(template_context)
    except Exception as ex:
        raise RuntimeError(
            f"❌ Ошибка при рендеринге шаблона {template_filename}: {ex}\n\n"
            f"Проверьте корректность переменных в шаблоне."
        )
    
    # Сохраняем в bytes
    bio = BytesIO()
    tpl.save(bio)
    bio.seek(0)
    
    logger.info(f"✅ Документ отказа успешно сформирован (исх. №{out_number})")
    
    return bio.getvalue(), str(out_number), out_date


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def validate_templates() -> Dict[str, bool]:
    """
    Проверяет наличие всех необходимых шаблонов.
    
    Returns:
        Словарь {код_причины: существует_шаблон}
    
    Example:
        >>> validate_templates()
        {
            'NO_RIGHTS': True,
            'NO_BORDERS': True,
            'NOT_IN_CITY': False,
            ...
        }
    """
    result = {}
    for reason_code, template_filename in REASON_TEMPLATES.items():
        template_path = TEMPLATES_DIR / template_filename
        result[reason_code] = template_path.exists()
    return result


def get_missing_templates() -> list:
    """
    Возвращает список отсутствующих шаблонов.
    
    Returns:
        Список имён файлов отсутствующих шаблонов
    
    Example:
        >>> get_missing_templates()
        ['refusal_not_in_city.docx', 'refusal_has_active_gp.docx']
    """
    missing = []
    for reason_code, template_filename in REASON_TEMPLATES.items():
        template_path = TEMPLATES_DIR / template_filename
        if not template_path.exists():
            missing.append(template_filename)
    return missing


def get_templates_status() -> str:
    """
    Возвращает текстовый отчёт о статусе шаблонов.
    
    Returns:
        Многострочная строка с информацией о шаблонах
    """
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


# Для тестирования из командной строки
if __name__ == "__main__":
    print(get_templates_status())