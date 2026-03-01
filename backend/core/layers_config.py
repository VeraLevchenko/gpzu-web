# core/layers_config.py
"""
Конфигурация путей к слоям TAB на сервере.

ОБНОВЛЕНО: Добавлены слои для второй карты (ситуационный план).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


# ======================== ПУТИ К СЛОЯМ ======================== #

class LayerPaths:
    """
    Пути к файлам TAB со слоями пространственных данных.
    
    Пути читаются из переменных окружения (.env файл).
    """
    
    # Базовая папка (опционально)
    BASE = Path(os.getenv("LAYERS_BASE_PATH", "/mnt/graphics/NOVOKUZ"))
    
    # ===== ОСНОВНЫЕ СЛОИ ===== #
    
    # Территориальные зоны
    ZONES = Path(os.getenv(
        "LAYER_ZONES",
        "/mnt/graphics/NOVOKUZ/_Правила землепользования и застройки/Территориальные_зоны_пр.TAB"
    ))
    
    # Объекты капитального строительства (ACTUAL_OKSN)
    CAPITAL_OBJECTS = Path(os.getenv(
        "LAYER_CAPITAL_OBJECTS",
        "/mnt/graphics/NOVOKUZ/ФГУ участки/ACTUAL_OKSN.TAB"
    ))
    
    # Проекты планировки территории
    PLANNING_PROJECTS = Path(os.getenv(
        "LAYER_PLANNING_PROJECTS",
        "/mnt/graphics/NOVOKUZ/Проекты планировок и межеваний.TAB"
    ))
    
    # ЗОУИТ (все типы в одном файле)
    ZOUIT = Path(os.getenv(
        "LAYER_ZOUIT",
        "/mnt/graphics/NOVOKUZ/ФГУ участки/ACTUAL_ZOUIT.TAB"
    ))
    
    # Объекты культурного наследия (ОКН)
    OKN = Path(os.getenv(
        "LAYER_OKN",
        "/mnt/graphics/NOVOKUZ/ЗОНЫ КУЛЬТУРНОГО НАСЛЕДИЯ/Объекты культурного наследия.TAB"
    ))
    
    # Районы города
    DISTRICTS = Path(os.getenv(
        "LAYER_DISTRICTS",
        "/mnt/graphics/NOVOKUZ/Районы.TAB"
    ))
    
    # ===== СЛОИ ДЛЯ ВТОРОЙ КАРТЫ (СИТУАЦИОННЫЙ ПЛАН) ===== #
    
    # Подписи адресов
    LABELS = Path(os.getenv(
        "LAYER_LABELS",
        "/home/gis_layers/Подписи.TAB"
    ))
    
    # Проезды (дороги)
    ROADS = Path(os.getenv(
        "LAYER_ROADS",
        "/home/gis_layers/Проезды.TAB"
    ))
    
    # Строения (здания)
    BUILDINGS = Path(os.getenv(
        "LAYER_BUILDINGS",
        "/home/gis_layers/Строения.TAB"
    ))
    
    # Земельные участки (подложка)
    ACTUAL_LAND = Path(os.getenv(
        "LAYER_ACTUAL_LAND",
        "/home/gis_layers/ACTUAL_LAND.TAB"
    ))
    
    # ===== ДОПОЛНИТЕЛЬНЫЕ СЛОИ ОКН ===== #
    
    # Зоны охраны ОКН
    OKN_ZONES = Path(os.getenv(
        "LAYER_OKN_ZONES",
        "/mnt/graphics/NOVOKUZ/ЗОНЫ КУЛЬТУРНОГО НАСЛЕДИЯ/Зоны охраны объектов культурного наследия.TAB"
    ))
    
    # Границы территорий ОКН
    OKN_BOUNDARIES = Path(os.getenv(
        "LAYER_OKN_BOUNDARIES",
        "/mnt/graphics/NOVOKUZ/ЗОНЫ КУЛЬТУРНОГО НАСЛЕДИЯ/Границы территорий объектов Культурного наследия.TAB"
    ))
    
    # ===== СЛОИ ДЛЯ МОДУЛЯ РРР (Разрешение на размещение ресурсов) ===== #

    # Кадастровые кварталы
    RRR_CADASTRAL_QUARTERS = Path(os.getenv(
        "LAYER_RRR_CADASTRAL_QUARTERS",
        "/mnt/graphics/NOVOKUZ/ФГУ участки/KK.TAB"
    ))

    # Красные линии (полигон)
    RRR_RED_LINES = Path(os.getenv(
        "LAYER_RRR_RED_LINES",
        "/mnt/graphics/NOVOKUZ/Красные_линии_полигон.TAB"
    ))

    # РРР Заявления (ранее выданные решения)
    RRR_APPLICATIONS = Path(os.getenv(
        "LAYER_RRR_APPLICATIONS",
        "/mnt/rrr/РэРэРэ.TAB"
    ))

    # Предварительное согласование
    RRR_PRELIMINARY_APPROVAL = Path(os.getenv(
        "LAYER_RRR_PRELIMINARY_APPROVAL",
        "/mnt/graphics/NOVOKUZ/Предварительно согласованные.TAB"
    ))

    # Предварительное согласование КУМИ
    RRR_PRELIMINARY_APPROVAL_KUMI = Path(os.getenv(
        "LAYER_RRR_PRELIMINARY_APPROVAL_KUMI",
        "/mnt/graphics/NOVOKUZ/КУМИ_предварительно_согласованные_с_кадастровым_номером.TAB"
    ))

    # Схема расположения
    RRR_SCHEME_LOCATION = Path(os.getenv(
        "LAYER_RRR_SCHEME_LOCATION",
        "/mnt/graphics/NOVOKUZ/Схема расположения.TAB"
    ))

    # Схема расположения КУМИ
    RRR_SCHEME_LOCATION_KUMI = Path(os.getenv(
        "LAYER_RRR_SCHEME_LOCATION_KUMI",
        "/mnt/graphics/NOVOKUZ/КУМИ_схема_расположения.TAB"
    ))

    # Схема НТО
    RRR_SCHEME_NTO = Path(os.getenv(
        "LAYER_RRR_SCHEME_NTO",
        "/mnt/graphics/NOVOKUZ/Схема НТО.TAB"
    ))

    # Реклама
    RRR_ADVERTISING = Path(os.getenv(
        "LAYER_RRR_ADVERTISING",
        "/mnt/graphics/NOVOKUZ/Схема расположения рекламных конструкций.TAB"
    ))

    # Банк ЗУ многодетные
    RRR_LAND_BANK = Path(os.getenv(
        "LAYER_RRR_LAND_BANK",
        "/mnt/graphics/NOVOKUZ/Банк ЗУ многодетные.TAB"
    ))

    # Участки
    RRR_PARCELS = Path(os.getenv(
        "LAYER_RRR_PARCELS",
        "/mnt/graphics/NOVOKUZ/Участки.TAB"
    ))

    # РРР выходной слой (для добавления объектов)
    RRR_OUTPUT = Path(os.getenv(
        "LAYER_RRR_OUTPUT",
        str(Path(__file__).resolve().parent.parent / "gis_layers" / "РэРэРэ.TAB")
    ))

    # Ранее выданные решения РРР (Разрешение на использование ЗУ)
    RRR_PREV_DECISIONS = Path(os.getenv(
        "LAYER_RRR_PREV_DECISIONS",
        str(Path(__file__).resolve().parent.parent / "gis_layers" / "Разрешение на использование ЗУ.TAB")
    ))

    # Листы масштаба 1:500 (планшеты)
    SHEETS_500 = Path(os.getenv(
        "LAYER_SHEETS_500",
        "/mnt/graphics/Номенклатура/Лист_500.TAB"
    ))

    # ===== ЗАГЛУШКИ ДЛЯ ПОКА НЕИСПОЛЬЗУЕМЫХ СЛОЁВ ===== #
    
    # Эти слои пока не используются, но структура готова
    ZOUIT_COMMUNICATIONS = ZOUIT  # Все ЗОУИТ в одном файле
    ZOUIT_SANITARY = ZOUIT
    ZOUIT_WATER = ZOUIT
    ZOUIT_OTHER = ZOUIT
    
    AGO = BASE / "ago.tab"  # Если появится слой АГО
    KRT = BASE / "krt.tab"  # Если появится слой КРТ
    
    
    @classmethod
    def get_all_zouit_layers(cls) -> list[Path]:
        """Получить список всех слоёв ЗОУИТ (пока один файл)"""
        return [cls.ZOUIT]
    
    @classmethod
    def get_situation_map_layers(cls) -> list[Path]:
        """
        Получить список слоёв для второй карты (ситуационный план).
        
        Returns:
            Список путей к TAB файлам для второй карты
        """
        return [
            cls.LABELS,
            cls.ROADS,
            cls.BUILDINGS,
            cls.ACTUAL_LAND
        ]
    
    @classmethod
    def check_layers_exist(cls) -> dict[str, bool]:
        """
        Проверить существование всех основных слоёв.
        
        Returns:
            Словарь {имя_слоя: существует}
        """
        layers = {
            "ZONES": cls.ZONES,
            "CAPITAL_OBJECTS": cls.CAPITAL_OBJECTS,
            "PLANNING_PROJECTS": cls.PLANNING_PROJECTS,
            "ZOUIT": cls.ZOUIT,
            "OKN": cls.OKN,
            "DISTRICTS": cls.DISTRICTS,
            "LABELS": cls.LABELS,
            "ROADS": cls.ROADS,
            "BUILDINGS": cls.BUILDINGS,
            "ACTUAL_LAND": cls.ACTUAL_LAND,
        }
        
        return {name: path.exists() for name, path in layers.items()}

    @classmethod
    def check_rrr_layers_exist(cls) -> dict[str, bool]:
        """
        Проверить существование всех слоёв РРР.

        Returns:
            Словарь {имя_слоя: существует}
        """
        layers = {
            "RRR_CADASTRAL_QUARTERS": cls.RRR_CADASTRAL_QUARTERS,
            "CAPITAL_OBJECTS": cls.CAPITAL_OBJECTS,
            "ZOUIT": cls.ZOUIT,
            "RRR_RED_LINES": cls.RRR_RED_LINES,
            "PLANNING_PROJECTS": cls.PLANNING_PROJECTS,
            "RRR_APPLICATIONS": cls.RRR_APPLICATIONS,
            "RRR_PRELIMINARY_APPROVAL": cls.RRR_PRELIMINARY_APPROVAL,
            "RRR_PRELIMINARY_APPROVAL_KUMI": cls.RRR_PRELIMINARY_APPROVAL_KUMI,
            "RRR_SCHEME_LOCATION": cls.RRR_SCHEME_LOCATION,
            "RRR_SCHEME_LOCATION_KUMI": cls.RRR_SCHEME_LOCATION_KUMI,
            "RRR_SCHEME_NTO": cls.RRR_SCHEME_NTO,
            "RRR_ADVERTISING": cls.RRR_ADVERTISING,
            "RRR_LAND_BANK": cls.RRR_LAND_BANK,
            "RRR_PARCELS": cls.RRR_PARCELS,
            "RRR_OUTPUT": cls.RRR_OUTPUT,
        }

        return {name: path.exists() for name, path in layers.items()}