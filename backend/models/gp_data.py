# models/gp_data.py
"""
Модель данных для градостроительного плана.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import date, datetime
import json


@dataclass
class ApplicationInfo:
    """Данные из заявления"""
    number: Optional[str] = None
    date: Optional[str] = None
    date_text: Optional[str] = None
    applicant: Optional[str] = None
    purpose: Optional[str] = None
    service_date: Optional[str] = None


@dataclass
class ParcelInfo:
    """Данные о земельном участке из ЕГРН"""
    cadnum: Optional[str] = None
    address: Optional[str] = None
    area: Optional[str] = None
    region: Optional[str] = None
    municipality: Optional[str] = None
    settlement: Optional[str] = None
    district: Optional[str] = None  # НОВОЕ: район города
    permitted_use: Optional[str] = None
    coordinates: List[Dict[str, str]] = field(default_factory=list)
    capital_objects_egrn: List[str] = field(default_factory=list)


@dataclass
class TerritorialZoneInfo:
    """Информация о территориальной зоне"""
    name: Optional[str] = None
    code: Optional[str] = None
    vri_main: List[str] = field(default_factory=list)
    vri_conditional: List[str] = field(default_factory=list)
    vri_auxiliary: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    act_reference: Optional[str] = None
    
    # Внутренние поля (не выводятся в JSON через to_dict)
    _multiple_zones: bool = False  # Попадает ли участок в несколько зон
    _all_zones: List[Dict[str, Any]] = field(default_factory=list)  # Все пересекающиеся зоны
    _overlap_percent: Optional[float] = None  # Процент перекрытия с выбранной зоной
    
    @property
    def multiple_zones(self) -> bool:
        return self._multiple_zones
    
    @multiple_zones.setter
    def multiple_zones(self, value: bool):
        self._multiple_zones = value
    
    @property
    def all_zones(self) -> List[Dict[str, Any]]:
        return self._all_zones
    
    @all_zones.setter
    def all_zones(self, value: List[Dict[str, Any]]):
        self._all_zones = value
    
    @property
    def overlap_percent(self) -> Optional[float]:
        return self._overlap_percent
    
    @overlap_percent.setter
    def overlap_percent(self, value: Optional[float]):
        self._overlap_percent = value


@dataclass
class DistrictInfo:
    """НОВОЕ: Информация о районе города"""
    name: Optional[str] = None
    code: Optional[str] = None
    
    def get_display_name(self) -> str:
        """Получить название для отображения"""
        if self.name:
            return self.name
        elif self.code:
            return f"Район {self.code}"
        else:
            return "Район не определён"


@dataclass
class CapitalObject:
    """Объект капитального строительства"""
    cadnum: Optional[str] = None
    object_type: Optional[str] = None
    purpose: Optional[str] = None
    area: Optional[str] = None
    floors: Optional[str] = None
    year_built: Optional[str] = None
    geometry: Optional[Any] = None  # ✅ ДОБАВЛЕНО: ПОЛНАЯ геометрия объекта


@dataclass
class PlanningProject:
    """Проект планировки территории"""
    exists: bool = False
    project_type: Optional[str] = None          # Вид проекта (проект планировки/межевания)
    project_name: Optional[str] = None          # Наименование проекта
    decision_number: Optional[str] = None       # Номер распоряжения
    decision_date: Optional[str] = None         # Дата распоряжения
    decision_authority: Optional[str] = None    # Орган (если есть)
    decision_full: Optional[str] = None         # Полная строка решения (формируется)
    territory: Optional[str] = None             # Территория (если есть)
    
    def get_formatted_description(self) -> str:
        """
        Получить форматированное описание проекта для раздела 5 ГПЗУ.
        
        Формат:
        "распоряжение администрации города Новокузнецка от {Дата} № {Номер}"
        
        Returns:
            Форматированная строка или "Документация по планировке территории не утверждена"
        """
        if not self.exists:
            return "Документация по планировке территории не утверждена"
        
        parts = ["распоряжение администрации города Новокузнецка"]
        
        # Дата распоряжения
        if self.decision_date:
            try:
                from datetime import datetime
                date_str = str(self.decision_date).split()[0]
                
                dt = None
                for fmt in ["%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"]:
                    try:
                        dt = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if dt:
                    formatted_date = dt.strftime("%d.%m.%Y")
                    parts.append(f"от {formatted_date}")
                else:
                    parts.append(f"от {date_str}")
            except Exception:
                parts.append(f"от {self.decision_date}")
        
        # Номер распоряжения
        if self.decision_number:
            parts.append(f"№ {self.decision_number}")
        
        return " ".join(parts)


@dataclass
class RestrictionZone:
    """Зона с особыми условиями использования территории"""
    zone_type: str
    name: Optional[str] = None
    registry_number: Optional[str] = None
    decision_number: Optional[str] = None
    decision_date: Optional[str] = None
    decision_authority: Optional[str] = None
    restrictions: List[str] = field(default_factory=list)
    additional_info: Optional[str] = None
    # 🔥 новые поля
    area_sqm: Optional[float] = None   # площадь пересечения, кв.м
    area: Optional[float] = None       # запасной вариант (для совместимости)
    geometry: Optional[Any] = None     # ✅ ДОБАВЛЕНО: ПОЛНАЯ геометрия ЗОУИТ
    
    def get_full_name(self) -> str:
        """Получить полное название с реестровым номером"""
        if self.name and self.registry_number:
            return f"{self.name} ({self.registry_number})"
        elif self.name:
            return self.name
        elif self.registry_number:
            return f"ЗОУИТ {self.registry_number}"
        else:
            return f"ЗОУИТ ({self.zone_type})"


@dataclass
class GPData:
    """Полная модель данных градплана"""
    application: ApplicationInfo = field(default_factory=ApplicationInfo)
    parcel: ParcelInfo = field(default_factory=ParcelInfo)
    zone: TerritorialZoneInfo = field(default_factory=TerritorialZoneInfo)
    district: DistrictInfo = field(default_factory=DistrictInfo)  # НОВОЕ: информация о районе
    capital_objects: List[CapitalObject] = field(default_factory=list)
    planning_project: PlanningProject = field(default_factory=PlanningProject)
    zouit: List[RestrictionZone] = field(default_factory=list)
    ago: List[RestrictionZone] = field(default_factory=list)
    krt: List[RestrictionZone] = field(default_factory=list)
    okn: List[RestrictionZone] = field(default_factory=list)
    other_restrictions: List[RestrictionZone] = field(default_factory=list)
    ago_index: Optional[str] = None     # "АГО-1", "АГО-2" или None
    ago_geometry: Optional[Any] = None  # геометрия зоны АГО (Polygon/MultiPolygon)
    gp_number: Optional[str] = None
    gp_date: Optional[str] = None
    analysis_completed: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Возвращает словарь только с данными для шаблона.
        
        НЕ включает:
        - warnings (они для пользователя, не для шаблона)
        - errors (они для пользователя, не для шаблона)
        - внутренние поля зоны (_multiple_zones, _all_zones, _overlap_percent)
        """
        # Используем asdict, но убираем лишнее
        data = asdict(self)
        
        # Убираем warnings и errors
        data.pop('warnings', None)
        data.pop('errors', None)
        
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Возвращает JSON только с данными для шаблона"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
    
    def add_error(self, error: str):
        self.errors.append(error)
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def has_restrictions(self) -> bool:
        return bool(self.zouit or self.ago or self.krt or self.okn or self.other_restrictions)
    
    def get_all_restrictions(self) -> List[RestrictionZone]:
        return self.zouit + self.ago + self.krt + self.okn + self.other_restrictions
    
    def get_summary(self) -> str:
        """
        Возвращает текстовую сводку для отправки пользователю в Telegram.
        Текст БЕЗ экранирования, т.к. не используется parse_mode='Markdown'.
        """
        lines = []
        lines.append("📊 СВОДКА ДАННЫХ ДЛЯ ГРАДПЛАНА\n")
        
        lines.append("📄 ЗАЯВЛЕНИЕ:")
        lines.append(f"  Номер: {self.application.number or '—'}")
        lines.append(f"  Заявитель: {self.application.applicant or '—'}")
        lines.append("")
        
        lines.append("🗺 ЗЕМЕЛЬНЫЙ УЧАСТОК:")
        lines.append(f"  Кадастровый номер: {self.parcel.cadnum or '—'}")
        lines.append(f"  Адрес: {self.parcel.address or '—'}")
        lines.append(f"  Площадь: {self.parcel.area or '—'} кв. м")
        # НОВОЕ: добавляем район в сводку
        lines.append(f"  Район: {self.district.get_display_name()}")
        lines.append("")
        
        lines.append("📍 ТЕРРИТОРИАЛЬНАЯ ЗОНА:")
        if self.zone.code or self.zone.name:
            zone_text = f"{self.zone.code or ''} {self.zone.name or ''}"
            lines.append(f"  {zone_text}")
            
            # Если участок в нескольких зонах, показываем это
            if self.zone.multiple_zones and self.zone.all_zones:
                lines.append(f"  ⚠️ Участок пересекается с несколькими зонами:")
                for z in self.zone.all_zones:
                    zone_code = z.get('code', '')
                    zone_name = z.get('name', '')
                    overlap = z.get('overlap_percent', 0)
                    lines.append(f"     • {zone_code} {zone_name} ({overlap:.1f}%)")
                lines.append(f"  ✅ Выбрана зона с максимальным перекрытием")
        else:
            lines.append("  Не определена")
        lines.append("")
        
        lines.append("🏢 ОБЪЕКТЫ КАПСТРОИТЕЛЬСТВА:")
        if self.capital_objects:
            lines.append(f"  Найдено: {len(self.capital_objects)} шт.")
            lines.append("")
            for i, obj in enumerate(self.capital_objects, 1):
                lines.append(f"  {i}. Кадастровый номер: {obj.cadnum or 'не указан'}")
                if obj.object_type:
                    lines.append(f"     Тип: {obj.object_type}")
                if obj.purpose:
                    lines.append(f"     Назначение: {obj.purpose}")
                if obj.area:
                    lines.append(f"     Площадь: {obj.area} кв. м")
                if obj.floors:
                    lines.append(f"     Этажность: {obj.floors}")
                lines.append("")
        else:
            lines.append("  Не найдено")
            lines.append("")
        
        lines.append("📋 ПРОЕКТ ПЛАНИРОВКИ:")
        if self.planning_project.exists:
            lines.append(f"  Участок входит в границы ППТ")
            
            # Показываем вид проекта
            if self.planning_project.project_type:
                lines.append(f"  Вид: {self.planning_project.project_type}")
            
            # Показываем название проекта
            if self.planning_project.project_name:
                name = self.planning_project.project_name
                # Если название слишком длинное, обрезаем
                if len(name) > 100:
                    name = name[:97] + "..."
                lines.append(f'  Название: "{name}"')
            
            # Показываем номер и дату распоряжения
            decision_parts = []
            if self.planning_project.decision_date:
                # Форматируем дату для вывода
                try:
                    from datetime import datetime
                    date_str = str(self.planning_project.decision_date).split()[0]
                    dt = None
                    for fmt in ["%Y-%m-%d", "%d.%m.%Y"]:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    if dt:
                        decision_parts.append(f"от {dt.strftime('%d.%m.%Y')}")
                    else:
                        decision_parts.append(f"от {self.planning_project.decision_date}")
                except:
                    decision_parts.append(f"от {self.planning_project.decision_date}")
            
            if self.planning_project.decision_number:
                decision_parts.append(f"№ {self.planning_project.decision_number}")
            
            if decision_parts:
                lines.append(f"  Распоряжение: {' '.join(decision_parts)}")
            
            # Для документа используется краткий формат
            if self.planning_project.decision_full:
                lines.append(f"  Для документа: {self.planning_project.decision_full}")
        else:
            # ИСПРАВЛЕНО: Если ППТ нет, выводим стандартную фразу
            lines.append(f"  Документация по планировке территории не утверждена")
        lines.append("")
        
        restrictions_count = len(self.get_all_restrictions())
        lines.append("⚠️ ОГРАНИЧЕНИЯ:")
        if restrictions_count > 0:
            lines.append(f"  Всего: {restrictions_count}")
            if self.zouit:
                lines.append(f"  - ЗОУИТ: {len(self.zouit)}")
                for z in self.zouit[:3]:
                    lines.append(f"    • {z.get_full_name()}")
                if len(self.zouit) > 3:
                    lines.append(f"    ... и ещё {len(self.zouit) - 3}")
            if self.okn:
                lines.append(f"  - ОКН: {len(self.okn)}")
        else:
            lines.append("  Отсутствуют")
        
        if self.errors:
            lines.append("\n❌ ОШИБКИ:")
            for err in self.errors:
                lines.append(f"  • {err}")
        
        if self.warnings:
            lines.append("\n⚠️ ПРЕДУПРЕЖДЕНИЯ:")
            for warn in self.warnings:
                lines.append(f"  • {warn}")
        
        return "\n".join(lines)


def create_gp_data_from_parsed(
    application_dict: Dict[str, Any],
    egrn_dict: Dict[str, Any]
) -> GPData:
    gp = GPData()
    
    gp.application = ApplicationInfo(
        number=application_dict.get('number'),
        date=application_dict.get('date'),
        date_text=application_dict.get('date_text'),
        applicant=application_dict.get('applicant'),
        purpose=application_dict.get('purpose'),
        service_date=application_dict.get('service_date'),
    )
    
    coords_list = egrn_dict.get('coordinates', [])
    coords_dicts = []
    if coords_list:
        for c in coords_list:
            # ВАЖНО: Меняем X и Y местами для JSON (как в слоях)
            # ЕГРН: X (север), Y (восток)
            # JSON/Слои: Y (восток), X (север)
            if hasattr(c, 'num'):
                # Меняем местами: x становится y, y становится x
                coords_dicts.append({'num': c.num, 'x': c.y, 'y': c.x})
            elif isinstance(c, dict):
                # Если уже dict, тоже меняем местами
                coords_dicts.append({
                    'num': c.get('num'),
                    'x': c.get('y'),  # Меняем местами
                    'y': c.get('x')   # Меняем местами
                })
    
    gp.parcel = ParcelInfo(
        cadnum=egrn_dict.get('cadnum'),
        address=egrn_dict.get('address'),
        area=egrn_dict.get('area'),
        region=egrn_dict.get('region'),
        municipality=egrn_dict.get('municipality'),
        settlement=egrn_dict.get('settlement'),
        district=egrn_dict.get('district'),  # НОВОЕ: район из ЕГРН (если есть)
        permitted_use=egrn_dict.get('permitted_use'),
        coordinates=coords_dicts,
        capital_objects_egrn=egrn_dict.get('capital_objects', []),
    )
    
    return gp