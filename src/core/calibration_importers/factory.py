"""Фабрика обработчиков файлов калибровки."""

from __future__ import annotations

import os
from typing import List, Optional

from .base import BaseCalibrationHandler, CalibrationPoint
from .loc_importer import LocImporter
from .cot_importer import CotImporter


class UnsupportedFormatError(Exception):
    pass


_HANDLERS: List[BaseCalibrationHandler] = [
    LocImporter(),
    CotImporter(),
]

# Wildcard для импорта
WILDCARD = (
    "Файлы калибровки (*.loc;*.cot)|*.loc;*.cot"
    "|Carlson LOC (*.loc)|*.loc"
    "|Carlson COT (*.cot)|*.cot"
    "|Все файлы (*.*)|*.*"
)

# Wildcard для экспорта — строится динамически из реестра
def export_wildcard() -> str:
    parts = []
    exts  = []
    for h in _HANDLERS:
        for ext in h.extensions:
            parts.append(f"{h.format_name} (*.{ext})|*.{ext}")
            exts.append(f"*.{ext}")
    all_exts = ";".join(exts)
    return (
        f"Все форматы калибровки ({all_exts})|{all_exts}"
        "|" + "|".join(parts)
        + "|Все файлы (*.*)|*.*"
    )


# ── Импорт ────────────────────────────────────────────────────────────────────

def load_calibration_file(filepath: str) -> List[CalibrationPoint]:
    content = _read_file(filepath)
    for h in _HANDLERS:
        if h.can_handle(filepath, content):
            points = h.parse(content)
            if not points:
                raise ValueError(
                    f"Файл распознан как «{h.format_name}», "
                    "но не содержит ни одной точки."
                )
            return points
    ext       = os.path.splitext(filepath)[1] or "(без расширения)"
    supported = ", ".join(f"*.{e}" for h in _HANDLERS for e in h.extensions)
    raise UnsupportedFormatError(
        f"Неподдерживаемый формат «{ext}».\nПоддерживаются: {supported}"
    )


# ── Экспорт ───────────────────────────────────────────────────────────────────

def get_handler_for_export(filepath: str) -> Optional[BaseCalibrationHandler]:
    """Возвращает обработчик по расширению файла. None если не найден."""
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    for h in _HANDLERS:
        if ext in h.extensions:
            return h
    return None


def save_calibration_file(filepath: str, points: List[CalibrationPoint]):
    """
    Сохраняет точки в файл. Формат определяется по расширению.
    Бросает UnsupportedFormatError если расширение не поддерживается.
    """
    handler = get_handler_for_export(filepath)
    if handler is None:
        ext       = os.path.splitext(filepath)[1] or "(без расширения)"
        supported = ", ".join(f"*.{e}" for h in _HANDLERS for e in h.extensions)
        raise UnsupportedFormatError(
            f"Неподдерживаемый формат для экспорта «{ext}».\n"
            f"Поддерживаются: {supported}"
        )

    content = handler.export(points)
    try:
        with open(filepath, "w", encoding=handler.export_encoding(), newline="\n") as f:
            f.write(content)
    except IOError as e:
        raise IOError(f"Не удалось записать файл:\n{e}") from e


# ── Чтение файла ──────────────────────────────────────────────────────────────

def _read_file(filepath: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                return fh.read()
        except UnicodeDecodeError:
            continue
    raise IOError(f"Не удалось прочитать файл (неизвестная кодировка):\n{filepath}")