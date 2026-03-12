"""Базовый класс и датакласс точки калибровки."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class CalibrationPoint:
    """Универсальная точка калибровки."""
    name:         str
    x1:           str  = ""
    y1:           str  = ""
    h1:           str  = ""
    x2:           str  = ""
    y2:           str  = ""
    h2:           str  = ""
    enabled_plan: bool = True
    enabled_h:    bool = True

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "x1": self.x1, "y1": self.y1, "h1": self.h1,
            "x2": self.x2, "y2": self.y2, "h2": self.h2,
            "enabled_plan": self.enabled_plan,
            "enabled_h":    self.enabled_h,
        }


class BaseCalibrationHandler(ABC):
    """
    Абстрактный базовый класс: один объект отвечает и за импорт, и за экспорт.
    Переименован из BaseCalibrationImporter — старое имя оставлено как алиас.
    """

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Человекочитаемое название формата."""

    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        """Список расширений без точки, нижний регистр."""

    @property
    def default_extension(self) -> str:
        """Расширение по умолчанию для сохранения."""
        return self.extensions[0]

    @abstractmethod
    def can_handle(self, filepath: str, content: str) -> bool:
        """True — этот обработчик умеет разобрать данный файл."""

    @abstractmethod
    def parse(self, content: str) -> List[CalibrationPoint]:
        """
        Импорт: разбирает содержимое файла → список точек.
        Бросает ValueError при некорректном содержимом.
        """

    @abstractmethod
    def export(self, points: List[CalibrationPoint]) -> str:
        """
        Экспорт: список точек → строка для записи в файл.
        Бросает ValueError если точки не содержат нужных полей.
        """

    def export_encoding(self) -> str:
        """Кодировка для записи файла. Переопределить при необходимости."""
        return "utf-8"


# Обратная совместимость
BaseCalibrationImporter = BaseCalibrationHandler