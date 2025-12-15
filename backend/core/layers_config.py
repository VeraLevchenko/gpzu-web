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