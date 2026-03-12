"""Импортёр/экспортёр Carlson .loc (XML)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import List, Optional

from .base import BaseCalibrationHandler, CalibrationPoint


class LocImporter(BaseCalibrationHandler):
    """
    Carlson Survey (.loc) — XML-формат.

    Соответствие полей:
        Lat, Lon, Ellipsoid_Elv   → x2/y2/h2  (WGS-84)
        Local_X (North), Local_Y (East), Local_Z → x1/y1/h1 (местная)
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

    # ── Импорт ───────────────────────────────────────────────────────────────

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
            break
        return points

    def _parse_point(self, record) -> Optional[CalibrationPoint]:
        vals = {
            v.get("name", ""): v.get("value", "")
            for v in record if v.tag == "value"
        }
        name = vals.get("Description", "").strip() or record.get("id", "").strip()
        if not name:
            return None

        def yn(key: str, default: bool = True) -> bool:
            v = vals.get(key, "").strip().lower()
            if v in ("yes", "1", "true"):  return True
            if v in ("no",  "0", "false"): return False
            return default

        return CalibrationPoint(
            name         = name,
            x2           = vals.get("Lon",           ""),
            y2           = vals.get("Lat",           ""),
            h2           = vals.get("Ellipsoid_Elv", ""),
            x1           = vals.get("Local_X",       ""),
            y1           = vals.get("Local_Y",       ""),
            h1           = vals.get("Local_Z",       ""),
            enabled_plan = yn("Use_Horizontal"),
            enabled_h    = yn("Use_Vertical"),
        )

    # ── Экспорт ──────────────────────────────────────────────────────────────

    def export(self, points: List[CalibrationPoint]) -> str:
        root = ET.Element("carlson_xml")
        loc_record = ET.SubElement(root, "record", id="Localization Points")

        for i, pt in enumerate(points, 1):
            rec = ET.SubElement(loc_record, "record", id=pt.name or f"Point {i}")
            _val = lambda name, value: ET.SubElement(
                rec, "value", name=name, value=str(value)
            )
            _val("Description",    pt.name)
            _val("Lat",            pt.y2)
            _val("Lon",            pt.x2)
            _val("Ellipsoid_Elv",  pt.h2)
            _val("Local_X",        pt.x1)
            _val("Local_Y",        pt.y1)
            _val("Local_Z",        pt.h1)
            _val("Use_Horizontal", "Yes" if pt.enabled_plan else "No")
            _val("Use_Vertical",   "Yes" if pt.enabled_h    else "No")

        ET.indent(root, space="  ")
        return '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(
            root, encoding="unicode"
        )