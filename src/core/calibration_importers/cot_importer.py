"""Импортёр COT (CSV-подобный формат геодезических контроллеров)."""

from __future__ import annotations

from typing import List

from .base import BaseCalibrationImporter, CalibrationPoint


class _C:
    """Индексы столбцов формата COT."""
    NAME      = 0
    NORTH_SRC = 1    # Север исх.  → y1
    EAST_SRC  = 2    # Восток исх. → x1
    H_SRC     = 3    # Высота исх. → h1
    NORTH_DST = 4    # Север цел.  → y2
    EAST_DST  = 5    # Восток цел. → x2
    H_DST     = 6    # Высота цел. → h2
    # 7, 8 — пропуск (HRMS, VRMS или аналоги)
    USE_PLAN  = 9    # Y/N
    USE_H     = 10   # Y/N
    # 11 — пропуск
    MIN_COLS  = 7    # минимум для валидной строки


class CotImporter(BaseCalibrationImporter):
    """
    Импортёр COT — текстовый CSV, 12 полей через запятую:

        Название, Север_исх, Восток_исх, Высота_исх,
        Север_цел, Восток_цел, Высота_цел,
        Пропуск, Пропуск,
        Использовать_план (Y/N), Использовать_высоту (Y/N),
        Пропуск
    """

    @property
    def format_name(self) -> str:
        return "COT (CSV)"

    @property
    def extensions(self) -> List[str]:
        return ["cot"]

    def can_handle(self, filepath: str, content: str) -> bool:
        if filepath.rsplit(".", 1)[-1].lower() == "cot":
            return True
        # Эвристика: ≥10 полей через запятую, поле [9] = Y или N
        for line in content.splitlines()[:8]:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 10 and parts[9].strip().upper() in ("Y", "N", "YES", "NO"):
                return True
        return False

    def parse(self, content: str) -> List[CalibrationPoint]:
        points: List[CalibrationPoint] = []

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < _C.MIN_COLS:
                continue

            name = parts[_C.NAME].strip()
            if not name:
                continue

            def get(idx: int) -> str:
                return parts[idx].strip() if idx < len(parts) else ""

            def yn(idx: int, default: bool = True) -> bool:
                v = get(idx).upper()
                if v in ("Y", "YES", "1", "TRUE"):
                    return True
                if v in ("N", "NO",  "0", "FALSE"):
                    return False
                return default

            points.append(CalibrationPoint(
                name         = name,
                y1           = get(_C.NORTH_SRC),
                x1           = get(_C.EAST_SRC),
                h1           = get(_C.H_SRC),
                y2           = get(_C.NORTH_DST),
                x2           = get(_C.EAST_DST),
                h2           = get(_C.H_DST),
                enabled_plan = yn(_C.USE_PLAN),
                enabled_h    = yn(_C.USE_H),
            ))

        return points