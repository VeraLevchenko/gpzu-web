# backend/utils/coords.py

from typing import List, Dict, Tuple
from parsers.egrn_parser import Coord as ECoord


def renumber_egrn_contours(contours: List[List[ECoord]]) -> List[List[ECoord]]:
    """
    Пересчитывает нумерацию точек в контурах ЕГРН.

    ИСПРАВЛЕНО: Теперь словарь coord_to_num ГЛОБАЛЬНЫЙ для всего участка,
    а не создается заново для каждого контура!

    Логика:
    - Одинаковые координаты (x, y) во ВСЕМ участке получают один номер
    - Нумерация сквозная (1..N для всего участка)
    - Если точка из контура 2 совпадает с точкой из контура 1 - она получает ТОТ ЖЕ номер
    """
    numbered_contours: List[List[ECoord]] = []
    
    # 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Словарь координат ГЛОБАЛЬНЫЙ для всего участка
    coord_to_num: Dict[Tuple[str, str], int] = {}
    next_global_num = 1

    for contour in contours:
        # ❌ УДАЛЕНО: coord_to_num = {}  # Словарь создавался заново!
        # ✅ ИСПРАВЛЕНО: Используем глобальный словарь coord_to_num
        
        contour_numbered: List[ECoord] = []

        for pt in contour:
            # Нормализуем координаты для сравнения
            normx = pt.x.strip().replace(",", ".")
            normy = pt.y.strip().replace(",", ".")
            key = (normx, normy)

            if key in coord_to_num:
                # Координата уже встречалась ГДЕ-ТО В УЧАСТКЕ (в любом контуре!)
                num_val = coord_to_num[key]
            else:
                # Новая координата для всего участка - присваиваем следующий номер
                num_val = next_global_num
                coord_to_num[key] = num_val
                next_global_num += 1

            contour_numbered.append(
                ECoord(num=str(num_val), x=pt.x, y=pt.y)
            )

        numbered_contours.append(contour_numbered)

    return numbered_contours
