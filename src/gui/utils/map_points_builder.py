from __future__ import annotations

from typing import List, Tuple, Dict, Any

from pyproj import CRS, Transformer

from core.models import CalculationResult
from core.geoid_correction import crs_is_wgs84_related
from core.transformation import base_crs
from utils.crs_utils import make_helmert_transformer, make_inverse_helmert_transformer


def can_show_map(source_crs: CRS | None, target_crs: CRS | None) -> bool:
    if source_crs is None or target_crs is None:
        return False
    return crs_is_wgs84_related(source_crs) or crs_is_wgs84_related(target_crs)


def _to_lonlat(crs: CRS, x: float, y: float, h: float) -> tuple[float, float]:
    b = base_crs(crs)
    tf = Transformer.from_crs(b, b.geodetic_crs, always_xy=True)
    lon, lat, _ = tf.transform(x, y, h)
    return float(lon), float(lat)


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    return float(s.replace(",", "."))


def build_points_for_map(
    raw_items: List[Tuple[int, dict]],
    source_crs: CRS,
    target_crs: CRS,
    result: CalculationResult,
) -> tuple[list[dict], list[dict]]:
    """
    Возвращает:
      src_points: [{"name","lon","lat"}, ...]
      tgt_points: [{"name","lon","lat"}, ...]

    Логика:
    - если target WGS-related: target = якорь
      src переводим через solved Helmert source->target
    - если source WGS-related: source = якорь
      tgt переводим через solved Helmert target->source
    """
    src_points: list[dict] = []
    tgt_points: list[dict] = []

    tgt_is_wgs = crs_is_wgs84_related(target_crs)
    src_is_wgs = crs_is_wgs84_related(source_crs)

    if not (tgt_is_wgs or src_is_wgs):
        return src_points, tgt_points

    fwd = make_helmert_transformer(source_crs, target_crs, result.params)
    inv = make_inverse_helmert_transformer(source_crs, target_crs, result.params)

    for _, r in raw_items:
        name = (r.get("name") or "").strip() or "Без имени"

        has_src = bool(str(r.get("x1", "")).strip() and str(r.get("y1", "")).strip())
        has_tgt = bool(str(r.get("x2", "")).strip() and str(r.get("y2", "")).strip())

        # --- исходные точки ---
        if has_src:
            x1 = _f(r.get("x1")); y1 = _f(r.get("y1")); h1 = _f(r.get("h1"), 0.0)

            try:
                if src_is_wgs:
                    lon, lat = _to_lonlat(source_crs, x1, y1, h1)
                else:
                    xp, yp, hp = fwd([x1], [y1], [h1])      # source -> target
                    lon, lat = _to_lonlat(target_crs, float(xp[0]), float(yp[0]), float(hp[0]))
                src_points.append({"name": name, "lon": lon, "lat": lat})
            except Exception:
                pass

        # --- опорные точки ---
        if has_tgt:
            x2 = _f(r.get("x2")); y2 = _f(r.get("y2")); h2 = _f(r.get("h2"), 0.0)

            try:
                if tgt_is_wgs:
                    lon, lat = _to_lonlat(target_crs, x2, y2, h2)
                else:
                    xp, yp, hp = inv([x2], [y2], [h2])      # target -> source
                    lon, lat = _to_lonlat(source_crs, float(xp[0]), float(yp[0]), float(hp[0]))
                tgt_points.append({"name": name, "lon": lon, "lat": lat})
            except Exception:
                pass

    return src_points, tgt_points