from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, computed_field

from .constants import FACTOR_TO_PPB, FACTOR_TO_PPM, RAD_TO_ARCSEC


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
    """7 параметров преобразования Гельмерта + статистика."""
    dx:    float = 0.0   # м
    dy:    float = 0.0   # м
    dz:    float = 0.0   # м
    rx:    float = 0.0   # рад
    ry:    float = 0.0   # рад
    rz:    float = 0.0   # рад
    # Полный масштабный множитель: 1.0 = нет масштаба, 1 + 2.4e-6 = 2.4 ppm
    scale: float = 1.0

    rms_error: float = 0.0   # СКО в ECEF, метры

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
        """dS безразмерный (scale − 1), используется в helmert_forward."""
        return self.scale - 1.0

    @computed_field
    @property
    def scale_ppm(self) -> float:
        return self.ds_raw * FACTOR_TO_PPM

    @computed_field
    @property
    def scale_ppb(self) -> float:
        return self.ds_raw * FACTOR_TO_PPB


class CalculationResult(BaseModel):
    """Результат расчёта параметров Гельмерта."""
    params:    TransformationParams
    # Невязки в единицах целевой СК: (dx, dy, dh)
    residuals: List[Tuple[float, float, float]]