"""
Утилиты pyproj: конвертация координат и описание систем координат.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from pyproj import CRS, Transformer


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