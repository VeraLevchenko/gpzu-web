# backend/utils/coords.py

from typing import List, Dict, Tuple
from parsers.egrn_parser import Coord as ECoord


def renumber_egrn_contours(contours: List[List[ECoord]]) -> List[List[ECoord]]:
    """
    Пересчитывает нумерацию точек в контурах ЕГРН.

    Логика:
    - внутри КАЖДОГО контура точки с одинаковыми координатами (x, y) получают один номер;
    - между контурами номера идут сквозняком (1..N для всего участка).

    ВАЖНО: работает с моделью Coord из egrn_parser.
    """
    numbered_contours: List[List[ECoord]] = []
    next_global_num = 1

    for contour in contours:
        # Для каждого контура свой словарь "коорд -> номер"
        coord_to_num: Dict[Tuple[str, str], int] = {}
        contour_numbered: List[ECoord] = []

        for pt in contour:
            # Нормализуем координаты для сравнения
            normx = pt.x.strip().replace(",", ".")
            normy = pt.y.strip().replace(",", ".")
            key = (normx, normy)

            if key in coord_to_num:
                num_val = coord_to_num[key]
            else:
                num_val = next_global_num
                coord_to_num[key] = num_val
                next_global_num += 1

            contour_numbered.append(
                ECoord(num=str(num_val), x=pt.x, y=pt.y)
            )

        numbered_contours.append(contour_numbered)

    return numbered_contours
