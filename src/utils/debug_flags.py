"""
utils/debug_flags.py — временные флаги отладки, включаемые скрытым способом
из UI (5 кликов по жирному заголовку в диалоге «О программе»). Не
персистентны — сбрасываются при перезапуске приложения.
"""
from __future__ import annotations

_geoid_debug_enabled = False
_use_global_undulation_for_calc = False


def is_geoid_debug_enabled() -> bool:
    return _geoid_debug_enabled


def enable_geoid_debug() -> None:
    global _geoid_debug_enabled
    _geoid_debug_enabled = True


def is_using_global_undulation_for_calc() -> bool:
    """
    Секретный переключатель (виден только в debug-режиме геоида): если
    включён, для РЕАЛЬНОГО расчёта высот (и, соответственно, финальных
    параметров МНК) используется ондуляция, посчитанная по захардкоженным
    "глобальным" параметрам (_DEBUG_GLOBAL_NAIVE_PARAMS в geoid_correction.py),
    вместо ондуляции по naive_params основного расчёта.
    """
    return _geoid_debug_enabled and _use_global_undulation_for_calc


def set_use_global_undulation_for_calc(value: bool) -> None:
    global _use_global_undulation_for_calc
    _use_global_undulation_for_calc = value
