"""
Утилиты pyproj: конвертация координат и описание систем координат.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pyproj import CRS, Transformer

from core.models import TransformationParams
from core.transformation import ellipsoid, base_crs, blh_to_ecef, ecef_to_blh, helmert_forward


# ── Базовые утилиты ───────────────────────────────────────────────────────────

def get_geodetic_crs(crs: CRS) -> CRS:
    return crs.geodetic_crs


def get_geocentric_crs(crs: CRS) -> CRS:
    """ECEF на том же эллипсоиде через proj=geocent."""
    ellipsoid = crs.ellipsoid
    a    = ellipsoid.semi_major_metre
    invf = ellipsoid.inverse_flattening
    proj4 = f"+proj=geocent +a={a} +rf={invf} +units=m +no_defs +type=crs"
    return CRS.from_proj4(proj4)


def projected_to_ecef(
    x: float, y: float, z: float, crs: CRS
) -> Tuple[float, float, float]:
    """Проецированные координаты → ECEF."""
    ecef = get_geocentric_crs(crs)
    t = Transformer.from_crs(crs, ecef, always_xy=True)
    return t.transform(x, y, z)


# ── Описание СК ───────────────────────────────────────────────────────────────

# Локализация имён параметров из coordinate_operation
_PARAM_RU: Dict[str, str] = {
    "Latitude of natural origin":           "Широта нач. точки",
    "Longitude of natural origin":          "Центральный меридиан",
    "Central meridian":                     "Центральный меридиан",
    "Scale factor at natural origin":       "Масштабный коэффициент",
    "False easting":                        "Смещение на восток",
    "False northing":                       "Смещение на север",
    "Latitude of projection centre":        "Широта центра",
    "Longitude of projection centre":       "Долгота центра",
    "Standard parallel":                    "Стандартная параллель",
    "Latitude of 1st standard parallel":    "1-я ст. параллель",
    "Latitude of 2nd standard parallel":    "2-я ст. параллель",
    "Azimuth of initial line":              "Азимут начальной линии",
    "Angle from Rectified to Skew Grid":    "Угол от прямоугольной к косой сетке",
    "Easting at projection centre":         "Восток центра проекции",
    "Northing at projection centre":        "Север центра проекции",
}

# Параметры proj4-словаря: ключ → (русское название, единица отображения)
_PROJ4_PARAM_RU: Dict[str, Tuple[str, str]] = {
    "lat_0":  ("Широта нач. точки",      "°"),
    "lon_0":  ("Центральный меридиан",   "°"),
    "lat_1":  ("1-я ст. параллель",      "°"),
    "lat_2":  ("2-я ст. параллель",      "°"),
    "k":      ("Масштабный коэффициент", ""),
    "k_0":    ("Масштабный коэффициент", ""),
    "x_0":    ("Смещение на восток",     "м"),
    "y_0":    ("Смещение на север",      "м"),
    "zone":   ("Зона UTM",               ""),
    "lat_ts": ("Параллель истинного масштаба", "°"),
}

_PROJ4_PROJ_RU: Dict[str, str] = {
    "tmerc":  "Поперечная Меркатора",
    "utm":    "UTM",
    "lcc":    "Коническая Ламберта (LCC)",
    "merc":   "Меркатора",
    "stere":  "Стереографическая",
    "aea":    "Равноплощадная Альберса",
    "eqc":    "Равнопромежуточная цилиндрическая",
    "cass":   "Кассини-Зольднера",
    "krovak": "Кровака",
    "poly":   "Поликоническая",
    "ortho":  "Ортографическая",
    "omerc":  "Косая Меркатора",
}

_PROJ4_UNITS_RU: Dict[str, str] = {
    "degree": "°",
    "metre": "метров",
    "meter": "метров",
    "m": "метров",
    "ft": "футов",
    "feet": "футов",
    "foot": "футов"
}


def _append_projection_params(crs: CRS, lines: List[str]) -> None:
    """
    Добавляет блок «Проекция» в lines.

    Попытка 1 — coordinate_operation (WKT-определения, EPSG).
    Попытка 2 — to_dict() / proj4 (СК, созданные из Proj4-строки).
    TOWGS84 намеренно не показывается.
    """
    # ── Попытка 1: через coordinate_operation ────────────────────────────────
    try:
        op = crs.coordinate_operation
        if op and op.params:
            lines.append(f"Проекция: {op.method_name}")
            for p in op.params:
                ru   = _PARAM_RU.get(p.name, p.name)
                unit = _PROJ4_UNITS_RU[p.unit_name] if p.unit_name not in ("unity", "1", "") else ""
                lines.append(f"  {ru}: {p.value:.10g} {unit}".rstrip())
            return
    except Exception:
        pass

    # ── Попытка 2: через proj4 dict ───────────────────────────────────────────
    try:
        d     = crs.to_dict()
        proj  = d.get("proj", "")
        label = _PROJ4_PROJ_RU.get(proj, proj.upper() if proj else "неизвестна")
        lines.append(f"Проекция: {label}")
        for key, (ru_name, unit) in _PROJ4_PARAM_RU.items():
            if key in d and d[key] is not None:
                val = d[key]
                fmt = f"{val:.10g}" if isinstance(val, float) else str(val)
                suffix = f" {_PROJ4_UNITS_RU[unit]}" if unit else ""
                lines.append(f"  {ru_name}: {fmt}{suffix}")
    except Exception:
        lines.append("  (параметры проекции недоступны)")


def describe_crs(crs: CRS) -> str:
    """
    Читаемое описание СК.
    Bound CRS (proj4 с +towgs84) прозрачно распаковывается:
    показываются параметры проекции, TOWGS84 скрыты.
    """
    lines: List[str] = []

    # Bound CRS = проецированная СК + TOWGS84-трансформация.
    # coordinate_operation Bound CRS — это и есть 7 параметров бурдана,
    # а не проекция. Поэтому для отображения всегда работаем с source_crs.
    display = crs.source_crs if crs.type_name == "Bound CRS" else crs

    lines.append(f"Название: {display.name}")
    lines.append(f"Тип: {display.type_name}")

    # Authority:code
    try:
        auth = display.to_authority() or crs.to_authority()
        if auth:
            lines.append(f"Код: {auth[0]}:{auth[1]}")
    except Exception:
        pass

    # Датум и эллипсоид — тоже от display, иначе в имени датума
    # будет "Unknown based on ... using towgs84=..."
    try:
        geodetic = display.geodetic_crs
        if geodetic:
            try:
                if geodetic.datum:
                    lines.append(f"Датум: {geodetic.datum.name}")
            except Exception:
                pass
            try:
                ell = display.ellipsoid
                if ell:
                    lines.append(f"Эллипсоид: {ell.name}")
                    if ell.semi_major_metre:
                        lines.append(f"  a = {ell.semi_major_metre:.3f} м")
                    if ell.inverse_flattening:
                        lines.append(f"  1/f = {ell.inverse_flattening:.9f}")
            except Exception:
                pass
    except Exception:
        pass

    # Параметры проекции — передаём display, не crs
    if display.is_projected:
        lines.append("")
        _append_projection_params(display, lines)

    # Область применения
    try:
        aou = display.area_of_use or crs.area_of_use
        if aou and aou.name:
            lines.append("")
            lines.append(f"Область применения: {aou.name}")
    except Exception:
        pass

    return "\n".join(lines)

def make_helmert_transformer(
    source_crs: CRS,
    target_crs: CRS,
    params: "TransformationParams",
):
    """
    Возвращает callable(x, y, h) → (x, y, h): source_crs → target_crs
    с явным 3D Гельмертом через ECEF.

    Три шага:
      1. source_crs → source geodetic  (pyproj, только проекция, без датума)
      2. BLH → ECEF → Helmert → ECEF → BLH  (наши формулы, EPSG:1033)
      3. target geodetic → target_crs  (pyproj, только проекция)

    Математически тождественно BOUNDCRS WKT2, который мы экспортируем.
    Используется вместо Transformer.from_crs(result_crs, target_crs),
    потому что PROJ не гарантирует корректное разворачивание BOUNDCRS
    в 3D-pipeline через from_crs.
    """
    import numpy as np

    ARCSEC_TO_RAD = np.pi / (180.0 * 3600.0)

    base_src = base_crs(source_crs)
    base_tgt = base_crs(target_crs)

    a_src, f_src = ellipsoid(base_src)
    a_tgt, f_tgt = ellipsoid(base_tgt)

    # Шаг 1: source → source geodetic (чистая инверсия проекции, никакого towgs84)
    tf_to_geo   = Transformer.from_crs(base_src, base_src.geodetic_crs, always_xy=True)
    # Шаг 3: target geodetic → target (чистая проекция, никакого towgs84)
    tf_from_geo = Transformer.from_crs(base_tgt.geodetic_crs, base_tgt, always_xy=True)

    raw = [
        params.dx,                        params.dy,                        params.dz,
        params.rx_sec * ARCSEC_TO_RAD,    params.ry_sec * ARCSEC_TO_RAD,    params.rz_sec * ARCSEC_TO_RAD,
        params.ds_raw,
    ]

    def _transform(xs, ys, hs):
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        hs = np.asarray(hs, float)

        # Шаг 1
        lons, lats, heights = tf_to_geo.transform(xs, ys, hs)

        # Шаг 2
        ecef_src = blh_to_ecef(np.deg2rad(lats), np.deg2rad(lons), heights, a_src, f_src)
        ecef_tgt = helmert_forward(ecef_src, *raw)
        lat_t, lon_t, h_t = ecef_to_blh(ecef_tgt[:, 0], ecef_tgt[:, 1], ecef_tgt[:, 2], a_tgt, f_tgt)

        # Шаг 3
        xp, yp, hp = tf_from_geo.transform(np.rad2deg(lon_t), np.rad2deg(lat_t), h_t)
        return xp, yp, np.asarray(hp)

    return _transform

def make_bound_crs(source_crs: CRS, params: TransformationParams) -> CRS:
    """
    Создаёт proper 3D BoundCRS в формате WKT2:
      - Source: 3D-версия исходной СК (projected или geographic)
      - Target: WGS 84 3D (EPSG:4979)
      - Transformation: Position Vector 7-param Helmert (EPSG:1033)

    to_3d() добавляет эллипсоидальную высоту как третью ось,
    после чего PROJ строит полный 3D-pipeline включая вертикальный
    компонент датумного сдвига — в отличие от 2D BoundCRS с passthrough.
    """
    base = base_crs(source_crs)

    try:
        source_3d = base.to_3d()
    except Exception:
        source_3d = base

    target_3d = CRS.from_epsg(4979)

    src_wkt = source_3d.to_wkt(version="WKT2_2019")
    tgt_wkt = target_3d.to_wkt(version="WKT2_2019")

    wkt2 = (
        'BOUNDCRS[\n'
        f'    SOURCECRS[{src_wkt}],\n'
        f'    TARGETCRS[{tgt_wkt}],\n'
        '    ABRIDGEDTRANSFORMATION["Helmert 7 parameters",\n'
        '        METHOD["Position Vector transformation (geocentric domain)",'
            'ID["EPSG",1033]],\n'
        f'        PARAMETER["X-axis translation",{params.dx:.6f},'
            'LENGTHUNIT["metre",1,ID["EPSG",9001]]],\n'
        f'        PARAMETER["Y-axis translation",{params.dy:.6f},'
            'LENGTHUNIT["metre",1,ID["EPSG",9001]]],\n'
        f'        PARAMETER["Z-axis translation",{params.dz:.6f},'
            'LENGTHUNIT["metre",1,ID["EPSG",9001]]],\n'
        f'        PARAMETER["X-axis rotation",{params.rx_sec:.8f},'
            'ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],\n'
        f'        PARAMETER["Y-axis rotation",{params.ry_sec:.8f},'
            'ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],\n'
        f'        PARAMETER["Z-axis rotation",{params.rz_sec:.8f},'
            'ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],\n'
        f'        PARAMETER["Scale difference",{params.scale_ppm:.8f},'
            'SCALEUNIT["parts per million",1e-06,ID["EPSG",9202]]]\n'
        '    ]\n'
        ']'
    )

    try:
        return CRS.from_wkt(wkt2)
    except Exception as e:
        raise RuntimeError(
            f"Не удалось создать 3D BoundCRS:\n{e}\n\nWKT2:\n{wkt2}"
        ) from e
    

def compute_metric_residuals(
    x1s, y1s, h1s,
    x2s, y2s, h2s,
    source_crs: CRS,
    target_crs: CRS,
    params: TransformationParams,
) -> list:
    """
    Невязки (dE, dN, dU) в метрах.

    Предсказанные координаты получаем через make_helmert_transformer
    (≡ result_crs → target_crs), сравниваем с фактическими (x2, y2, h2).
    """
    import numpy as np

    x1 = np.asarray(x1s, float)
    y1 = np.asarray(y1s, float)
    h1 = np.asarray(h1s, float)
    x2 = np.asarray(x2s, float)
    y2 = np.asarray(y2s, float)
    h2 = np.asarray(h2s, float)

    transform = make_helmert_transformer(source_crs, target_crs, params)
    xp, yp, hp = transform(x1, y1, h1)

    # dU всегда в метрах
    du = (hp - h2).tolist()

    base_src = base_crs(source_crs)
    base_tgt = base_crs(target_crs)

    if base_tgt.is_projected:
        # а) целевая метрическая — разности уже в метрах
        de = (xp - x2).tolist()
        dn = (yp - y2).tolist()

    elif base_src.is_projected:
        # б) целевая градусная, исходная метрическая
        # Оба набора → исходная проекция одним трансформером → метры
        tf_inv         = Transformer.from_crs(base_tgt, base_src, always_xy=True)
        xp_m, yp_m, _ = tf_inv.transform(xp, yp, hp)
        xa_m, ya_m, _ = tf_inv.transform(x2, y2, h2)
        de = (xp_m - xa_m).tolist()
        dn = (yp_m - ya_m).tolist()

    else:
        # в) обе градусные → UTM по центроиду предсказанных точек
        centroid_lon = float(np.mean(xp))
        centroid_lat = float(np.mean(yp))
        zone         = int((centroid_lon + 180) / 6) % 60 + 1
        utm_epsg     = (32700 if centroid_lat < 0 else 32600) + zone
        utm_crs      = CRS.from_epsg(utm_epsg)

        tf_utm         = Transformer.from_crs(base_tgt, utm_crs, always_xy=True)
        xp_m, yp_m, _ = tf_utm.transform(xp, yp, hp)
        xa_m, ya_m, _ = tf_utm.transform(x2, y2, h2)
        de = (xp_m - xa_m).tolist()
        dn = (yp_m - ya_m).tolist()

    return [(float(de[i]), float(dn[i]), float(du[i])) for i in range(len(x1))]


def make_inverse_helmert_transformer(
    source_crs: CRS,
    target_crs: CRS,
    params: TransformationParams,
):
    """
    Возвращает callable(x, y, h) → (x, y, h): target_crs → source_crs.

    Это обратный ход к make_helmert_transformer(), но без приближённой
    инверсии через «отрицательные параметры» на уровне GUI-представления.

    Используется для автодостраивания координат:
      - если известна только опорная точка, вычисляем исходную
      - если известна только исходная, используем прямой трансформер
    """
    import numpy as np

    ARCSEC_TO_RAD = np.pi / (180.0 * 3600.0)

    base_src = base_crs(source_crs)
    base_tgt = base_crs(target_crs)

    a_src, f_src = ellipsoid(base_src)
    a_tgt, f_tgt = ellipsoid(base_tgt)

    # target → target geodetic
    tf_to_geo = Transformer.from_crs(base_tgt, base_tgt.geodetic_crs, always_xy=True)
    # source geodetic → source
    tf_from_geo = Transformer.from_crs(base_src.geodetic_crs, base_src, always_xy=True)

    dX = params.dx
    dY = params.dy
    dZ = params.dz
    rX = params.rx_sec * ARCSEC_TO_RAD
    rY = params.ry_sec * ARCSEC_TO_RAD
    rZ = params.rz_sec * ARCSEC_TO_RAD
    dS = params.ds_raw

    M = 1.0 + dS
    T = np.array([dX, dY, dZ])

    # Та же матрица, что и в helmert_forward()
    R = np.array([
        [ 1.0,  -rZ,   rY],
        [ rZ,   1.0,  -rX],
        [-rY,    rX,  1.0],
    ])

    def _transform(xs, ys, hs):
        xs = np.asarray(xs, float)
        ys = np.asarray(ys, float)
        hs = np.asarray(hs, float)

        # target → target geodetic
        lons, lats, heights = tf_to_geo.transform(xs, ys, hs)

        # target BLH → ECEF
        ecef_tgt = blh_to_ecef(
            np.deg2rad(lats), np.deg2rad(lons), heights,
            a_tgt, f_tgt
        )

        # Обратный Гельмерт:
        # X_tgt = M * X_src @ R.T + T
        # X_src = ((X_tgt - T) / M) @ R
        ecef_src = ((ecef_tgt - T[np.newaxis, :]) / M) @ R

        # source ECEF → source BLH
        lat_s, lon_s, h_s = ecef_to_blh(
            ecef_src[:, 0], ecef_src[:, 1], ecef_src[:, 2],
            a_src, f_src
        )

        # source geodetic → source CRS
        xp, yp, hp = tf_from_geo.transform(
            np.rad2deg(lon_s), np.rad2deg(lat_s), h_s
        )
        return xp, yp, np.asarray(hp)

    return _transform