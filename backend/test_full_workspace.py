#!/usr/bin/env python3
"""
Полный тестовый скрипт генерации рабочего набора MapInfo.

Автоматически находит все пересечения:
- Участок (полигон)
- Точки участка
- Зона строительства (буфер -5м)
- ОКС (объекты капитального строительства) - АВТОПОИСК
- ЗОУИТ (зоны с особыми условиями) - АВТОПОИСК
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

import logging
from parsers.egrn_parser import parse_egrn_xml
from generator.spatial_adapter import create_workspace_from_egrn
from generator.mif_writer import (
    create_parcel_mif,
    create_parcel_points_mif,
    create_building_zone_mif,
    create_oks_mif,
    create_zouit_mif,
    create_workspace_directory,
)
from generator.mif_to_tab_converter import convert_all_mif_to_tab
from generator.wor_builder import create_workspace_wor

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def test_full_workspace_with_autosearch(egrn_file_path: str):
    """
    Полный тест генерации рабочего набора с автоматическим поиском ОКС и ЗОУИТ.
    
    Args:
        egrn_file_path: Путь к XML-файлу ЕГРН
    """
    
    print("=" * 80)
    print("ТЕСТ: Полная генерация рабочего набора MapInfo с АВТОПОИСКОМ")
    print("=" * 80)
    print()
    
    # ========== ШАГ 1: Парсинг ЕГРН ========== #
    
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
    print(f"   Адрес: {egrn_data.address or 'Не указан'}")
    print(f"   Точек границ: {len(egrn_data.coordinates)}")
    print()
    
    # ========== ШАГ 2: Пространственный анализ и создание WorkspaceData ========== #
    
    print("ШАГ 2: Пространственный анализ (АВТОПОИСК ОКС и ЗОУИТ)")
    print("-" * 80)
    
    try:
        workspace = create_workspace_from_egrn(egrn_data)
    except Exception as e:
        print(f"❌ Ошибка пространственного анализа: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"✅ Участок: {workspace.parcel.cadnum}")
    print(f"   Площадь участка: {workspace.parcel.geometry.area:.2f} кв.м")
    print(f"   Площадь зоны строительства: {workspace.building_zone.geometry.area:.2f} кв.м")
    print()
    
    print(f"🔍 НАЙДЕНО:")
    print(f"   ОКС: {len(workspace.capital_objects)}")
    if workspace.capital_objects:
        for i, oks in enumerate(workspace.capital_objects, 1):
            print(f"      {i}. {oks.cadnum or 'б/н'} - {oks.object_type} ({oks.purpose})")
            if oks.area:
                print(f"         Площадь: {oks.area} кв.м", end="")
            if oks.floors:
                print(f", Этажей: {oks.floors}", end="")
            print()
    
    print(f"   ЗОУИТ: {len(workspace.zouit)}")
    if workspace.zouit:
        for i, zone in enumerate(workspace.zouit, 1):
            print(f"      {i}. {zone.name} ({zone.type})")
            if zone.restriction:
                # Ограничиваем длину для читаемости
                restr = zone.restriction
                if len(restr) > 60:
                    restr = restr[:57] + "..."
                print(f"         {restr}")
    print()
    
    # ========== ШАГ 3: Создание рабочей директории ========== #
    
    print("ШАГ 3: Создание рабочей директории")
    print("-" * 80)
    
    workspace_dir = create_workspace_directory(workspace.parcel.cadnum)
    print(f"✅ Директория: {workspace_dir}")
    print()
    
    #!/usr/bin/env python3
# ФРАГМЕНТ ДЛЯ ЗАМЕНЫ В test_full_workspace.py
# Скопируйте этот блок вместо старого (примерно строки 140-185)

    # ========== ШАГ 4: Генерация MIF/MID файлов ========== #
    
    print("ШАГ 4: Генерация MIF/MID файлов")
    print("-" * 80)
    
    # 4.1 Участок
    mif1, mid1 = create_parcel_mif(workspace.parcel, workspace_dir)
    print(f"✅ {mif1.name} и {mid1.name}")
    
    # 4.2 Точки участка
    mif2, mid2 = create_parcel_points_mif(workspace.parcel, workspace_dir)
    print(f"✅ {mif2.name} и {mid2.name}")
    
    # 4.3 Зона строительства
    mif3, mid3 = create_building_zone_mif(
        workspace.building_zone, 
        workspace.parcel.cadnum, 
        workspace_dir
    )
    print(f"✅ {mif3.name} и {mid3.name}")
    
    # 4.4 ОКС (может вернуть None если нет геометрии)
    result_oks = create_oks_mif(workspace.capital_objects, workspace_dir)
    if result_oks:
        mif4, mid4 = result_oks
        print(f"✅ {mif4.name} и {mid4.name} ({len(workspace.capital_objects)} объектов)")
    else:
        print(f"⊘  ОКС пропущены (нет данных или геометрии)")
    
    # 4.5 ЗОУИТ - каждая зона в отдельном слое ✨ ОБНОВЛЕНО
    result_zouit = create_zouit_mif(workspace.zouit, workspace_dir)
    if result_zouit:
        print(f"✅ Создано отдельных слоёв ЗОУИТ: {len(result_zouit)}")
        for i, (mif, mid) in enumerate(result_zouit, start=1):
            # Показываем первые 3 слоя для краткости
            if i <= 3:
                print(f"   {i}. {mif.name}")
        if len(result_zouit) > 3:
            print(f"   ... и ещё {len(result_zouit) - 3} слоёв")
    else:
        print(f"⊘  ЗОУИТ пропущены (нет данных или геометрии)")
    
    print()
    
    # ========== ШАГ 5: Конвертация MIF → TAB ========== #
    
    print("ШАГ 5: Конвертация MIF → TAB")
    print("-" * 80)
    
    tab_files = convert_all_mif_to_tab(workspace_dir, remove_mif=True, method='auto')
    print(f"✅ Конвертировано: {len(tab_files)} файлов")
    for tab in sorted(tab_files):
        print(f"   {tab.name}")
    print()
    
    # ========== ШАГ 6: Создание WOR-файла ========== #
    
    print("ШАГ 6: Создание WOR-файла (рабочий набор)")
    print("-" * 80)
    
    # ✨ ОБНОВЛЕНО: Передаем список файлов ЗОУИТ
    has_oks = result_oks is not None
    
    wor_path = create_workspace_wor(
        workspace_dir=workspace_dir,
        cadnum=workspace.parcel.cadnum,
        has_oks=has_oks,
        zouit_files=result_zouit  # ✅ Вместо has_zouit
    )
    print(f"✅ {wor_path.name} создан")
    print()
    
    # ========== ШАГ 5: Конвертация MIF → TAB ========== #
    
    print("ШАГ 5: Конвертация MIF → TAB")
    print("-" * 80)
    
    tab_files = convert_all_mif_to_tab(workspace_dir, remove_mif=True, method='auto')
    print(f"✅ Конвертировано: {len(tab_files)} файлов")
    for tab in sorted(tab_files):
        print(f"   {tab.name}")
    print()
    
    # ========== ШАГ 6: Создание WOR-файла ========== #
    
    print("ШАГ 6: Создание WOR-файла (рабочий набор)")
    print("-" * 80)
    
    # Проверяем что файлы действительно созданы
    has_oks = result_oks is not None
    has_zouit = result_zouit is not None
    
    wor_path = create_workspace_wor(
        workspace_dir=workspace_dir,
        cadnum=workspace.parcel.cadnum,
        has_oks=has_oks,
        has_zouit=has_zouit
    )
    print(f"✅ {wor_path.name} создан")
    print()
    
    # ========== ШАГ 7: Итоговая статистика ========== #
    
    print("ШАГ 7: Список созданных файлов")
    print("-" * 80)
    
    all_files = list(workspace_dir.glob("*.*"))
    print(f"Всего файлов: {len(all_files)}")
    for f in sorted(all_files):
        size_kb = f.stat().st_size / 1024
        print(f"   {f.name:<35} ({size_kb:>8.2f} KB)")
    print()
    
    # ========== ИТОГ ========== #
    
    print("=" * 80)
    print("✅ ТЕСТ ЗАВЕРШЕН!")
    print("=" * 80)
    print(f"📁 Директория: {workspace_dir}")
    print()
    print("📊 СТАТИСТИКА:")
    print(f"   Слои создано: {len(tab_files)}")
    print(f"   - Участок: ✅")
    print(f"   - Точки участка: ✅")
    print(f"   - Зона строительства: ✅")
    print(f"   - ОКС: {'✅ (' + str(len(workspace.capital_objects)) + ')' if has_oks else '⊘'}")
    print(f"   - ЗОУИТ: {'✅ (' + str(len(workspace.zouit)) + ')' if has_zouit else '⊘'}")
    print()
    print("🗺️  ОТКРЫТИЕ:")
    print(f"   1. Откройте MapInfo Professional")
    print(f"   2. File → Open Workspace...")
    print(f"   3. Выберите: {wor_path}")
    print(f"   4. Проверьте что все слои отображаются")
    print("=" * 80)


if __name__ == "__main__":
    # Тестовый файл ЕГРН
    test_file = "/home/verasheregesh/projects/gpzu-web/backend/uploads/магазин лесная 14.xml"
    
    # Можно передать путь как аргумент
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    test_full_workspace_with_autosearch(test_file)