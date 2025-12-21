#!/usr/bin/env python3
"""
Полный тестовый скрипт генерации рабочего набора MapInfo.

ОБНОВЛЕНО:
- Новая структура папок: GP_Graphics_<cadnum>/
- Подпапка "База_проекта" для всех слоёв
- Автоматическое создание README.txt
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
    get_project_base_dir,  # ✅ НОВАЯ ФУНКЦИЯ
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
    
    # ========== ШАГ 2: Пространственный анализ ========== #
    
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
                restr = zone.restriction
                if len(restr) > 60:
                    restr = restr[:57] + "..."
                print(f"         {restr}")
    print()
    
    # ========== ШАГ 3: Создание рабочей директории ========== #
    
    print("ШАГ 3: Создание структуры папок")
    print("-" * 80)
    
    # Создаём корневую папку проекта
    workspace_dir = create_workspace_directory(workspace.parcel.cadnum)
    print(f"✅ Корневая папка: {workspace_dir}")
    
    # Получаем путь к подпапке для слоёв
    project_base = get_project_base_dir(workspace_dir)
    print(f"✅ Подпапка слоёв: {project_base.relative_to(workspace_dir)}")
    print(f"✅ README.txt создан")
    print()
    
    # ========== ШАГ 4: Генерация MIF/MID файлов ========== #
    
    print("ШАГ 4: Генерация MIF/MID файлов в подпапке 'База_проекта'")
    print("-" * 80)
    
    # ✅ Все файлы создаются в подпапке project_base
    mif1, mid1 = create_parcel_mif(workspace.parcel, project_base)
    print(f"✅ {mif1.name} и {mid1.name}")
    
    mif2, mid2 = create_parcel_points_mif(workspace.parcel, project_base)
    print(f"✅ {mif2.name} и {mid2.name}")
    
    mif3, mid3 = create_building_zone_mif(
        workspace.building_zone, 
        workspace.parcel.cadnum, 
        project_base
    )
    print(f"✅ {mif3.name} и {mid3.name}")
    
    result_oks = create_oks_mif(workspace.capital_objects, project_base)
    if result_oks:
        mif4, mid4 = result_oks
        print(f"✅ {mif4.name} и {mid4.name} ({len(workspace.capital_objects)} объектов)")
    else:
        print(f"⊘  ОКС пропущены (нет данных или геометрии)")
    
    result_zouit = create_zouit_mif(workspace.zouit, project_base)
    if result_zouit:
        print(f"✅ Создано отдельных слоёв ЗОУИТ: {len(result_zouit)}")
        for i, (mif, mid) in enumerate(result_zouit, start=1):
            if i <= 3:
                print(f"   {i}. {mif.name}")
        if len(result_zouit) > 3:
            print(f"   ... и ещё {len(result_zouit) - 3} слоёв")
    else:
        print(f"⊘  ЗОУИТ пропущены (нет данных или геометрии)")
    
    # ========== ШАГ 4-Б: Создание слоя подписей ЗОУИТ ========== #
    
    if result_zouit and workspace.parcel.geometry:
        print()
        print("ШАГ 4-Б: Создание слоя подписей ЗОУИТ")
        print("-" * 80)
        
        from generator.mif_writer import create_zouit_labels_mif
        
        result_labels = create_zouit_labels_mif(
            zouit_list=workspace.zouit,
            parcel_geometry=workspace.parcel.geometry,
            output_dir=project_base
        )
        
        if result_labels:
            mif_labels, mid_labels = result_labels
            print(f"✅ {mif_labels.name} - слой подписей ЗОУИТ")
            print(f"   Точки размещены в центре пересечения зон с участком")
        else:
            print(f"⊘  Слой подписей не создан (нет пересечений)")
        print()

    print()
    
    # ========== ШАГ 5: Конвертация MIF → TAB ========== #
    
    print("ШАГ 5: Конвертация MIF → TAB в подпапке")
    print("-" * 80)
    
    tab_files = convert_all_mif_to_tab(project_base, remove_mif=True, method='auto')
    print(f"✅ Конвертировано: {len(tab_files)} файлов")
    for tab in sorted(tab_files):
        print(f"   {tab.name}")
    print()
    
    # ========== ШАГ 6: Создание WOR-файла ========== #
    
    print("ШАГ 6: Создание WOR-файла с относительными путями")
    print("-" * 80)
    
    has_oks = result_oks is not None
    
    # ✅ WOR создаётся в корневой папке, слои берутся из подпапки
    wor_path = create_workspace_wor(
        workspace_dir=workspace_dir,
        cadnum=workspace.parcel.cadnum,
        has_oks=has_oks,
        zouit_files=result_zouit,
        has_zouit_labels=(result_labels is not None),
        address=workspace.parcel.address,
        specialist_name="Ляпина К.С.",
        zouit_list=workspace.zouit,   # ✅ ВОТ ЭТО
    )

    print(f"✅ {wor_path.name} создан в корне проекта")
    print()
    
    # ========== ШАГ 7: Итоговая статистика ========== #
    
    print("ШАГ 7: Структура созданного проекта")
    print("-" * 80)
    
    print(f"\n📁 {workspace_dir.name}/")
    print(f"   ├── README.txt")
    print(f"   ├── рабочий_набор.WOR")
    print(f"   └── База_проекта/")
    
    all_files = list(project_base.glob("*.*"))
    print(f"       ├── Слоёв: {len(all_files)}")
    for f in sorted(all_files)[:5]:  # Показываем первые 5
        size_kb = f.stat().st_size / 1024
        print(f"       ├── {f.name:<35} ({size_kb:>8.2f} KB)")
    if len(all_files) > 5:
        print(f"       └── ... и ещё {len(all_files) - 5} файлов")
    
    print()
    
    # ========== ИТОГ ========== #
    
    print("=" * 80)
    print("✅ ТЕСТ ЗАВЕРШЕН!")
    print("=" * 80)
    print(f"📁 Проект создан: {workspace_dir}")
    print()
    print("📊 СТАТИСТИКА:")
    print(f"   Структура:")
    print(f"   ├── README.txt ✅")
    print(f"   ├── рабочий_набор.WOR ✅")
    print(f"   └── База_проекта/ ({len(tab_files)} слоёв) ✅")
    print()
    print(f"   Слои:")
    print(f"   - Участок: ✅")
    print(f"   - Точки участка: ✅")
    print(f"   - Зона строительства: ✅")
    print(f"   - ОКС: {'✅ (' + str(len(workspace.capital_objects)) + ')' if has_oks else '⊘'}")
    print(f"   - ЗОУИТ: {'✅ (' + str(len(result_zouit)) + ' слоёв)' if result_zouit else '⊘'}")
    print()
    print("🗺️  ОТКРЫТИЕ:")
    print(f"   1. Откройте MapInfo Professional")
    print(f"   2. File → Open Workspace...")
    print(f"   3. Выберите: {wor_path}")
    print(f"   4. Откроется 2 карты: Градплан и Ситуационный план")
    print("=" * 80)


if __name__ == "__main__":
    test_file = "/home/gpzu-web/backend/uploads/магазин лесная 14.xml"
    
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
    
    test_full_workspace_with_autosearch(test_file)