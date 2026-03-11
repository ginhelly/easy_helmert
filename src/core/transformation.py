"""
core/transformation.py — расчёт 7 параметров Гельмерта.

Пайплайн:
  1. Проецированные → геодезические через pyproj
  2. BLH → ECEF по стандартным формулам
  3. МНК с весами в локальной ENU: план / высота независимо
  4. Невязки в единицах целевой проекции
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import least_squares
from typing import List, Tuple

from pyproj import CRS, Transformer

from .models import CalculationResult, PointPair, TransformationParams
from utils.crs_utils import base_crs


# ── Эллипсоид ─────────────────────────────────────────────────────────────────

def _ellipsoid(crs: CRS) -> Tuple[float, float]:
    ell   = crs.geodetic_crs.ellipsoid
    a     = ell.semi_major_metre
    inv_f = ell.inverse_flattening
    f     = (1.0 / inv_f) if inv_f else 0.0
    return a, f


# ── BLH ↔ ECEF ────────────────────────────────────────────────────────────────

def _blh_to_ecef(lat: np.ndarray, lon: np.ndarray, h: np.ndarray,
                 a: float, f: float) -> np.ndarray:
    e2      = 2 * f - f ** 2
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    N       = a / np.sqrt(1.0 - e2 * sin_lat ** 2)
    X = (N + h) * cos_lat * np.cos(lon)
    Y = (N + h) * cos_lat * np.sin(lon)
    Z = (N * (1.0 - e2) + h) * sin_lat
    return np.column_stack([X, Y, Z])


def _ecef_to_blh(X: np.ndarray, Y: np.ndarray, Z: np.ndarray,
                 a: float, f: float) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    e2  = 2 * f - f ** 2
    p   = np.sqrt(X ** 2 + Y ** 2)
    lon = np.arctan2(Y, X)
    lat = np.arctan2(Z, p * (1.0 - e2))
    for _ in range(10):
        sin_lat = np.sin(lat)
        N       = a / np.sqrt(1.0 - e2 * sin_lat ** 2)
        lat_new = np.arctan2(Z + e2 * N * sin_lat, p)
        if np.all(np.abs(lat_new - lat) < 1e-14):
            break
        lat = lat_new
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    N = a / np.sqrt(1.0 - e2 * sin_lat ** 2)
    h = np.where(
        np.abs(cos_lat) > 1e-10,
        p / cos_lat - N,
        np.abs(Z) / np.abs(sin_lat) - N * (1.0 - e2),
    )
    return lat, lon, h


# ── Локальная система ENU ─────────────────────────────────────────────────────

def _enu_matrices(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """
    Матрицы поворота ECEF → ENU для каждой точки.
    Возвращает (N, 3, 3): R[i] @ v_ecef = v_enu.
    Строки матрицы: East, North, Up.
    """
    sl, cl = np.sin(lat), np.cos(lat)
    sp, cp = np.sin(lon), np.cos(lon)
    N = len(lat)
    R = np.zeros((N, 3, 3))
    # East
    R[:, 0, 0] = -sp
    R[:, 0, 1] =  cp
    R[:, 0, 2] =  0.0
    # North
    R[:, 1, 0] = -sl * cp
    R[:, 1, 1] = -sl * sp
    R[:, 1, 2] =  cl
    # Up
    R[:, 2, 0] =  cl * cp
    R[:, 2, 1] =  cl * sp
    R[:, 2, 2] =  sl
    return R


# ── Гельмерт (Position Vector, EPSG:1033) ─────────────────────────────────────

def _helmert_forward(pts: np.ndarray,
                     dX: float, dY: float, dZ: float,
                     rX: float, rY: float, rZ: float,
                     dS: float) -> np.ndarray:
    M = 1.0 + dS
    R = np.array([[  1, -rZ, +rY],
                  [+rZ,   1, -rX],
                  [-rY, +rX,   1]])
    return M * (pts @ R.T) + np.array([dX, dY, dZ])


# ── МНК ───────────────────────────────────────────────────────────────────────

def _linear_initial(src: np.ndarray, tgt: np.ndarray,
                    enu_w: np.ndarray) -> np.ndarray:
    """
    Линеаризованное МНК — стартовая точка для LM.
    Точки с нулевым суммарным весом исключаются.
    """
    total_w = enu_w.sum(axis=1)           # (N,)
    mask    = total_w > 0
    s, t    = src[mask], tgt[mask]

    N = s.shape[0]
    b = (t - s).ravel()
    A = np.zeros((3 * N, 7))
    for i in range(N):
        Xs, Ys, Zs = s[i]
        r = 3 * i
        A[r]     = [1, 0, 0,    0, +Zs, -Ys, Xs]
        A[r + 1] = [0, 1, 0, -Zs,   0, +Xs, Ys]
        A[r + 2] = [0, 0, 1, +Ys, -Xs,   0, Zs]
    p, *_ = np.linalg.lstsq(A, b, rcond=None)
    return p


def _fit(src_ecef: np.ndarray,
         tgt_ecef: np.ndarray,
         enu_w:    np.ndarray) -> np.ndarray:
    """
    Нелинейный МНК (LM) с взвешиванием в локальной ENU.

    enu_w : (N, 3) — веса для [E, N, U] каждой точки:
      - plan-only  (enabled_h=False)    → [1, 1, 0]
      - height-only (enabled_plan=False) → [0, 0, 1]
      - both                             → [1, 1, 1]

    Невязка вычисляется в ENU, умножается на веса и возвращается
    обратно в ECEF — так оптимизатор работает в метрах по всем осям.
    """
    # Матрицы поворота считаем один раз по исходным ECEF
    lat, lon, _ = _ecef_to_blh(
        src_ecef[:, 0], src_ecef[:, 1], src_ecef[:, 2],
        *_ellipsoid_from_ecef_approx(src_ecef)
    )
    R  = _enu_matrices(lat, lon)   # (N,3,3): ECEF→ENU
    Rt = R.transpose(0, 2, 1)     # (N,3,3): ENU→ECEF

    p0 = _linear_initial(src_ecef, tgt_ecef, enu_w)

    def fun(p):
        pred    = _helmert_forward(src_ecef, *p)          # (N,3) ECEF
        d_ecef  = pred - tgt_ecef                         # (N,3)
        d_enu   = np.einsum('nij,nj->ni', R,  d_ecef)    # (N,3) ENU
        d_w     = d_enu * enu_w                           # взвешиваем
        d_back  = np.einsum('nij,nj->ni', Rt, d_w)       # обратно в ECEF
        return d_back.ravel()

    return least_squares(fun, p0, method='lm').x


def _ellipsoid_from_ecef_approx(ecef: np.ndarray) -> Tuple[float, float]:
    """Приближённые параметры эллипсоида WGS84 для вычисления ENU-матриц."""
    return 6378137.0, 1 / 298.257223563


# ── Точки → ECEF ──────────────────────────────────────────────────────────────

def _to_ecef(pairs: List[PointPair], source: bool, crs: CRS) -> np.ndarray:
    base = base_crs(crs)
    geo  = base.geodetic_crs
    tf   = Transformer.from_crs(base, geo, always_xy=True)
    a, f = _ellipsoid(base)

    xs = np.array([p.x1 if source else p.x2 for p in pairs])
    ys = np.array([p.y1 if source else p.y2 for p in pairs])
    hs = np.array([(p.h1 or 0.0) if source else (p.h2 or 0.0) for p in pairs])

    lons, lats, hs_geo = tf.transform(xs, ys, hs)
    return _blh_to_ecef(np.deg2rad(lats), np.deg2rad(lons), hs_geo, a, f)


# ── Невязки ────────────────────────────────────────────────────────────────────

def _residuals(
    pairs:      List[PointPair],
    src_ecef:   np.ndarray,
    raw:        np.ndarray,
    target_crs: CRS,
) -> List[Tuple[float, float, float]]:
    base = base_crs(target_crs)
    geo  = base.geodetic_crs
    tf   = Transformer.from_crs(geo, base, always_xy=True)
    a, f = _ellipsoid(base)

    pred              = _helmert_forward(src_ecef, *raw)
    lat_r, lon_r, h_p = _ecef_to_blh(pred[:, 0], pred[:, 1], pred[:, 2], a, f)
    x_pred, y_pred    = tf.transform(np.rad2deg(lon_r), np.rad2deg(lat_r))

    return [
        (
            float(x_pred[i] - p.x2),
            float(y_pred[i] - p.y2),
            float(h_p[i]    - (p.h2 or 0.0)),
        )
        for i, p in enumerate(pairs)
    ]


# ── Публичный API ──────────────────────────────────────────────────────────────

def calculate_helmert(
    pairs:      List[PointPair],
    source_crs: CRS,
    target_crs: CRS,
) -> CalculationResult:
    """
    pairs — все точки с заполненными координатами, включая полностью отключённые.
    Полностью отключённые (enu_w=[0,0,0]) не влияют на решение,
    но получают невязки постфактум.
    """
    # Проверяем решаемость только по активным точкам
    n_equations = sum(
        (2 if p.enabled_plan else 0) + (1 if p.enabled_h else 0)
        for p in pairs
    )
    if n_equations < 7:
        n_plan = sum(1 for p in pairs if p.enabled_plan)
        n_h    = sum(1 for p in pairs if p.enabled_h)
        raise ValueError(
            f"Недостаточно данных для решения системы:\n"
            f"  плановых точек: {n_plan}  (дают {n_plan*2} уравнений)\n"
            f"  высотных точек: {n_h}  (дают {n_h} уравнений)\n"
            f"  итого: {n_equations} из 7 необходимых\n\n"
            f"Варианты минимального набора:\n"
            f"  • 3 полных точки (план + высота)\n"
            f"  • 4 плановых точки (без высот)\n"
            f"  • 3 плановых + 1 высотная"
        )

    src_ecef = _to_ecef(pairs, source=True,  crs=source_crs)
    tgt_ecef = _to_ecef(pairs, source=False, crs=target_crs)

    # Полностью отключённые → [0,0,0]: не входят в оптимизацию
    enu_w = np.array([
        [
            1.0 if p.enabled_plan else 0.0,
            1.0 if p.enabled_plan else 0.0,
            1.0 if p.enabled_h    else 0.0,
        ]
        for p in pairs
    ])

    raw = _fit(src_ecef, tgt_ecef, enu_w)
    dX, dY, dZ, rX, rY, rZ, dS = raw

    # RMSE считаем только по активным точкам
    active_mask = enu_w.sum(axis=1) > 0
    pred_ecef   = _helmert_forward(src_ecef, *raw)
    ecef_rmse   = float(np.sqrt(
        np.mean((pred_ecef[active_mask] - tgt_ecef[active_mask]) ** 2)
    ))

    params = TransformationParams(
        dx=float(dX), dy=float(dY), dz=float(dZ),
        rx=float(rX), ry=float(rY), rz=float(rZ),
        scale=float(1.0 + dS),
        rms_error=ecef_rmse,
    )

    # _residuals считает для ВСЕХ переданных точек, включая отключённые
    return CalculationResult(
        params=params,
        residuals=_residuals(pairs, src_ecef, raw, target_crs),
    )