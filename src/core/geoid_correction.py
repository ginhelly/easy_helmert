"""
core/geoid_correction.py — расчёт 7 параметров с поправкой высот по геоиду EGM2008.

Пайплайн calculate_helmert_with_geoid():
  1. Наивный расчёт local_crs → wgs84_crs (направление гарантировано явно)
  2. Точки → WGS-84 (lon, lat): прямо если дано WGS-84, через Гельмерт если нет
  3. Считывание EGM2008 — только окно растра по bbox точек (rasterio windowed read)
  4. Ондуляции на эллипсоиде нужной СК — обратный Гельмерт local→WGS84
  5. Коррекция высот (прибавить / вычесть / ничего)
  6. Финальный расчёт с откорректированными высотами
"""
from __future__ import annotations

from enum import IntEnum
from typing import List, Optional, Tuple
from dataclasses import dataclass, field as _dc_field
import re

import numpy as np
from pyproj import CRS, Transformer

from .models import PointPair, CalculationResult, TransformationParams
from .transformation import (
    calculate_helmert,
    base_crs,
    ellipsoid,
    blh_to_ecef,
    ecef_to_blh,
)

# ── Константы WGS-84 ──────────────────────────────────────────────────────────

_WGS84_A    = 6378137.0
_WGS84_INVF = 298.257223563
_WGS84_F    = 1.0 / _WGS84_INVF

# Имя датума WGS-84: "WGS 84", "WGS84", "World Geodetic System 1984"
# Negative lookbehind (?<!\w) отсекает "towgs84" — там перед "wgs" стоит буква "o"
_WGS84_DATUM_RE = re.compile(
    r'(?<!\w)wgs\s*84(?!\w)|world\s+geodetic\s+system',
    re.IGNORECASE,
)

# ── Перечисление действий ─────────────────────────────────────────────────────

class GeoidAction(IntEnum):
    """Порядок элементов совпадает с m_rb_src_action / m_rb_tgt_action."""
    ADD      = 0   # Прибавить высоту EGM2008
    SUBTRACT = 1   # Вычесть высоту EGM2008
    NOTHING  = 2   # Ничего не делать


@dataclass
class GeoidCorrectionInfo:
    """
    Данные поправок геоида для отображения в таблице.
    Индексы совпадают с исходным списком pairs.

    src[i] / tgt[i]:
      (h_corrected, n_geoid) — высота после поправки и ондуляция, или
      None                   — высота не задана / поправка не применялась.
    """
    src: List[Optional[Tuple[float, float]]] = _dc_field(default_factory=list)
    tgt: List[Optional[Tuple[float, float]]] = _dc_field(default_factory=list)
    delta_zeta_mean: Optional[float] = None


# ── Проверка связи СК с WGS-84 ────────────────────────────────────────────────

def crs_is_wgs84_related(crs: CRS) -> bool:
    """
    True, если СК основана на датуме или эллипсоиде WGS-84.
    Проверяет сначала по имени датума, затем по параметрам эллипсоида.
    """
    try:
        geo = base_crs(crs).geodetic_crs
        try:
            dname = geo.datum.name or ""
            if _WGS84_DATUM_RE.search(dname):
                return True
        except Exception:
            pass
        ell = geo.ellipsoid
        if ell and (
            abs(ell.semi_major_metre   - _WGS84_A)    < 0.1 and
            abs(ell.inverse_flattening - _WGS84_INVF) < 0.001
        ):
            return True
    except Exception:
        pass
    return False


def geoid_controls_active(
    source_crs: Optional[CRS],
    target_crs: Optional[CRS],
) -> bool:
    """
    True, если хотя бы одна СК связана с WGS-84.
    Управляет активностью контролов геоида в UI.
    """
    return (
        (source_crs is not None and crs_is_wgs84_related(source_crs)) or
        (target_crs is not None and crs_is_wgs84_related(target_crs))
    )


def geoid_needed(src: GeoidAction, tgt: GeoidAction) -> bool:
    return src != GeoidAction.NOTHING or tgt != GeoidAction.NOTHING


# ── Поиск файла геоида ────────────────────────────────────────────────────────

def _find_geoid_path(tiff_first: bool = False) -> str:
    """
    Ищет файл геоида в resources/.
    Предпочитает egm08_25.gtx (\~30 МБ), fallback на us_nga_egm2008_1.tif (\~400 МБ).
    GTX — нативный формат PROJ, rasterio читает его через GDAL так же, как TIF.
    """
    from utils.resources import get_resource
    files = ("egm08_25.gtx", "us_nga_egm2008_1.tif")
    if tiff_first:
        files = tuple(reversed(files))
    for name in files:
        p = get_resource(name)
        if p is not None:
            return str(p)
    raise FileNotFoundError(
        "Файл геоида не найден в resources/.\n"
        "Ожидался один из:\n"
        "  egm08_25.gtx           (\~30 МБ, рекомендуется)\n"
        "  us_nga_egm2008_1.tif   (\~400 МБ)"
    )


# ── Выборка EGM2008 — оконное чтение ─────────────────────────────────────────

def _sample_egm2008(
    lons: np.ndarray,
    lats: np.ndarray,
    geoid_path: str,
) -> np.ndarray:
    """
    Билинейная интерполяция ондуляций EGM2008.

    Вместо чтения всего файла (400 МБ) читает только окно растра,
    покрывающее bbox входных точек + 2-пиксельный отступ.
    Для типичной геодезической съёмки это несколько сотен килобайт.

    Поддерживает оба формата: GTX и GeoTIFF.
    """
    try:
        import rasterio
        from rasterio.windows import from_bounds
    except ImportError:
        raise RuntimeError(
            "Библиотека rasterio не установлена.\n"
            "Установите: pip install rasterio"
        )

    with rasterio.open(geoid_path) as src:
        T      = src.transform        # аффинное преобразование растра
        nodata = src.nodata

        # BBox точек с запасом 2 пикселя для билинейной интерполяции
        pad_x = 2.0 * abs(T.a)        # шаг по долготе
        pad_y = 2.0 * abs(T.e)        # шаг по широте

        west  = float(lons.min()) - pad_x
        east  = float(lons.max()) + pad_x
        south = float(lats.min()) - pad_y
        north = float(lats.max()) + pad_y

        # Окно от географических координат
        win = from_bounds(west, south, east, north, src.transform)

        # Клип к границам растра (целочисленные смещения)
        col_off = max(0,          int(win.col_off) - 1)
        row_off = max(0,          int(win.row_off) - 1)
        col_end = min(src.width,  int(win.col_off + win.width)  + 2)
        row_end = min(src.height, int(win.row_off + win.height) + 2)

        safe_win  = rasterio.windows.Window(
            col_off, row_off,
            col_end - col_off,
            row_end - row_off,
        )
        data  = src.read(1, window=safe_win).astype(np.float64)
        win_T = src.window_transform(safe_win)   # аффин окна

    if nodata is not None:
        data = np.where(data == nodata, np.nan, data)

    nrows, ncols = data.shape

    # Некоторые файлы EGM2008 используют диапазон долгот 0–360
    lons_n = np.where(lons < 0, lons + 360.0, lons) if win_T.c >= 0 else lons.copy()

    # Дробные координаты пикселей в системе окна (0.0 = центр пикселя 0)
    cols_f = (lons_n - win_T.c) / win_T.a - 0.5
    rows_f = (lats   - win_T.f) / win_T.e - 0.5

    r0 = np.floor(rows_f).astype(int)
    c0 = np.floor(cols_f).astype(int)
    dr = rows_f - r0
    dc = cols_f - c0

    r0 = np.clip(r0,     0, nrows - 1)
    r1 = np.clip(r0 + 1, 0, nrows - 1)
    c0 = np.clip(c0,     0, ncols - 1)
    c1 = np.clip(c0 + 1, 0, ncols - 1)

    result = (
        data[r0, c0] * (1 - dc) * (1 - dr) +
        data[r0, c1] *      dc  * (1 - dr) +
        data[r1, c0] * (1 - dc) *      dr  +
        data[r1, c1] *      dc  *      dr
    )
    return np.where(np.isnan(result), 0.0, result)


# ── Определение local / WGS-84 СК ────────────────────────────────────────────

def _split_local_wgs84(source_crs: CRS, target_crs: CRS) -> Tuple[CRS, CRS]:
    """
    Возвращает (local_crs, wgs84_crs).

    Типичный случай: source — локальная, target — WGS-84.
    Нестандартный: source — WGS-84, target — локальная.
    Если обе WGS-84 или ни одна — ValueError.
    """
    tgt_is_wgs = crs_is_wgs84_related(target_crs)
    src_is_wgs = crs_is_wgs84_related(source_crs)

    if tgt_is_wgs and not src_is_wgs:
        return source_crs, target_crs   # типичный случай
    if src_is_wgs and not tgt_is_wgs:
        return target_crs, source_crs   # нестандартный (WGS-84 → local)
    if tgt_is_wgs and src_is_wgs:
        # Обе WGS-84 — ондуляции не нужно пересчитывать; local = source
        return source_crs, target_crs
    raise ValueError(
        "Ни исходная, ни опорная СК не связаны с WGS-84 — "
        "поправка по геоиду EGM2008 неприменима."
    )


# ── Наивные параметры строго local → WGS-84 ──────────────────────────────────

def _naive_local_to_wgs84(
    pairs:      List[PointPair],
    source_crs: CRS,
    target_crs: CRS,
    local_crs:  CRS,
    wgs84_crs:  CRS,
) -> TransformationParams:
    """
    Возвращает параметры Гельмерта в направлении local_crs → wgs84_crs.

    Если source уже является local (типичный случай target=WGS84):
        calculate_helmert(pairs, source_crs, target_crs) — как есть.
    Если source является WGS-84 (нестандартный случай):
        флипаем пары и вычисляем calculate_helmert(flipped, target_crs, source_crs).

    Результат гарантированно: X_wgs = M · R · X_local + T.
    Это важно для _undulation_on_ellipsoid, которая делает обратный Гельмерт.
    """
    if crs_is_wgs84_related(target_crs):
        # source = local, target = WGS-84 — стандарт
        return calculate_helmert(pairs, source_crs, target_crs).params

    # source = WGS-84, target = local → нужны параметры target → source (local → WGS-84)
    flipped = [
        p.model_copy(update={
            "x1": p.x2, "y1": p.y2, "h1": p.h2,
            "x2": p.x1, "y2": p.y1, "h2": p.h1,
        })
        for p in pairs
    ]
    return calculate_helmert(flipped, target_crs, source_crs).params


# ── WGS-84 координаты точек ───────────────────────────────────────────────────

def _wgs84_lonlat_for(
    xs:           List[float],
    ys:           List[float],
    hs:           List[float],
    given_crs:    CRS,
    local_crs:    CRS,
    wgs84_crs:    CRS,
    naive_params: TransformationParams,   # local → WGS-84
) -> Tuple[np.ndarray, np.ndarray]:
    """
    WGS-84 (lon, lat) для набора точек в given_crs.

    Если given_crs — WGS-84: прямой перевод в геодезические координаты.
    Если given_crs — local:  преобразование через наивный Гельмерт local → WGS-84.
    """
    xs_a = np.asarray(xs, float)
    ys_a = np.asarray(ys, float)
    hs_a = np.asarray(hs, float)

    if crs_is_wgs84_related(given_crs):
        # Прямой перевод в географические координаты
        b   = base_crs(given_crs)
        geo = b.geodetic_crs
        tf  = Transformer.from_crs(b, geo, always_xy=True)
        lons, lats, _ = tf.transform(xs_a, ys_a, hs_a)
    else:
        # local → WGS-84 через наивный Гельмерт
        from utils.crs_utils import make_helmert_transformer
        tf         = make_helmert_transformer(local_crs, wgs84_crs, naive_params)
        xp, yp, hp = tf(xs_a, ys_a, hs_a)
        b_wgs = base_crs(wgs84_crs)
        t2g   = Transformer.from_crs(b_wgs, b_wgs.geodetic_crs, always_xy=True)
        lons, lats, _ = t2g.transform(xp, yp, hp)

    return np.asarray(lons, float), np.asarray(lats, float)


# ── Пересчёт ондуляций на эллипсоид нужной СК ────────────────────────────────

def _undulation_on_ellipsoid(
    lons_wgs:     np.ndarray,
    lats_wgs:     np.ndarray,
    n_wgs:        np.ndarray,
    crs:          CRS,
    naive_params: TransformationParams,   # local → WGS-84
) -> np.ndarray:
    """
    Пересчитывает ондуляции EGM2008 с WGS-84 на эллипсоид CRS.

    Алгоритм:
      1. Точки (lon, lat, N_wgs) лежат на поверхности геоида в WGS-84.
      2. ECEF WGS-84: blh_to_ecef.
      3. Обратный Гельмерт (инверсия local→WGS84): X_local = R^T @ (X_wgs − T) / M.
      4. ECEF → BLH на эллипсоиде CRS: высота = ондуляция на эллипсоиде CRS.

    Если CRS связана с WGS-84 (тот же эллипсоид) — возвращает n_wgs напрямую.
    """
    if crs_is_wgs84_related(crs):
        return n_wgs.copy()

    b = base_crs(crs)
    a_crs, f_crs = ellipsoid(b)

    # Шаг 2: геоид (WGS-84 BLH) → WGS-84 ECEF
    print('--- ПРЕОБРАЗУЕМ ВЫСОТЫ ГЕОИДА ---')
    print('    BLH_WGS')
    for B, L, H in zip(lats_wgs, lons_wgs, n_wgs):
        print('    ', B, L, H)
    ecef_wgs = blh_to_ecef(
        np.deg2rad(lats_wgs), np.deg2rad(lons_wgs), n_wgs,
        _WGS84_A, _WGS84_F,
    )
    print('    ECEF_WGS', ecef_wgs)

    # Шаг 3: обратный Гельмерт (линеаризован; точность sub-мкм при геодезических углах)
    # Forward (local→WGS84): X_wgs = M · R · X_local + T
    # Inverse:               X_local = R^T · (X_wgs − T) / M
    p   = naive_params
    M   = 1.0 + p.ds_raw
    T   = np.array([p.dx, p.dy, p.dz])
    rX, rY, rZ = p.rx, p.ry, p.rz     # радианы, Position Vector (EPSG:1033)

    # Прямое (строки-векторы): x_wgs = M * x_local @ R^T + T
    # Обратное:                x_local = (x_wgs - T) / M @ R
    #
    # R для Position Vector (EPSG:1033) — та же матрица что в helmert_forward:
    R = np.array([
        [ 1.0,  -rZ,   rY],
        [ rZ,   1.0,  -rX],
        [-rY,    rX,  1.0],
    ])

    ecef_local = (1.0 / M) * (ecef_wgs - T[np.newaxis, :]) @ R
    print('    ECEF_LOCAL', ecef_local)

    # Шаг 4: ECEF → BLH на эллипсоиде CRS
    b_local, l_local, h_local = ecef_to_blh(
        ecef_local[:, 0], ecef_local[:, 1], ecef_local[:, 2],
        a_crs, f_crs,
    )
    print('    BLH_LOCAL')
    for B, L, H in zip(b_local, l_local, h_local):
        print('   ', np.rad2deg(B), np.rad2deg(L), np.rad2deg(H))
    return np.asarray(h_local, float)


# ── Применение поправки к высоте ─────────────────────────────────────────────

def _apply_geoid(
    h: Optional[float], n: float, action: GeoidAction
) -> Optional[float]:
    if h is None:
        return None
    if action == GeoidAction.ADD:
        return h + n
    if action == GeoidAction.SUBTRACT:
        return h - n
    return h


# ── Публичный API ─────────────────────────────────────────────────────────────

def calculate_helmert_with_geoid(
    pairs:            List[PointPair],
    source_crs:       CRS,
    target_crs:       CRS,
    src_action:       GeoidAction,
    tgt_action:       GeoidAction,
    apply_correction: bool = False,
) -> Tuple[CalculationResult, GeoidCorrectionInfo]:
    geoid_path = _find_geoid_path()
    local_crs, wgs84_crs = _split_local_wgs84(source_crs, target_crs)
    naive_params = _naive_local_to_wgs84(
        pairs, source_crs, target_crs, local_crs, wgs84_crs
    )

    n          = len(pairs)
    corrected  = list(pairs)
    src_display: List[Optional[Tuple[float, float]]] = [None] * n
    tgt_display: List[Optional[Tuple[float, float]]] = [None] * n
    delta_zeta_mean: Optional[float] = None

    # ── EGM2008 для исходных точек ────────────────────────────────────────────
    # Вычисляем всегда когда src_action != NOTHING (нужно для поправки и для Δζ)
    n_wgs_src = n_src = None
    lons_src  = lats_src = None
    if src_action != GeoidAction.NOTHING:
        lons_src, lats_src = _wgs84_lonlat_for(
            [p.x1        for p in pairs],
            [p.y1        for p in pairs],
            [p.h1 or 0.0 for p in pairs],
            source_crs, local_crs, wgs84_crs, naive_params,
        )
        n_wgs_src = _sample_egm2008(lons_src, lats_src, geoid_path)
        n_src     = _undulation_on_ellipsoid(
            lons_src, lats_src, n_wgs_src, source_crs, naive_params
        )

    # ── EGM2008 для опорных точек ─────────────────────────────────────────────
    # Нужно и при tgt_action != NOTHING, и при apply_correction + tgt_action==ADD
    n_wgs_tgt = n_tgt_arr = None
    if tgt_action != GeoidAction.NOTHING:
        lons_tgt, lats_tgt = _wgs84_lonlat_for(
            [p.x2        for p in pairs],
            [p.y2        for p in pairs],
            [p.h2 or 0.0 for p in pairs],
            target_crs, local_crs, wgs84_crs, naive_params,
        )
        n_wgs_tgt = _sample_egm2008(lons_tgt, lats_tgt, geoid_path)
        n_tgt_arr = _undulation_on_ellipsoid(
            lons_tgt, lats_tgt, n_wgs_tgt, target_crs, naive_params
        )

    # ── Поправка среднего расхождения Балтика ↔ EGM2008 ─────────────────────
    # Условия: флаг включён + src_action==ADD + target связан с WGS-84
    if (
        apply_correction
        and src_action == GeoidAction.ADD
        and crs_is_wgs84_related(target_crs)
        and n_wgs_src is not None
    ):
        # Шаг 0–1: геодезические высоты опорных точек
        # Если tgt_action==ADD — даны ортометрические → добавляем N_EGM_wgs
        # Иначе — уже геодезические (эллипсоидальные)
        if tgt_action == GeoidAction.ADD and n_wgs_tgt is not None:
            h_target_geo = np.array([
                (p.h2 or 0.0) + float(n_wgs_tgt[i])
                for i, p in enumerate(pairs)
            ])
        else:
            h_target_geo = np.array([p.h2 or 0.0 for p in pairs])

        h_source_cat = np.array([p.h1 or 0.0 for p in pairs])

        # Шаг 2: ζ⁰ = H_target_geodetic − H_source_catalog
        # = расстояние от эллипсоида WGS до Балтийского квазигеоида
        zeta0 = h_target_geo - h_source_cat

        # Шаг 3–4: Δζ = ζ⁰ − N_EGM_wgs
        # = расстояние от EGM2008 до Балтийского квазигеоида
        delta_zeta_arr = zeta0 - n_wgs_src

        # Шаг 5: среднее только по точкам с обеими высотами
        valid_mask = np.array([
            p.h1 is not None and p.h2 is not None
            for p in pairs
        ])
        delta_zeta_mean = (
            float(np.mean(delta_zeta_arr[valid_mask]))
            if valid_mask.any() else 0.0
        )

    # ── Применение поправки к исходным высотам ───────────────────────────────
    # Шаг 6: H_corr = H_source + ζ'(EGM на реф. эллипс.) + Δζ_mean
    if src_action != GeoidAction.NOTHING and n_src is not None:
        dz = delta_zeta_mean if delta_zeta_mean is not None else 0.0
        for i, p in enumerate(corrected):
            n_eff  = float(n_src[i]) + dz      # суммарная поправка
            h_corr = _apply_geoid(p.h1, n_eff, src_action)
            corrected[i] = corrected[i].model_copy(update={"h1": h_corr})
            if h_corr is not None:
                src_display[i] = (h_corr, n_eff)

    # ── Применение поправки к опорным высотам ────────────────────────────────
    if tgt_action != GeoidAction.NOTHING and n_tgt_arr is not None:
        for i, p in enumerate(corrected):
            n_val  = float(n_tgt_arr[i])
            h_corr = _apply_geoid(p.h2, n_val, tgt_action)
            corrected[i] = corrected[i].model_copy(update={"h2": h_corr})
            if h_corr is not None:
                tgt_display[i] = (h_corr, n_val)

    # Шаг 7: финальный расчёт по скорректированным высотам
    result     = calculate_helmert(corrected, source_crs, target_crs)
    geoid_info = GeoidCorrectionInfo(
        src             = src_display,
        tgt             = tgt_display,
        delta_zeta_mean = delta_zeta_mean,
    )
    return result, geoid_info