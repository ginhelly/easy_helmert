from __future__ import annotations
from enum import IntEnum
from typing import Tuple


class DegreesParseMode(IntEnum):
    DM_TO_DD   = 0  # 52.015473 -> 52°01.5473' -> 52.02578833
    DMS_TO_DD  = 1  # 52.015473 -> 52°01'54.73'' -> 52.03186944
    DD_TO_DM   = 2  # 52.015473 -> 52°0.92838' -> 52.00928380
    DD_TO_DMS  = 3  # 52.015473 -> 52°0'55.70'' -> 52.00557000


def _to_float(s: str) -> float:
    return float(s.strip().replace(",", "."))


def _fmt8(v: float) -> str:
    return f"{v:.8f}"


def _sign(v: float) -> int:
    return -1 if v < 0 else 1


def _split_deg_abs(v: float) -> tuple[int, float]:
    av = abs(v)
    deg = int(av)
    frac = av - deg
    return deg, frac


def _decode_dm_to_dd(v: float) -> tuple[float, str]:
    sgn = _sign(v)
    deg, frac = _split_deg_abs(v)
    mm_dec = frac * 100.0
    if not (0.0 <= mm_dec < 60.0):
        raise ValueError("Минуты вне диапазона [0,60)")
    dd = sgn * (deg + mm_dec / 60.0)
    preview = f"{v} -> {deg:02d}°{mm_dec:06.4f}' ({_fmt8(dd)})"
    return dd, preview


def _decode_dms_to_dd(v: float) -> tuple[float, str]:
    sgn = _sign(v)
    deg, frac = _split_deg_abs(v)
    mmss = frac * 100.0
    mm = int(mmss)
    ss = (mmss - mm) * 100.0
    if not (0 <= mm < 60):
        raise ValueError("Минуты вне диапазона [0,60)")
    if not (0.0 <= ss < 60.0):
        raise ValueError("Секунды вне диапазона [0,60)")
    dd = sgn * (deg + mm / 60.0 + ss / 3600.0)
    preview = f"{v} -> {deg:02d}°{mm:02d}'{ss:05.2f}'' ({_fmt8(dd)})"
    return dd, preview


def _encode_dd_to_dm(v: float) -> tuple[float, str]:
    sgn = _sign(v)
    av = abs(v)
    deg = int(av)
    mm_dec = (av - deg) * 60.0
    # carry
    if mm_dec >= 60.0:
        deg += 1
        mm_dec -= 60.0
    enc = sgn * (deg + mm_dec / 100.0)
    preview = f"{_fmt8(v)} ({deg:02d}°{mm_dec:07.5f}') -> {_fmt8(enc)}"
    return enc, preview


def _encode_dd_to_dms(v: float) -> tuple[float, str]:
    sgn = _sign(v)
    av = abs(v)
    deg = int(av)
    mm_total = (av - deg) * 60.0
    mm = int(mm_total)
    ss = (mm_total - mm) * 60.0
    ss = round(ss, 2)

    # carry
    if ss >= 60.0:
        ss -= 60.0
        mm += 1
    if mm >= 60:
        mm -= 60
        deg += 1

    enc = sgn * (deg + mm / 100.0 + ss / 10000.0)
    preview = f"{_fmt8(v)} ({deg:02d}°{mm:02d}'{ss:05.2f}'') -> {_fmt8(enc)}"
    return enc, preview


def parse_value(raw: str, mode: DegreesParseMode) -> Tuple[str, str]:
    """
    returns: (new_value_8dp, preview_text)
    """
    v = _to_float(raw)
    if mode == DegreesParseMode.DM_TO_DD:
        out, preview = _decode_dm_to_dd(v)
    elif mode == DegreesParseMode.DMS_TO_DD:
        out, preview = _decode_dms_to_dd(v)
    elif mode == DegreesParseMode.DD_TO_DM:
        out, preview = _encode_dd_to_dm(v)
    else:
        out, preview = _encode_dd_to_dms(v)
    return _fmt8(out), preview