"""
utils/crs_export.py — генерация WKT1 / WKT2 / Proj4 для результирующей СК.
"""
from __future__ import annotations

import re
from pyproj import CRS

from core.models import TransformationParams


def is_wgs84_target(target_crs: CRS) -> bool:
    """True если целевая СК — WGS 84."""
    try:
        auth = target_crs.to_authority()
        if auth and auth[0].upper() == "EPSG" and auth[1] in ("4326", "4979", "4978"):
            return True
    except Exception:
        pass
    try:
        datum_name = target_crs.geodetic_crs.datum.name.lower()
        return "wgs" in datum_name and "84" in datum_name
    except Exception:
        return False


def _base(crs: CRS) -> CRS:
    """Снимает Bound CRS обёртку."""
    return crs.source_crs if crs.type_name == "Bound CRS" else crs


def _towgs84_values(params: TransformationParams) -> str:
    return (
        f"{params.dx:.6f},{params.dy:.6f},{params.dz:.6f},"
        f"{params.rx_sec:.8f},{params.ry_sec:.8f},{params.rz_sec:.8f},"
        f"{params.scale_ppm:.8f}"
    )


def _strip_epsg_suffix(name: str) -> str:
    """Убирает суффикс вида '  [EPSG:28403]' из метки диалога выбора СК."""
    idx = name.find("[EPSG:")
    if idx != -1:
        return name[:idx].strip()
    return name.strip()


def _replace_crs_name(wkt: str, display_name: str) -> str:
    """
    Заменяет имя верхнего уровня PROJCS/GEOGCS/PROJCRS/GEOGCRS в WKT
    на display_name (с очищенным суффиксом EPSG).
    """
    if not display_name:
        return wkt
    name = _strip_epsg_suffix(display_name)
    if not name:
        return wkt
    # Ищем открывающий тег верхнего уровня и заменяем имя внутри первых кавычек
    result = re.sub(
        r'^(PROJ(?:CS|CRS)|GEOG(?:CS|CRS))\["[^"]*"',
        lambda m: m.group(1) + '["' + name + '"',
        wkt,
        count=1,
    )
    return result


# ── AUTHORITY injection для WKT1 ──────────────────────────────────────────────

def _find_block_end(wkt: str, start: int) -> int:
    """Индекс закрывающего ] блока, начинающегося с [ на позиции start."""
    depth = 0
    for i in range(start, len(wkt)):
        if wkt[i] == '[':
            depth += 1
        elif wkt[i] == ']':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError(f"Незакрытый блок в позиции {start}")


def _insert_authority(wkt: str, keyword: str, name: str,
                      auth: str, code: str) -> str:
    """
    Вставляет AUTHORITY["auth","code"] в конец блока KEYWORD["name"...]
    если AUTHORITY там ещё нет.
    """
    search = keyword + '["' + name + '"'
    pos = wkt.find(search)
    if pos == -1:
        return wkt
    bracket_pos = wkt.index('[', pos)
    end_pos     = _find_block_end(wkt, bracket_pos)
    block       = wkt[bracket_pos + 1 : end_pos]
    if 'AUTHORITY' in block:
        return wkt
    authority_str = ',AUTHORITY["' + auth + '","' + code + '"]'
    return wkt[:end_pos] + authority_str + wkt[end_pos:]


# ── Справочник эллипсоидов по параметрам ─────────────────────────────────────

# (a, 1/f округлённое до 4 знаков) → EPSG-код эллипсоида
_ELLIPSOID_BY_PARAMS: list[tuple[float, float, str]] = [
    (6378245.0,   298.3,         "7024"),  # Krassowsky 1940
    (6378137.0,   298.2572236,   "7030"),  # WGS 84
    (6378137.0,   298.2572221,   "7019"),  # GRS 1980
    (6377397.155, 299.1528128,   "7004"),  # Bessel 1841
    (6378388.0,   297.0,         "7022"),  # International 1924
    (6377563.396, 299.3249646,   "7001"),  # Airy 1830
    (6378206.4,   294.9786982,   "7008"),  # Clarke 1866
    (6378249.145, 293.465,       "7012"),  # Clarke 1880 (RGS)
    (6378160.0,   298.25,        "7036"),  # GRS 1967 / Australian
    (6377276.345, 300.8017,      "7044"),  # Everest 1830
    (6378136.0,   298.2578393,   "7054"),  # PZ-90
    (6378136.5,   298.2564151,   "1025"),  # GSK-2011
    (6371000.0,   0.0,           "7035"),  # Sphere
]

_ELLIPSOID_TOL_A    = 0.01    # допуск на большую полуось, метры
_ELLIPSOID_TOL_INVF = 0.0001  # допуск на обратное сжатие


def _epsg_for_ellipsoid(a: float, inv_f: float) -> str | None:
    """
    Возвращает EPSG-код эллипсоида по значениям a и 1/f.
    None если не найдено совпадений в справочнике.
    """
    for ref_a, ref_invf, code in _ELLIPSOID_BY_PARAMS:
        if abs(a - ref_a) <= _ELLIPSOID_TOL_A and abs(inv_f - ref_invf) <= _ELLIPSOID_TOL_INVF:
            return code
    return None


def _parse_spheroid_params(block: str) -> tuple[float, float] | None:
    """
    Извлекает (a, 1/f) из строки вида SPHEROID["name",6378245,298.3,...].
    Возвращает None если не удалось распарсить.
    """
    # Ищем два числа после имени: SPHEROID["...",a,invf
    m = re.search(r'SPHEROID\["[^"]*",\s*([\d.]+)\s*,\s*([\d.]+)', block)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def _inject_spheroid_authority(wkt: str) -> str:
    """
    Заменяет или добавляет AUTHORITY в блоки SPHEROID на основе
    сравнения параметров a и 1/f — независимо от написания имени.
    """
    def replace_spheroid(m: re.Match) -> str:
        block = m.group(0)
        # Если AUTHORITY уже есть — не трогаем
        if 'AUTHORITY' in block:
            return block
        params = _parse_spheroid_params(block)
        if params is None:
            return block
        a, inv_f = params
        code = _epsg_for_ellipsoid(a, inv_f)
        if code is None:
            return block
        # Вставляем перед закрывающей ]
        return block[:-1] + ',AUTHORITY["EPSG","' + code + '"]]'

    return re.sub(r'SPHEROID\["[^"]*",[^\]]*\]', replace_spheroid, wkt)


# Справочник для не-сфероидных элементов
_KNOWN_AUTHORITIES_NON_SPHEROID = [
    ("DATUM",  "Pulkovo_1942",  "EPSG", "6284"),
    ("DATUM",  "Pulkovo 1942",  "EPSG", "6284"),
    ("DATUM",  "WGS_1984",      "EPSG", "6326"),
    ("DATUM",  "D_WGS_1984",    "EPSG", "6326"),
    ("DATUM",  "GSK_2011",      "EPSG", "1159"),
    ("PRIMEM", "Greenwich",     "EPSG", "8901"),
    ("UNIT",   "metre",         "EPSG", "9001"),
    ("UNIT",   "meter",         "EPSG", "9001"),
    ("UNIT",   "degree",        "EPSG", "9102"),
    ("UNIT",   "Degree",        "EPSG", "9102"),
]


def _inject_authorities(wkt: str) -> str:
    """Добавляет AUTHORITY-блоки: сфероиды по параметрам, остальное по имени."""
    wkt = _inject_spheroid_authority(wkt)
    for keyword, name, auth, code in _KNOWN_AUTHORITIES_NON_SPHEROID:
        wkt = _insert_authority(wkt, keyword, name, auth, code)
    return wkt


# ── Публичные функции ─────────────────────────────────────────────────────────

def to_wkt1(source_crs: CRS, params: TransformationParams,
            display_name: str = "") -> str:
    """WKT1 (GDAL) с TOWGS84, исправленным именем и AUTHORITY-блоками."""
    base = _base(source_crs)
    try:
        wkt = base.to_wkt(version="WKT1_GDAL", pretty=True)
    except Exception as e:
        raise ValueError(f"Не удалось получить WKT1 исходной СК:\n{e}") from e

    # Убираем старый TOWGS84
    wkt = re.sub(r',\s*TOWGS84\[[^\]]*\]', '', wkt)

    # Вставляем новый TOWGS84 в конец DATUM[...]
    datum_pos   = wkt.find('DATUM[')
    bracket_pos = wkt.index('[', datum_pos)
    idx         = _find_block_end(wkt, bracket_pos)
    towgs84_str = 'TOWGS84[' + _towgs84_values(params) + ']'
    wkt         = wkt[:idx] + ',\n        ' + towgs84_str + wkt[idx:]

    wkt = _replace_crs_name(wkt, display_name)
    wkt = _inject_authorities(wkt)

    return wkt


def to_wkt2(source_crs: CRS, params: TransformationParams,
            display_name: str = "",
            target_crs: CRS = None) -> str:
    """WKT2-2019 BoundCRS с исправленным именем source CRS."""
    base = _base(source_crs)
    try:
        source_3d = base.to_3d()
    except Exception:
        source_3d = base

    src_wkt = source_3d.to_wkt(version="WKT2_2019")
    src_wkt = _replace_crs_name(src_wkt, display_name)

    _tgt = target_crs if target_crs is not None else CRS.from_epsg(4979)
    try:
        tgt_3d  = _tgt.to_3d()
    except Exception:
        tgt_3d  = _tgt
    tgt_wkt = tgt_3d.to_wkt(version="WKT2_2019")
    p       = params

    lines = [
        'BOUNDCRS[',
        '    SOURCECRS[' + src_wkt + '],',
        '    TARGETCRS[' + tgt_wkt + '],',
        '    ABRIDGEDTRANSFORMATION["Helmert 7 parameters",',
        '        METHOD["Position Vector transformation (geocentric domain)",ID["EPSG",1033]],',
        '        PARAMETER["X-axis translation",'    + f'{p.dx:.6f},LENGTHUNIT["metre",1,ID["EPSG",9001]]],',
        '        PARAMETER["Y-axis translation",'    + f'{p.dy:.6f},LENGTHUNIT["metre",1,ID["EPSG",9001]]],',
        '        PARAMETER["Z-axis translation",'    + f'{p.dz:.6f},LENGTHUNIT["metre",1,ID["EPSG",9001]]],',
        '        PARAMETER["X-axis rotation",'       + f'{p.rx_sec:.8f},ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],',
        '        PARAMETER["Y-axis rotation",'       + f'{p.ry_sec:.8f},ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],',
        '        PARAMETER["Z-axis rotation",'       + f'{p.rz_sec:.8f},ANGLEUNIT["arc-second",4.84813681109536e-06,ID["EPSG",9104]]],',
        '        PARAMETER["Scale difference",'      + f'{p.scale_ppm:.8f},SCALEUNIT["parts per million",1e-06,ID["EPSG",9202]]]',
        '    ]',
        ']',
    ]
    return '\n'.join(lines)


def to_proj4(source_crs: CRS, params: TransformationParams) -> str:
    """Proj4-строка с +towgs84. Масштаб берётся из params.scale_ppm напрямую."""
    base = _base(source_crs)
    try:
        proj4 = base.to_proj4()
    except Exception as e:
        raise ValueError(f"Не удалось получить Proj4 исходной СК:\n{e}") from e

    proj4 = re.sub(r'\s*\+towgs84=\S+', '', proj4).strip()
    return proj4 + ' +towgs84=' + _towgs84_values(params)