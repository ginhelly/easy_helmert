"""Фабрика импортёров файлов калибровки."""

from __future__ import annotations

import os
from typing import List

from .base import BaseCalibrationImporter, CalibrationPoint
from .loc_importer import LocImporter
from .cot_importer import CotImporter


class UnsupportedFormatError(Exception):
    """Ни один из зарегистрированных импортёров не смог обработать файл."""


# Реестр — более специфичные форматы первыми
_IMPORTERS: List[BaseCalibrationImporter] = [
    LocImporter(),
    CotImporter(),
]

# Готовый wildcard для wx.FileDialog
WILDCARD = (
    "Файлы калибровки (*.loc;*.cot)|*.loc;*.cot"
    "|Carlson LOC (*.loc)|*.loc"
    "|COT (*.cot)|*.cot"
    "|Все файлы (*.*)|*.*"
)


def load_calibration_file(filepath: str) -> List[CalibrationPoint]:
    """
    Читает файл, автоматически определяет формат, возвращает точки.

    Raises:
        IOError               — файл не удалось прочитать
        UnsupportedFormatError — формат не распознан
        ValueError            — файл распознан, но содержит ошибки
    """
    content = _read_file(filepath)

    for imp in _IMPORTERS:
        if imp.can_handle(filepath, content):
            points = imp.parse(content)
            if not points:
                raise ValueError(
                    f"Файл распознан как «{imp.format_name}», "
                    f"но не содержит ни одной точки калибровки."
                )
            return points

    ext       = os.path.splitext(filepath)[1] or "(без расширения)"
    supported = ", ".join(f"*.{e}" for i in _IMPORTERS for e in i.extensions)
    raise UnsupportedFormatError(
        f"Неподдерживаемый формат файла «{ext}».\n"
        f"Поддерживаются: {supported}"
    )


def _read_file(filepath: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
        try:
            with open(filepath, "r", encoding=enc) as fh:
                return fh.read()
        except UnicodeDecodeError:
            continue
    raise IOError(
        f"Не удалось прочитать файл (неизвестная кодировка):\n{filepath}"
    )