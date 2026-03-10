"""Базовый класс и датакласс точки калибровки."""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class CalibrationPoint:
    """Универсальная точка калибровки — результат любого импортёра."""
    name:         str
    x1:           str  = ""    # Восток исх.
    y1:           str  = ""    # Север исх.
    h1:           str  = ""    # Высота исх.
    x2:           str  = ""    # Восток цел.
    y2:           str  = ""    # Север цел.
    h2:           str  = ""    # Высота цел.
    enabled_plan: bool = True
    enabled_h:    bool = True

    def to_dict(self) -> dict:
        return {
            "name":         self.name,
            "x1":           self.x1,  "y1": self.y1,  "h1": self.h1,
            "x2":           self.x2,  "y2": self.y2,  "h2": self.h2,
            "enabled_plan": self.enabled_plan,
            "enabled_h":    self.enabled_h,
        }


class BaseCalibrationImporter(ABC):
    """Абстрактный базовый класс для всех импортёров файлов калибровки."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Человекочитаемое название формата."""

    @property
    @abstractmethod
    def extensions(self) -> List[str]:
        """Список расширений без точки, в нижнем регистре."""

    @abstractmethod
    def can_handle(self, filepath: str, content: str) -> bool:
        """
        True — этот импортёр умеет разобрать данный файл.
        Используется фабрикой для автоопределения формата.
        """

    @abstractmethod
    def parse(self, content: str) -> List[CalibrationPoint]:
        """
        Разбирает содержимое файла.
        Бросает ValueError при некорректном содержимом.
        """