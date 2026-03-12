"""Импортёр/экспортёр Carlson .cot (CSV)."""

from __future__ import annotations

from typing import List

from .base import BaseCalibrationHandler, CalibrationPoint


# Порядок 12 полей в строке COT
# 0:name 1:local_n 2:local_e 3:local_h 4:lat 5:lon 6:ellh
# 7:use_h 8:use_v 9:code 10:desc 11:?
_FIELD_COUNT = 12


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
        for lineno, line in enumerate(content.splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            fields = line.split(",")
            if len(fields) < 9:
                continue
            # Дополняем до 12 если строка короче
            while len(fields) < _FIELD_COUNT:
                fields.append("")

            name = fields[10].strip() or fields[0].strip()
            if not name:
                name = f"Point {lineno}"

            points.append(CalibrationPoint(
                name         = name,
                y1           = fields[1].strip(),
                x1           = fields[2].strip(),
                h1           = fields[3].strip(),
                y2           = fields[4].strip(),
                x2           = fields[5].strip(),
                h2           = fields[6].strip(),
                enabled_plan = fields[7].strip() not in ("0", "false", "no", ""),
                enabled_h    = fields[8].strip() not in ("0", "false", "no", ""),
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