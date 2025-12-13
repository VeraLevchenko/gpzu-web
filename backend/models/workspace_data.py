# backend/models/workspace_data.py
"""
Модели данных для модуля подготовки рабочего набора MapInfo.

Содержит структуры данных для:
- Слоя земельного участка
- Слоя зоны строительства (буфер -5м)
- Информации о найденных объектах (ОКС, ЗОУИТ)
- Полного рабочего набора
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Dict, Any
from shapely.geometry import Polygon


@dataclass
class ParcelLayer:
    """
    Слой земельного участка.
    
    Содержит основную информацию об участке и его геометрию.
    """
    cadnum: str                                    # Кадастровый номер
    coordinates: List[Tuple[float, float]]         # Координаты границ [(x, y), ...]
    area: Optional[float] = None                   # Площадь в кв.м
    address: Optional[str] = None                  # Адрес
    geometry: Optional[Polygon] = None             # Геометрия Shapely
    
    def __post_init__(self):
        """Создаем геометрию из координат если не задана"""
        if self.geometry is None and self.coordinates:
            self.geometry = Polygon(self.coordinates)


@dataclass
class BuildingZoneLayer:
    """
    Слой зоны строительства (минимальные отступы от границ ЗУ).
    
    Создается как буфер -5м от границ земельного участка.
    Согласно требованиям к графической части градплана.
    """
    geometry: Polygon                              # Геометрия зоны строительства
    buffer_distance: float = -5.0                  # Расстояние буфера (отрицательное = внутрь)
    
    @property
    def coordinates(self) -> List[Tuple[float, float]]:
        """Получить координаты границ зоны строительства"""
        if self.geometry and not self.geometry.is_empty:
            return list(self.geometry.exterior.coords)
        return []


@dataclass
class CapitalObjectInfo:
    """
    Информация об объекте капитального строительства.
    
    Используется для отображения найденных ОКС в границах участка.
    """
    cadnum: Optional[str] = None                   # Кадастровый номер ОКС
    object_type: Optional[str] = None              # Тип объекта
    purpose: Optional[str] = None                  # Назначение
    area: Optional[float] = None                   # Площадь
    floors: Optional[int] = None                   # Этажность
    geometry: Optional[Any] = None                 # Геометрия (Point/Polygon)


@dataclass
class ZouitInfo:
    """
    Информация о зоне с особыми условиями использования территории.
    
    Используется для отображения найденных ЗОУИТ в границах участка.
    """
    name: Optional[str] = None                     # Наименование ЗОУИТ
    type: Optional[str] = None                     # Тип ограничения
    restriction: Optional[str] = None              # Описание ограничения
    geometry: Optional[Any] = None                 # Геометрия (обычно Polygon)


@dataclass
class WorkspaceData:
    """
    Полные данные для создания рабочего набора MapInfo.
    
    Содержит все необходимые слои и информацию для генерации:
    - TAB-файлов
    - WOR-файла с Map и Layout
    - Условных обозначений
    """
    # Обязательные слои (всегда создаются)
    parcel: ParcelLayer                            # Слой участка
    building_zone: BuildingZoneLayer               # Слой зоны строительства
    
    # Опциональные слои (создаются при наличии объектов)
    capital_objects: List[CapitalObjectInfo] = field(default_factory=list)  # Список ОКС
    zouit: List[ZouitInfo] = field(default_factory=list)                    # Список ЗОУИТ
    
    # Путь к серверному слою красных линий
    red_lines_layer_path: str = "/mnt/graphics/NOVOKUZ/Красные_линии.TAB"
    
    # Метаданные
    created_at: Optional[str] = None               # Дата создания
    output_directory: Optional[str] = None         # Папка для выходных файлов
    
    @property
    def has_capital_objects(self) -> bool:
        """Есть ли ОКС в границах участка"""
        return len(self.capital_objects) > 0
    
    @property
    def has_zouit(self) -> bool:
        """Есть ли ЗОУИТ в границах участка"""
        return len(self.zouit) > 0
    
    @property
    def zouit_types(self) -> List[str]:
        """Получить список типов ЗОУИТ для условных обозначений"""
        types = set()
        for z in self.zouit:
            if z.type:
                types.add(z.type)
        return sorted(list(types))
    
    def get_legend_items(self) -> List[Dict[str, str]]:
        """
        Получить элементы условных обозначений для Layout.
        
        Всегда включает:
        - Границы земельного участка
        - Минимальные отступы (зона строительства)
        - Красные линии
        
        При наличии добавляет:
        - ОКС
        - ЗОУИТ (каждый тип отдельно)
        
        Returns:
            Список словарей с названием и стилем для легенды
        """
        items = [
            {
                "name": "Границы земельного участка",
                "style": "Сплошная линия 0.7 мм",
                "color": "black"
            },
            {
                "name": "Минимальные отступы от границ ЗУ",
                "style": "Линия 1.2 мм, штриховка",
                "color": "black"
            },
            {
                "name": "Красные линии",
                "style": "Сплошная линия",
                "color": "red"
            },
        ]
        
        if self.has_capital_objects:
            items.append({
                "name": "Объекты капитального строительства",
                "style": "Номер в окружности ⌀6 мм",
                "color": "black"
            })
        
        if self.has_zouit:
            zouit_colors = ["yellow", "orange", "cyan", "magenta", "green"]
            for i, zouit_type in enumerate(self.zouit_types):
                color = zouit_colors[i % len(zouit_colors)]
                items.append({
                    "name": f"ЗОУИТ: {zouit_type}",
                    "style": f"Заливка",
                    "color": color
                })
        
        return items
    
    def get_summary(self) -> str:
        """
        Получить текстовую сводку о рабочем наборе.
        
        Returns:
            Многострочная строка с информацией о содержимом
        """
        lines = []
        lines.append("=" * 60)
        lines.append("РАБОЧИЙ НАБОР MAPINFO")
        lines.append("=" * 60)
        lines.append(f"Кадастровый номер: {self.parcel.cadnum}")
        if self.parcel.address:
            lines.append(f"Адрес: {self.parcel.address}")
        if self.parcel.area:
            lines.append(f"Площадь: {self.parcel.area:.2f} кв.м")
        lines.append("")
        
        lines.append("СЛОИ:")
        lines.append("✅ Земельный участок (всегда)")
        lines.append("✅ Зона строительства (буфер -5м)")
        lines.append("✅ Красные линии (с сервера)")
        
        if self.has_capital_objects:
            lines.append(f"✅ ОКС: найдено {len(self.capital_objects)} объектов")
        else:
            lines.append("❌ ОКС: не найдено")
        
        if self.has_zouit:
            lines.append(f"✅ ЗОУИТ: найдено {len(self.zouit)} зон")
            for zouit_type in self.zouit_types:
                count = sum(1 for z in self.zouit if z.type == zouit_type)
                lines.append(f"   • {zouit_type}: {count} шт.")
        else:
            lines.append("❌ ЗОУИТ: не найдено")
        
        lines.append("")
        lines.append("УСЛОВНЫЕ ОБОЗНАЧЕНИЯ:")
        legend = self.get_legend_items()
        for item in legend:
            lines.append(f"  • {item['name']}")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================ #

def create_workspace_data_from_egrn(
    egrn_data: Any,
    capital_objects: List[CapitalObjectInfo],
    zouit: List[ZouitInfo]
) -> WorkspaceData:
    """
    Создать WorkspaceData из данных ЕГРН и результатов пространственного анализа.
    
    Args:
        egrn_data: Объект EGRNData из парсера
        capital_objects: Список найденных ОКС
        zouit: Список найденных ЗОУИТ
    
    Returns:
        Заполненный объект WorkspaceData
    """
    from datetime import datetime
    from .geometry_builder import create_building_zone  # Импорт будет после создания файла
    
    # Преобразуем координаты из ЕГРН в список кортежей
    # В парсере ЕГРН: coord.x = север, coord.y = восток
    coordinates = [(float(c.x), float(c.y)) for c in egrn_data.coordinates if c.x and c.y]
    
    # Создаем слой участка
    parcel = ParcelLayer(
        cadnum=egrn_data.cadnum or "Без номера",
        coordinates=coordinates,
        area=float(egrn_data.area) if egrn_data.area else None,
        address=egrn_data.address
    )
    
    # Создаем зону строительства (буфер -5м)
    building_zone_geom = create_building_zone(coordinates)
    building_zone = BuildingZoneLayer(geometry=building_zone_geom)
    
    # Создаем полный объект
    workspace = WorkspaceData(
        parcel=parcel,
        building_zone=building_zone,
        capital_objects=capital_objects,
        zouit=zouit,
        created_at=datetime.now().isoformat()
    )
    
    return workspace