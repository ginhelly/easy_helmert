"""
gui/utils/deviation_grid.py — сетка отклонений между двумя наборами
параметров Гельмерта для карты отклонений в MapDialog.

Для регулярной сетки точек (E_i, N_i, 0) в исходной СК:
  1. Прямое преобразование ТЕКУЩИМИ параметрами (source -> target).
  2. Обратное преобразование результата ОПОРНЫМИ параметрами (target -> source).
  3. Дельта (ΔE, ΔN, ΔU) — расхождение, вызванное разницей двух наборов
     параметров, выраженное как невязка кругового перехода.

Если в основном окне включён учёт геоида (src_action/tgt_action), оба
перехода учитывают ондуляцию EGM2008 так же, как основной расчёт: синтетическая
высота 0 на старте и на финише (мы всё время на стороне source_crs)
интерпретируется как "табличная" по src_action — конвертируется в
геодезическую перед трансформацией и обратно в табличную после. tgt_action
здесь не участвует: высота на "опорной" стороне на протяжении всего пути —
чисто промежуточная (геодезическая) величина, никогда не читается и не
пишется как табличная — в отличие от основного расчёта, где обе стороны
берутся из реальных данных пользователя.

ВАЖНО: и на старте, и на финише ондуляция выбирается ОДНИМ и тем же
naive_params — построенным из ТЕКУЩИХ параметров (как в основном расчёте,
_correct_heights_for_geoid: там на весь расчёт всегда один naive_params, а
не свой на каждую сторону). Если бы для финальной точки использовался
naive_params от ОПОРНЫХ параметров, выборка ондуляции проецировала бы точку
в WGS-84 теми же опорными параметрами, которыми эта точка только что была
получена обратным преобразованием — почти отматывая её обратно в
промежуточную целевую точку, и итоговая ondulation почти тождественно
сокращалась бы с высотой при вычитании независимо от реальной разницы
параметров (ложный «почти ноль» по ΔU).

Использует уже существующие векторизованные трансформеры из
utils/crs_utils.py и геоид-хелперы core/geoid_correction.py — никакой новой
геодезической математики.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from pyproj import CRS, Transformer

from core.geoid_correction import (
    GeoidAction,
    crs_is_wgs84_related,
    geoid_needed,
    sample_undulation,
    _split_local_wgs84,   # приватная, но переиспользуем как есть — см. docstring модуля
)
from core.models import TransformationParams
from core.transformation import base_crs
from utils.crs_utils import make_helmert_transformer, make_inverse_helmert_transformer

MIN_COLS = 10
MAX_COLS = 15
MIN_ROWS = 2
MAX_ROWS = 30


def _clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))


def _naive_params_for(params: TransformationParams, target_crs: CRS) -> TransformationParams:
    """Как в apply_helmert_with_geoid: naive_params всегда в направлении local -> WGS-84."""
    return params if crs_is_wgs84_related(target_crs) else params.inverted()


def _table_to_calc_arr(h: np.ndarray, action: GeoidAction, n_eff: np.ndarray) -> np.ndarray:
    if action == GeoidAction.ADD:
        return h + n_eff
    if action == GeoidAction.SUBTRACT:
        return h - n_eff
    return h


def _calc_to_table_arr(h: np.ndarray, action: GeoidAction, n_eff: np.ndarray) -> np.ndarray:
    if action == GeoidAction.ADD:
        return h - n_eff
    if action == GeoidAction.SUBTRACT:
        return h + n_eff
    return h


def compute_deviation_grid(
    bounds_lonlat: Tuple[float, float, float, float],   # west, south, east, north
    source_crs: CRS,
    target_crs: CRS,
    current_params: TransformationParams,
    reference_params: TransformationParams,
    src_action: GeoidAction = GeoidAction.NOTHING,
    tgt_action: GeoidAction = GeoidAction.NOTHING,
    delta_zeta_mean: Optional[float] = None,
    target_cols: int = 12,
) -> dict:
    """
    Возвращает GeoJSON FeatureCollection полигонов-ячеек. Каждая ячейка несёт
    properties {dE, dN, dU, mag} — среднее по её 4 угловым узлам (без
    интерполяции). Цветовая шкала строится на JS-стороне по фактическим
    min/max в самом geojson.

    src_action/tgt_action/delta_zeta_mean — те же настройки, что сейчас
    активны в главном окне (см. MainFrame._read_geoid_actions() и
    self._last_delta_zeta_mean); при src_action == tgt_action == NOTHING
    поведение идентично отсутствию геоид-коррекции (было до этого изменения).
    """
    west, south, east, north = bounds_lonlat

    base_src = base_crs(source_crs)
    geo_src = base_src.geodetic_crs
    to_xy = Transformer.from_crs(geo_src, base_src, always_xy=True)
    to_lonlat = Transformer.from_crs(base_src, geo_src, always_xy=True)

    corner_lons = [west, east, east, west]
    corner_lats = [south, south, north, north]
    corner_xs, corner_ys = to_xy.transform(corner_lons, corner_lats)

    e_min, e_max = float(min(corner_xs)), float(max(corner_xs))
    n_min, n_max = float(min(corner_ys)), float(max(corner_ys))

    cols = _clamp(int(target_cols), MIN_COLS, MAX_COLS)
    if e_max > e_min:
        rows = _clamp(round(cols * (n_max - n_min) / (e_max - e_min)), MIN_ROWS, MAX_ROWS)
    else:
        rows = cols

    xs = np.linspace(e_min, e_max, cols + 1)
    ys = np.linspace(n_min, n_max, rows + 1)
    grid_x, grid_y = np.meshgrid(xs, ys)   # shape (rows+1, cols+1)

    flat_x = grid_x.ravel()
    flat_y = grid_y.ravel()
    flat_h = np.zeros_like(flat_x)

    fwd     = make_helmert_transformer(source_crs, target_crs, current_params)
    inv_ref = make_inverse_helmert_transformer(source_crs, target_crs, reference_params)

    use_geoid = geoid_needed(src_action, tgt_action)

    if not use_geoid:
        h_src_start = flat_h
        xt, yt, ht = fwd(flat_x, flat_y, h_src_start)
        xs2, ys2, hs2_calc = inv_ref(xt, yt, ht)
        h_src_final = hs2_calc
    else:
        local_crs, wgs84_crs = _split_local_wgs84(source_crs, target_crs)
        dz = float(delta_zeta_mean) if delta_zeta_mean is not None else 0.0

        # ЕДИНЫЙ naive_params — от ТЕКУЩИХ параметров — используется для
        # обеих выборок ондуляции (и на старте, и на финише), точно как в
        # основном расчёте (_correct_heights_for_geoid): там на весь расчёт
        # всегда один naive_params, а не свой на каждую сторону/переход.
        #
        # Если бы для финальной точки использовался naive_reference
        # (построенный из ОПОРНЫХ параметров), выборка ондуляции там
        # проецировала бы точку в WGS-84 ТЕМИ ЖЕ опорными параметрами,
        # которыми эта точка только что была получена обратным
        # преобразованием — то есть почти отматывала бы её обратно в
        # промежуточную (целевую) точку. Из-за этого h'_calc и ондуляция
        # почти тождественно сокращались бы при вычитании независимо от
        # реальной разницы параметров — ложный «почти ноль» по высоте.
        naive_params = _naive_params_for(current_params, target_crs)

        # ── Прямой переход: текущие параметры ────────────────────────────
        n_src_start = sample_undulation(flat_x, flat_y, flat_h, source_crs, local_crs, wgs84_crs, naive_params)
        h_src_start = _table_to_calc_arr(flat_h, src_action, n_src_start + dz)

        xt, yt, ht = fwd(flat_x, flat_y, h_src_start)

        # ── Обратный переход: опорные параметры (сама трансформация),
        #    но ондуляция — тем же naive_params, что и на прямом переходе ──
        xs2, ys2, hs2_calc = inv_ref(xt, yt, ht)

        n_src_final = sample_undulation(
            np.asarray(xs2), np.asarray(ys2), np.asarray(hs2_calc),
            source_crs, local_crs, wgs84_crs, naive_params,
        )
        h_src_final = _calc_to_table_arr(np.asarray(hs2_calc), src_action, n_src_final + dz)

    d_e = np.asarray(xs2) - flat_x
    d_n = np.asarray(ys2) - flat_y
    d_u = np.asarray(h_src_final) - flat_h
    mag = np.sqrt(d_e ** 2 + d_n ** 2 + d_u ** 2)

    lons, lats = to_lonlat.transform(flat_x, flat_y)

    shape = (rows + 1, cols + 1)
    lons  = np.asarray(lons).reshape(shape)
    lats  = np.asarray(lats).reshape(shape)
    d_e   = d_e.reshape(shape)
    d_n   = d_n.reshape(shape)
    d_u   = d_u.reshape(shape)
    mag   = mag.reshape(shape)

    features = []
    for i in range(rows):
        for j in range(cols):
            idxs = [(i, j), (i, j + 1), (i + 1, j + 1), (i + 1, j)]
            ring = [[float(lons[r, c]), float(lats[r, c])] for r, c in idxs]
            ring.append(ring[0])

            cell_de  = float(np.mean([d_e[r, c] for r, c in idxs]))
            cell_dn  = float(np.mean([d_n[r, c] for r, c in idxs]))
            cell_du  = float(np.mean([d_u[r, c] for r, c in idxs]))
            cell_mag = float(np.mean([mag[r, c] for r, c in idxs]))

            features.append({
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [ring]},
                "properties": {
                    "dE": cell_de, "dN": cell_dn, "dU": cell_du, "mag": cell_mag,
                    # Готовые подписи по всем режимам — чтобы переключение
                    # режима на JS-стороне было мгновенным, без пересчёта.
                    "label_mag": f"{cell_mag:.2f} м",
                    "label_dE":  f"{cell_de:+.2f} м",
                    "label_dN":  f"{cell_dn:+.2f} м",
                    "label_dU":  f"{cell_du:+.2f} м",
                },
            })

    return {"type": "FeatureCollection", "features": features}
