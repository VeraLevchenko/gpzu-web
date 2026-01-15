#!/usr/bin/env python3
"""
Тестовый скрипт для проверки:
1. Парсинга заявления
2. Расчёта 14 рабочих дней с учётом праздников из holidays.json
3. Формирования данных для карточки Kaiten
"""

import sys
from pathlib import Path
from datetime import date, timedelta
import json

# Путь к backend проекта
BACKEND_DIR = Path("/home/vera/gpzu-web/backend")
sys.path.insert(0, str(BACKEND_DIR))

from parsers.application_parser import parse_application_docx, is_working_day, RUSSIAN_HOLIDAYS


def print_holidays_2025():
    """Показать все праздники 2025 года из holidays.json"""
    print("\n" + "=" * 80)
    print("РОССИЙСКИЕ ПРАЗДНИКИ 2025 ГОДА (из holidays.json)")
    print("=" * 80)
    
    # Фильтруем праздники 2025 года и сортируем
    holidays_2025 = [h for h in RUSSIAN_HOLIDAYS if h.startswith('2025')]
    holidays_2025.sort()
    
    for h_str in holidays_2025:
        # Парсим строку в дату
        year, month, day = map(int, h_str.split('-'))
        h_date = date(year, month, day)
        print(f"  {h_date.strftime('%d.%m.%Y %A')}")
    
    print(f"\nВсего праздничных дней в 2025: {len(holidays_2025)}")
    print()


def test_working_days_calculation(start_date: date):
    """Детальный расчёт рабочих дней"""
    print("\n" + "=" * 80)
    print("ДЕТАЛЬНЫЙ РАСЧЁТ РАБОЧИХ ДНЕЙ")
    print("=" * 80)
    
    d = start_date
    working_count = 0
    days_list = []
    
    while working_count < 14:
        is_working = is_working_day(d)
        
        # Определяем тип дня
        day_type = ""
        if is_working:
            working_count += 1
            day_type = f"✓ Рабочий день #{working_count}"
        else:
            if d.weekday() in (5, 6):
                day_type = "✗ Выходной (сб/вс)"
            else:
                # Проверяем, есть ли в списке праздников
                date_str = d.strftime('%Y-%m-%d')
                if date_str in RUSSIAN_HOLIDAYS:
                    day_type = "✗ Праздник"
                else:
                    day_type = "✗ Выходной"
        
        days_list.append({
            'date': d,
            'type': day_type,
            'is_working': is_working
        })
        
        d = d + timedelta(days=1)
    
    # Выводим таблицу
    print(f"\nДата начала: {start_date.strftime('%d.%m.%Y (%A)')}")
    print("-" * 80)
    
    for day_info in days_list:
        d = day_info['date']
        print(f"{d.strftime('%d.%m.%Y (%A)'):30} {day_info['type']}")
    
    service_date = days_list[-1]['date']
    calendar_days = (service_date - start_date).days + 1
    
    print("-" * 80)
    print(f"Дата оказания услуги: {service_date.strftime('%d.%m.%Y (%A)')}")
    print(f"Календарных дней: {calendar_days}")
    print(f"Рабочих дней: 14")
    print()
    
    return service_date


def test_application_parsing():
    """Тест парсинга заявления"""
    
    print("\n" + "=" * 80)
    print("ТЕСТ: Парсинг заявления и расчёт срока для Kaiten")
    print("=" * 80)
    
    # Путь к файлу заявления
    application_file = Path("/home/vera/gpzu-web/Заявление 6633861330 о выдаче ГПЗУ.docx")
    
    if not application_file.exists():
        print(f"\n❌ ОШИБКА: Файл не найден: {application_file}")
        print("\nПроверьте путь к файлу.")
        return
    
    print(f"\n📄 Файл: {application_file.name}")
    print(f"   Размер: {application_file.stat().st_size} байт")
    print()
    
    # Парсим заявление
    print("Шаг 1: Парсинг заявления...")
    print("-" * 80)
    
    with open(application_file, 'rb') as f:
        app_data = parse_application_docx(f.read())
    
    # Выводим результаты парсинга
    print(f"✅ Номер заявления: {app_data.number}")
    print(f"✅ Дата заявления: {app_data.date.strftime('%d.%m.%Y') if app_data.date else 'не указана'}")
    print(f"✅ Заявитель: {app_data.applicant}")
    print(f"✅ Кадастровый номер: {app_data.cadnum}")
    print(f"✅ Цель использования: {app_data.purpose}")
    print(f"✅ Телефон: {app_data.phone}")
    print(f"✅ Email: {app_data.email}")
    print()
    
    if not app_data.date:
        print("❌ ОШИБКА: Дата заявления не найдена в документе")
        return
    
    # Показываем праздники
    print_holidays_2025()
    
    # Детальный расчёт
    service_date = test_working_days_calculation(app_data.date)
    
    # Формируем данные для Kaiten
    print("=" * 80)
    print("ДАННЫЕ ДЛЯ КАРТОЧКИ KAITEN")
    print("=" * 80)
    print(f"Название задачи: ГПЗУ #{app_data.number}")
    print(f"Кадастровый номер: {app_data.cadnum}")
    print(f"Заявитель: {app_data.applicant}")
    print(f"Контакты: {app_data.phone or 'не указан'}, {app_data.email or 'не указан'}")
    print(f"Дата создания: {app_data.date.strftime('%d.%m.%Y')}")
    print(f"Срок выполнения: {service_date.strftime('%d.%m.%Y')} (14 рабочих дней)")
    print()
    
    # JSON для API
    print("=" * 80)
    print("JSON ДЛЯ API KAITEN")
    print("=" * 80)
    print(f'''{{
  "title": "ГПЗУ #{app_data.number}",
  "description": "Заявитель: {app_data.applicant}\\nКадастровый номер: {app_data.cadnum}\\nЦель: {app_data.purpose}\\nКонтакты: {app_data.phone or 'не указан'}, {app_data.email or 'не указан'}",
  "due_date": "{service_date.strftime('%Y-%m-%d')}",
  "custom_fields": {{
    "Номер заявления": "{app_data.number}",
    "Кадастровый номер": "{app_data.cadnum}",
    "Дата заявления": "{app_data.date.strftime('%d.%m.%Y')}",
    "Телефон": "{app_data.phone or ''}",
    "Email": "{app_data.email or ''}"
  }}
}}''')
    print()


if __name__ == "__main__":
    try:
        test_application_parsing()
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()