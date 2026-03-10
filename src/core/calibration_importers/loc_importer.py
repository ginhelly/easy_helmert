"""Импортёр Carlson .loc (XML)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import BaseCalibrationImporter, CalibrationPoint


class LocImporter(BaseCalibrationImporter):
    """
    Файл калибровки Carlson Survey (.loc) — XML-формат.

    Соответствие полей:
        Lat, Lon, Ellipsoid_Elv  → исходная СК (WGS-84 географические)
        Local_X, Local_Y, Local_Z → целевая СК (местная)

    Российская геодезическая традиция в Carlson:
        Local_X = Northing (Север)  → y2
        Local_Y = Easting  (Восток) → x2

    Use_Horizontal → enabled_plan
    Use_Vertical   → enabled_h
    Description    → name (приоритет перед «Point N»)
    """

    @property
    def format_name(self) -> str:
        return "Carlson LOC (XML)"

    @property
    def extensions(self) -> List[str]:
        return ["loc"]

    def can_handle(self, filepath: str, content: str) -> bool:
        by_ext     = filepath.rsplit(".", 1)[-1].lower() == "loc"
        by_content = "carlson_xml" in content[:512]
        return by_ext or by_content

    def parse(self, content: str) -> List[CalibrationPoint]:
        try:
            root = ET.fromstring(content)
        except ET.ParseError as exc:
            raise ValueError(f"Ошибка разбора XML: {exc}") from exc

        points: List[CalibrationPoint] = []

        for record in root.iter("record"):
            if record.get("id") != "Localization Points":
                continue
            for child in record:
                if child.tag != "record":
                    continue
                pt = self._parse_point(child)
                if pt is not None:
                    points.append(pt)
            break   # нашли нужный блок — дальше не ищем

        return points

    def _parse_point(self, record) -> Optional[CalibrationPoint]:
        vals: dict = {
            v.get("name", ""): v.get("value", "")
            for v in record
            if v.tag == "value"
        }

        name = vals.get("Description", "").strip() or record.get("id", "").strip()
        if not name:
            return None

        def yn(key: str, default: bool = True) -> bool:
            v = vals.get(key, "").strip().lower()
            if v in ("yes", "1", "true"):
                return True
            if v in ("no",  "0", "false"):
                return False
            return default

        return CalibrationPoint(
            name         = name,
            # Исходная СК: WGS-84 географические
            x2           = vals.get("Lon",           ""),   # Восток цел. = долгота
            y2           = vals.get("Lat",           ""),   # Север цел.  = широта
            h2           = vals.get("Ellipsoid_Elv", ""),   # Высота цел.
            # Целевая СК: местная система координат
            x1           = vals.get("Local_X",       ""),   # Восток исх. (правая система координат)
            y1           = vals.get("Local_Y",       ""),   # Север исх.  (правая система координат)
            h1           = vals.get("Local_Z",       ""),   # Высота исх.
            enabled_plan = yn("Use_Horizontal"),
            enabled_h    = yn("Use_Vertical"),
        )