#!/usr/bin/env python3
"""Тестовый скрипт для проверки генерации MIF/MID файлов из выписки ЕГРН."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import logging
from parsers.egrn_parser import parse_egrn_xml
from generator.geometry_builder import create_building_zone, get_geometry_info
from generator.mif_writer import (
    create_parcel_mif,
    create_parcel_points_mif,
    create_building_zone_mif,
    create_workspace_directory,
    get_mif_files_list
)
from generator.mif_to_tab_converter import convert_all_mif_to_tab, get_tab_files_list
from generator.wor_builder import create_workspace_wor
from models.workspace_data import ParcelLayer, BuildingZoneLayer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger(__name__)

def test_mif_generation(egrn_file_path: str):
    print("=" * 80)
    print("ТЕСТ: Генерация MIF/MID файлов из выписки ЕГРН")
    print("=" * 80)
    print()
    
    # ШАГ 1: Парсинг ЕГРН
    print("ШАГ 1: Парсинг выписки ЕГРН")
    print("-" * 80)
    
    egrn_path = Path(egrn_file_path)
    if not egrn_path.exists():
        print(f"❌ Файл не найден: {egrn_path}")
        return
    
    with open(egrn_path, 'rb') as f:
        egrn_data = parse_egrn_xml(f.read())
    
    print(f"✅ Кадастровый номер: {egrn_data.cadnum}")
    print(f"   Площадь: {egrn_data.area} кв.м")
    print(f"   Точек границ: {len(egrn_data.coordinates)}")
    print()
    
    # Преобразуем координаты
    coordinates = [(float(c.x.replace(',', '.')), float(c.y.replace(',', '.'))) for c in egrn_data.coordinates]
    
    # ШАГ 2: Создание моделей
    print("ШАГ 2: Создание моделей данных")
    print("-" * 80)
    
    parcel = ParcelLayer(
        cadnum=egrn_data.cadnum or "Без_номера",
        coordinates=coordinates,
        area=float(egrn_data.area) if egrn_data.area else None,
        address=egrn_data.address
    )
    print(f"✅ ParcelLayer создан, площадь: {parcel.geometry.area:.2f} кв.м")
    print()
    
    # ШАГ 3: Зона строительства
    print("ШАГ 3: Создание зоны строительства (буфер -5м)")
    print("-" * 80)
    
    building_zone_geom = create_building_zone(coordinates, buffer_distance=-5.0)
    building_zone = BuildingZoneLayer(geometry=building_zone_geom)
    
    zone_info = get_geometry_info(building_zone_geom)
    print(f"✅ Площадь зоны: {zone_info['area']} кв.м")
    print()
    
    # ШАГ 4: Рабочая директория
    print("ШАГ 4: Создание рабочей директории")
    print("-" * 80)
    
    workspace_dir = create_workspace_directory(parcel.cadnum)
    print(f"✅ Директория: {workspace_dir}")
    print()
    
    # ШАГ 5: Генерация MIF/MID
    print("ШАГ 5: Генерация MIF/MID файлов")
    print("-" * 80)
    
    mif1, mid1 = create_parcel_mif(parcel, workspace_dir)
    print(f"✅ {mif1.name} и {mid1.name}")
    
    mif2, mid2 = create_parcel_points_mif(parcel, workspace_dir)
    print(f"✅ {mif2.name} и {mid2.name}")
    
    mif3, mid3 = create_building_zone_mif(building_zone, parcel.cadnum, workspace_dir)
    print(f"✅ {mif3.name} и {mid3.name}")
    print()
    
    # ШАГ 6: Конвертация MIF → TAB
    print("ШАГ 6: Конвертация MIF → TAB")
    print("-" * 80)
    
    tab_files = convert_all_mif_to_tab(workspace_dir, remove_mif=True, method='auto')
    print(f"✅ Конвертировано: {len(tab_files)} файлов")
    for tab in tab_files:
        print(f"   {tab.name}")
    print()
    
    # ШАГ 7: Создание WOR-файла (рабочий набор)
    print("ШАГ 7: Создание WOR-файла (рабочий набор)")
    print("-" * 80)
    
    wor_path = create_workspace_wor(
        workspace_dir=workspace_dir,
        cadnum=parcel.cadnum,
        has_oks=False,
        has_zouit=False
    )
    print(f"✅ {wor_path.name} создан")
    print()
    
    # ШАГ 8: Список всех файлов
    print("ШАГ 8: Список созданных файлов")
    print("-" * 80)
    
    all_files = list(workspace_dir.glob("*.*"))
    print(f"Всего файлов: {len(all_files)}")
    for f in sorted(all_files):
        size_kb = f.stat().st_size / 1024
        print(f"   {f.name:<35} ({size_kb:>8.2f} KB)")
    print()
    
    print("=" * 80)
    print("✅ ТЕСТ ЗАВЕРШЕН!")
    print(f"📁 Директория: {workspace_dir}")
    print()
    print("ПРОВЕРКА:")
    print(f"  1. Откройте в MapInfo: {wor_path}")
    print(f"  2. Проверьте что все слои отображаются")
    print(f"  3. Проверьте координаты")
    print("=" * 80)

if __name__ == "__main__":
    test_file = "/home/verasheregesh/projects/gpzu-web/backend/uploads/report-f09f88b3-e743-4374-a6f7-08c480bfe63b-Vedomstvo-2025-11-11-231166-42-01[0].xml"
    test_mif_generation(test_file)