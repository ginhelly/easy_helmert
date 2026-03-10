from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Tuple
import numpy as np

from .constants import RAD_TO_ARCSEC, FACTOR_TO_PPM, FACTOR_TO_PPB

class Point(BaseModel):
    """Точка в системе координат."""
    id: Optional[str] = None
    x: float
    y: float
    z: float = 0.0
    
    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

class PointPair(BaseModel):
    """Пара соответственных точек."""
    source: Point
    target: Point
    # Здесь можно хранить флаг, использовать ли точку в расчёте
    enabled: bool = True
    weight: float = 1.0  # вес точки при уравнивании

class TransformationParams(BaseModel):
    """Результат расчёта параметров (например, для 7-параметрического Гельмерта)."""
    #model_config = ConfigDict(arbitrary_types_allowed=True)
    
    # Параметры в базовых единицах
    dx: float = 0.0
    dy: float = 0.0
    dz: float = 0.0
    rx: float = 0.0  # радианы
    ry: float = 0.0  # радианы
    rz: float = 0.0  # радианы
    scale: float = 1.0  # коэффициент
    
    # Статистика
    rms_error: float = 0.0
    max_error: float = 0.0

    @computed_field
    @property
    def rx_sec(self) -> float:
        """RX в секундах."""
        return self.rx * RAD_TO_ARCSEC
    
    @computed_field
    @property
    def ry_sec(self) -> float:
        """RY в секундах."""
        return self.ry * RAD_TO_ARCSEC
    
    @computed_field
    @property
    def rz_sec(self) -> float:
        """RZ в секундах."""
        return self.rz * RAD_TO_ARCSEC
    
    @computed_field
    @property
    def scale_ppm(self) -> float:
        """Масштаб в ppm (parts per million)."""
        return (self.scale - 1.0) * FACTOR_TO_PPM
    
    @computed_field
    @property
    def scale_ppb(self) -> float:
        """Масштаб в ppb (parts per billion)."""
        return (self.scale - 1.0) * FACTOR_TO_PPB
    
    def as_display_dict(self) -> dict:
        """Для отображения в GUI с отформатированными значениями."""
        return {
            "DX (м)": f"{self.dx:.4f}",
            "DY (м)": f"{self.dy:.4f}",
            "DZ (м)": f"{self.dz:.4f}",
            "RX (сек)": f"{self.rx_sec:.4f}",
            "RY (сек)": f"{self.ry_sec:.4f}",
            "RZ (сек)": f"{self.rz_sec:.4f}",
            "Масштаб (ppm)": f"{self.scale_ppm:.3f}",
            "Масштаб (ppb)": f"{self.scale_ppb:.1f}",
            "СКО (м)": f"{self.rms_error:.4f}",
            "Макс. невязка (м)": f"{self.max_error:.4f}",
        }

class CalculationResult(BaseModel):
    """Полный результат вычисления."""
    params: TransformationParams
    transformed_points: List[Tuple[float, float, float]]  # X, Y, Z исходных, преобразованные параметрами
    residuals: List[Tuple[float, float, float]]  # Невязки по X, Y, Z