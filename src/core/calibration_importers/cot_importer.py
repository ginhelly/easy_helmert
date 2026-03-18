"""Импортёр/экспортёр Carlson .cot (CSV)."""

from __future__ import annotations

from typing import List

import csv
from io import StringIO

from .base import BaseCalibrationHandler, CalibrationPoint


# Порядок 12 полей в строке COT
# 0:name 1:local_n 2:local_e 3:local_h 4:lat 5:lon 6:ellh
# 7:use_h 8:use_v 9:code 10:desc 11:?
_FIELD_COUNT = 12

_FALSE = {"0", "false", "no", "n", ""}
_TRUE  = {"1", "true", "yes", "y"}

def _norm(s: str) -> str:
    return (s or "").strip().lower()

def _is_bool_token(s: str) -> bool:
    v = _norm(s)
    return v in _FALSE or v in _TRUE

def _to_bool(s: str, default: bool = True) -> bool:
    v = _norm(s)
    if v in _FALSE:
        return False
    if v in _TRUE:
        return True
    return default

def _is_description_candidate(s: str) -> bool:
    v = (s or "").strip()
    if not v:
        return False
    if _is_bool_token(v):
        return False
    # не брать очевидные числовые коды
    try:
        float(v.replace(",", "."))
        return False
    except Exception:
        return True

class CotImporter(BaseCalibrationHandler):
    """
    Carlson Survey (.cot) — CSV, 12 полей через запятую.

    Порядок полей:
        0  name          — имя точки
        1  Local_North   → y1 (Север исходной СК)
        2  Local_East    → x1 (Восток исходной СК)
        3  Local_H       → h1
        4  Lat           → y2 (широта WGS-84)
        5  Lon           → x2 (долгота WGS-84)
        6  Ellipsoid_H   → h2
        7  Use_Horiz     → enabled_plan  (1/0)
        8  Use_Vert      → enabled_h     (1/0)
        9  Code          — не используется
        10 Description   — если не пустое, заменяет имя
        11 reserved      — не используется
    """

    @property
    def format_name(self) -> str:
        return "Carlson COT (CSV)"

    @property
    def extensions(self) -> List[str]:
        return ["cot"]

    def can_handle(self, filepath: str, content: str) -> bool:
        if filepath.rsplit(".", 1)[-1].lower() == "cot":
            return True
        # Эвристика: первая непустая строка содержит 12 полей через запятую
        for line in content.splitlines():
            line = line.strip()
            if line:
                return len(line.split(",")) == _FIELD_COUNT
        return False

    # ── Импорт ───────────────────────────────────────────────────────────────

    def parse(self, content: str) -> List[CalibrationPoint]:
        points: List[CalibrationPoint] = []

        reader = csv.reader(StringIO(content))
        for lineno, fields in enumerate(reader, 1):
            if not fields:
                continue

            # trim + pad
            fields = [f.strip() for f in fields]
            if len(fields) < 9:
                continue
            while len(fields) < _FIELD_COUNT:
                fields.append("")

            # Определяем, где флаги use_h/use_v: (7,8) или (9,10)
            if _is_bool_token(fields[9]) and _is_bool_token(fields[10]):
                idx_use_h, idx_use_v = 9, 10
            else:
                idx_use_h, idx_use_v = 7, 8

            enabled_plan = _to_bool(fields[idx_use_h], default=True)
            enabled_h    = _to_bool(fields[idx_use_v], default=True)

            # Имя: берём description только если это реально описание
            desc = fields[10]
            name = desc if _is_description_candidate(desc) else fields[0]
            if not name:
                name = f"Point {lineno}"

            points.append(CalibrationPoint(
                name         = name,
                y1           = fields[1],  # Local_North
                x1           = fields[2],  # Local_East
                h1           = fields[3],  # Local_H
                y2           = fields[4],  # Lat
                x2           = fields[5],  # Lon
                h2           = fields[6],  # Ellipsoid_H
                enabled_plan = enabled_plan,
                enabled_h    = enabled_h,
            ))

        return points

    # ── Экспорт ──────────────────────────────────────────────────────────────

    def export(self, points: List[CalibrationPoint]) -> str:
        lines = []
        for pt in points:
            fields = [
                pt.name,
                pt.y1,                              # Local_North
                pt.x1,                              # Local_East
                pt.h1,                              # Local_H
                pt.y2,                              # Lat
                pt.x2,                              # Lon
                pt.h2,                              # Ellipsoid_H
                "1" if pt.enabled_plan else "0",    # Use_Horiz
                "1" if pt.enabled_h    else "0",    # Use_Vert
                "",                                 # Code
                pt.name,                            # Description
                "",                                 # reserved
            ]
            lines.append(",".join(fields))
        return "\n".join(lines)