# backend/parsers/rrr_xml_parser.py
"""
Парсер XML-схемы границ для модуля РРР.
Формат: SchemaParcels / NewParcels / NewParcel
"""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BytesIO
from typing import List, Optional
import zipfile
import gzip

from lxml import etree


@dataclass
class RRRCoord:
    """Одна точка контура из XML схемы."""
    num: str
    x: str
    y: str


@dataclass
class RRRXMLData:
    """Результат парсинга XML схемы границ РРР."""
    cadastral_block: Optional[str] = None
    note: Optional[str] = None
    area: Optional[float] = None
    coordinates: List[RRRCoord] = field(default_factory=list)
    has_coords: bool = False


def _extract_xml_bytes(raw: bytes) -> bytes:
    """
    Извлечь XML из raw-данных (XML/ZIP/GZ).
    """
    data = raw

    # GZIP?
    if len(data) >= 2 and data[0] == 0x1F and data[1] == 0x8B:
        data = gzip.decompress(data)

    # ZIP?
    bio = BytesIO(data)
    if zipfile.is_zipfile(bio):
        with zipfile.ZipFile(bio, "r") as zf:
            xml_names = [
                name for name in zf.namelist()
                if name.lower().endswith(".xml")
            ]
            if not xml_names:
                raise ValueError("В ZIP-архиве не найден подходящий XML файл.")
            with zf.open(xml_names[0], "r") as xf:
                return xf.read()

    return data


def _text_or_none(elem) -> Optional[str]:
    if elem is None:
        return None
    txt = "".join(elem.itertext()).strip()
    return txt or None


def parse_rrr_xml(raw: bytes) -> RRRXMLData:
    """
    Парсинг XML схемы границ РРР.

    Ожидаемая структура:
    <SchemaParcels>
      <NewParcels>
        <NewParcel>
          <CadastralBlock>42:04:0313001</CadastralBlock>
          <Area>
            <Area>370</Area>
            <Unit>055</Unit>
          </Area>
          <Entity_Spatial>
            <Spatial_Element>
              <Spelement_Unit Type_Unit="Точка">
                <NewOrdinate X="450305.73" Y="2213542.44" Num_Geopoint="1"/>
              </Spelement_Unit>
            </Spatial_Element>
          </Entity_Spatial>
        </NewParcel>
      </NewParcels>
    </SchemaParcels>

    ВАЖНО: В XML схемы:
    - X = ВОСТОК (малое значение ~450000)
    - Y = СЕВЕР (большое значение ~2213000)

    Для совместимости с ГИС слоями меняем местами:
    - x (в результате) = СЕВЕР (из Y в XML)
    - y (в результате) = ВОСТОК (из X в XML)
    """
    xml_bytes = _extract_xml_bytes(raw)

    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    root = etree.fromstring(xml_bytes, parser=parser)

    result = RRRXMLData()

    # Ищем NewParcel
    new_parcel = root.xpath("//*[local-name()='NewParcel']")
    if not new_parcel:
        return result

    parcel = new_parcel[0]

    # CadastralBlock
    cb = parcel.xpath("*[local-name()='CadastralBlock']")
    if cb:
        result.cadastral_block = _text_or_none(cb[0])

    # Note — местоположение объекта
    note_el = parcel.xpath("*[local-name()='Note']")
    if note_el:
        result.note = _text_or_none(note_el[0])

    # Area
    area_el = parcel.xpath("*[local-name()='Area']/*[local-name()='Area']")
    if area_el:
        try:
            result.area = float(_text_or_none(area_el[0]))
        except (ValueError, TypeError):
            pass

    # Coordinates
    ordinates = parcel.xpath(
        ".//*[local-name()='Entity_Spatial']"
        "//*[local-name()='Spatial_Element']"
        "//*[local-name()='Spelement_Unit']"
        "/*[local-name()='NewOrdinate']"
    )

    coords = []
    for ord_el in ordinates:
        x_xml = ord_el.get("X")  # восток
        y_xml = ord_el.get("Y")  # север
        num = ord_el.get("Num_Geopoint", str(len(coords) + 1))

        if x_xml and y_xml:
            # МЕНЯЕМ МЕСТАМИ: x=север(из Y), y=восток(из X)
            coords.append(RRRCoord(num=num, x=y_xml, y=x_xml))

    result.coordinates = coords
    result.has_coords = bool(coords)

    return result
