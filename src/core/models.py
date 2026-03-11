from __future__ import annotations

import math
from enum import IntEnum
from typing import List, Optional, Tuple

from pydantic import BaseModel, computed_field

from .constants import FACTOR_TO_PPB, FACTOR_TO_PPM, RAD_TO_ARCSEC


class HelmertMethod(IntEnum):
    POSITION_VECTOR   = 0   # EPSG:1033  (наш внутренний формат)
    COORDINATE_FRAME  = 1   # EPSG:1032  (знаки rX/rY/rZ инвертированы)


class HelmertDirection(IntEnum):
    FORWARD  = 0   # исходная → целевая (как вычислено)
    INVERSE  = 1   # целевая → исходная


class RotationUnit(IntEnum):
    ARCSEC  = 0
    RADIANS = 1


class ScaleUnit(IntEnum):
    DIMENSIONLESS = 0
    PPM           = 1
    PPB           = 2


class DisplaySettings(BaseModel):
    """Настройки отображения результата — читаются из контролов MainFrame."""
    method:         HelmertMethod    = HelmertMethod.POSITION_VECTOR
    direction:      HelmertDirection = HelmertDirection.FORWARD
    rotation_unit:  RotationUnit     = RotationUnit.ARCSEC
    scale_unit:     ScaleUnit        = ScaleUnit.PPM
    source_name:    str              = "исходная"
    target_name:    str              = "целевая"
    rms_metric_m:   float            = 0.0


class PointPair(BaseModel):
    """Пара точек исходная/целевая."""
    name:         str            = ""
    x1:           float          = 0.0   # Восток исходной СК
    y1:           float          = 0.0   # Север исходной СК
    h1:           Optional[float] = None  # Высота исходной СК
    x2:           float          = 0.0   # Восток целевой СК
    y2:           float          = 0.0   # Север целевой СК
    h2:           Optional[float] = None  # Высота целевой СК
    enabled_plan: bool           = True
    enabled_h:    bool           = True


class TransformationParams(BaseModel):
    """
    7 параметров Гельмерта в базовых единицах:
      dx/dy/dz  — метры
      rx/ry/rz  — радианы  (Position Vector, EPSG:1033)
      scale     — полный множитель (1.0 + dS)
    """
    dx:    float = 0.0
    dy:    float = 0.0
    dz:    float = 0.0
    rx:    float = 0.0
    ry:    float = 0.0
    rz:    float = 0.0
    scale: float = 1.0
    rms_error: float = 0.0

    # ── Вычисляемые поля ─────────────────────────────────────────────────────

    @computed_field
    @property
    def rx_sec(self) -> float:
        return self.rx * RAD_TO_ARCSEC

    @computed_field
    @property
    def ry_sec(self) -> float:
        return self.ry * RAD_TO_ARCSEC

    @computed_field
    @property
    def rz_sec(self) -> float:
        return self.rz * RAD_TO_ARCSEC

    @computed_field
    @property
    def ds_raw(self) -> float:
        """dS безразмерный (scale − 1)."""
        return self.scale - 1.0

    @computed_field
    @property
    def scale_ppm(self) -> float:
        return self.ds_raw * FACTOR_TO_PPM

    @computed_field
    @property
    def scale_ppb(self) -> float:
        return self.ds_raw * FACTOR_TO_PPB

    # ── Форматирование с учётом настроек отображения ─────────────────────────

    def as_display(self, s: DisplaySettings) -> "HelmertDisplay":
        """
        Возвращает параметры в единицах и конвенции, заданных DisplaySettings.
        MainFrame получает готовый объект и просто подставляет поля в строку.
        """
        dx, dy, dz = self.dx, self.dy, self.dz
        rx, ry, rz = self.rx, self.ry, self.rz
        ds         = self.ds_raw

        # 1. Метод: Position Vector → Coordinate Frame = инверсия знаков вращения
        if s.method == HelmertMethod.COORDINATE_FRAME:
            rx, ry, rz = -rx, -ry, -rz

        # 2. Направление: инверсия всех параметров
        #    Точна до O(r², dS²) — для геодезических задач погрешность < 1e-12 м
        if s.direction == HelmertDirection.INVERSE:
            dx, dy, dz = -dx, -dy, -dz
            rx, ry, rz = -rx, -ry, -rz
            ds         = -ds

        # 3. Единицы вращения
        if s.rotation_unit == RotationUnit.ARCSEC:
            rx_d, ry_d, rz_d = (rx * RAD_TO_ARCSEC,
                                 ry * RAD_TO_ARCSEC,
                                 rz * RAD_TO_ARCSEC)
            rot_label = "″"
        else:
            rx_d, ry_d, rz_d = rx, ry, rz
            rot_label = "рад"

        # 4. Единицы масштаба
        if s.scale_unit == ScaleUnit.DIMENSIONLESS:
            sc_value = 1.0 + ds
            sc_label = ""
            sc_fmt   = f"{sc_value:.10f}"
        elif s.scale_unit == ScaleUnit.PPM:
            sc_value = ds * FACTOR_TO_PPM
            sc_label = " ppm"
            sc_fmt   = f"{sc_value:+.6f}"
        else:
            sc_value = ds * FACTOR_TO_PPB
            sc_label = " ppb"
            sc_fmt   = f"{sc_value:+.4f}"

        return HelmertDisplay(
            method_label    = ("Position Vector (EPSG:1033)"
                               if s.method == HelmertMethod.POSITION_VECTOR
                               else "Coordinate Frame (EPSG:1032)"),
            direction_label = (f"{s.source_name} → {s.target_name}"
                               if s.direction == HelmertDirection.FORWARD
                               else f"{s.target_name} → {s.source_name}"),
            dx=dx, dy=dy, dz=dz,
            rx=rx_d, ry=ry_d, rz=rz_d,
            rot_label = rot_label,
            sc_fmt    = sc_fmt,
            sc_label  = sc_label,
            rms_cm    = self.rms_error * 100,
            rms_enu   = s.rms_metric_m * 100
        )


class HelmertDisplay(BaseModel):
    """Готовые к отображению строки — только для GUI, не хранить."""
    method_label:    str
    direction_label: str
    dx: float;  dy: float;  dz: float
    rx: float;  ry: float;  rz: float
    rot_label: str
    sc_fmt:    str
    sc_label:  str
    rms_cm:    float
    rms_enu:   float

    def to_text(self) -> str:
        return (
            f"  Метод:       {self.method_label}\n"
            f"  Направление: {self.direction_label}\n"
            f"\n"
            f"  dX = {self.dx:+.4f} м\n"
            f"  dY = {self.dy:+.4f} м\n"
            f"  dZ = {self.dz:+.4f} м\n"
            f"  rX = {self.rx:+.8f} {self.rot_label}\n"
            f"  rY = {self.ry:+.8f} {self.rot_label}\n"
            f"  rZ = {self.rz:+.8f} {self.rot_label}\n"
            f"  dS = {self.sc_fmt}{self.sc_label}\n"
            f"\n"
            f"  СКО (ECEF) = {self.rms_cm:.2f} см\n"
            f"  СКО_контр. (ENU) = {self.rms_enu:.4f} см"
        )


class CalculationResult(BaseModel):
    """Результат расчёта параметров Гельмерта."""
    params:    TransformationParams
    # Невязки в единицах целевой СК: (dx, dy, dh)
    residuals: List[Tuple[float, float, float]]
    residuals_enu: List[Tuple[float, float, float]]   # ENU контрольные, метры