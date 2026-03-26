from __future__ import annotations

import itertools
from typing import Callable, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

from .models import PointPair, CalculationResult, TransformationParams
from .transformation import calculate_helmert
from .geoid_correction import calculate_helmert_with_geoid, GeoidAction

# Сигнатура колбэка прогресса: (current_step, total_steps)
ProgressCallback = Optional[Callable[[int, int], None]]


@dataclass
class OptimizationResult:
    """
    Результат оптимизации.
    Для режима полного исключения: included_mask (список bool длины N).
    Для раздельного режима: enabled_plan_mask, enabled_h_mask (списки bool длины N).
    """
    included_mask: Optional[List[bool]] = None
    enabled_plan_mask: Optional[List[bool]] = None
    enabled_h_mask: Optional[List[bool]] = None
    params: Optional[TransformationParams] = None
    rms_error: float = float('inf')
    residuals_enu: Optional[List[Tuple[float, float, float]]] = None
    equations: int = 0


# ---------------------------------------------------------------------------
# Вспомогательные функции
# ---------------------------------------------------------------------------

def _apply_mask(
    pairs: List[PointPair],
    plan_mask: List[bool],
    h_mask: List[bool],
) -> List[PointPair]:
    return [
        p.model_copy(update={"enabled_plan": ep, "enabled_h": eh})
        for p, ep, eh in zip(pairs, plan_mask, h_mask)
    ]


def _count_equations(plan_mask: List[bool], h_mask: List[bool]) -> int:
    return sum(2 if p else 0 for p in plan_mask) + sum(1 if h else 0 for h in h_mask)


def _compute(
    pairs: List[PointPair],
    plan_mask: List[bool],
    h_mask: List[bool],
    source_crs, target_crs,
    src_action: GeoidAction,
    tgt_action: GeoidAction,
    apply_correction: bool,
) -> Optional[CalculationResult]:
    if _count_equations(plan_mask, h_mask) < 7:
        return None
    try:
        result, _ = calculate_helmert_with_geoid(
            _apply_mask(pairs, plan_mask, h_mask),
            source_crs, target_crs,
            src_action, tgt_action, apply_correction,
        )
        return result
    except Exception:
        return None


def _to_result_full(res: CalculationResult, mask: List[bool]) -> OptimizationResult:
    return OptimizationResult(
        included_mask=mask,
        params=res.params,
        rms_error=res.params.rms_error,
        residuals_enu=res.residuals_enu,
        equations=_count_equations(mask, mask),
    )


def _to_result_split(
    res: CalculationResult,
    plan_mask: List[bool],
    h_mask: List[bool],
) -> OptimizationResult:
    return OptimizationResult(
        enabled_plan_mask=plan_mask,
        enabled_h_mask=h_mask,
        params=res.params,
        rms_error=res.params.rms_error,
        residuals_enu=res.residuals_enu,
        equations=_count_equations(plan_mask, h_mask),
    )


# ---------------------------------------------------------------------------
# Полный перебор — полное исключение
# ---------------------------------------------------------------------------

def exhaustive_optimize(
    pairs: List[PointPair],
    source_crs, target_crs,
    src_action: GeoidAction,
    tgt_action: GeoidAction,
    apply_correction: bool,
    max_excluded: int = 4,
    progress_callback: ProgressCallback = None,
) -> List[OptimizationResult]:
    n = len(pairs)
    results: List[OptimizationResult] = []

    total = sum(
        len(list(itertools.combinations(range(n), k)))
        for k in range(0, max_excluded + 1)
    )
    step = 0

    for k in range(0, max_excluded + 1):
        for excluded in itertools.combinations(range(n), k):
            mask = [i not in excluded for i in range(n)]
            res = _compute(pairs, mask, mask, source_crs, target_crs,
                           src_action, tgt_action, apply_correction)
            if res is not None:
                results.append(_to_result_full(res, mask))
            step += 1
            if progress_callback:
                progress_callback(step, total)

    results.sort(key=lambda x: x.rms_error)
    return results


# ---------------------------------------------------------------------------
# Полный перебор — раздельный режим
# ---------------------------------------------------------------------------

def exhaustive_optimize_split(
    pairs: List[PointPair],
    source_crs, target_crs,
    src_action: GeoidAction,
    tgt_action: GeoidAction,
    apply_correction: bool,
    progress_callback: ProgressCallback = None,
) -> List[OptimizationResult]:
    """
    Полный перебор для раздельного режима.
    Рекомендуется только для N <= 8 (2^8 * 2^8 = 65536 итераций).
    """
    n = len(pairs)
    results: List[OptimizationResult] = []
    total_bits = 1 << n
    total = total_bits * total_bits
    step = 0

    for plan_bits in range(total_bits):
        plan_mask = [(plan_bits >> i) & 1 == 1 for i in range(n)]
        if sum(plan_mask) < 3:
            # Пропускаем целый блок h_bits, но считаем шаги
            step += total_bits
            if progress_callback:
                progress_callback(min(step, total), total)
            continue
        for h_bits in range(total_bits):
            h_mask = [(h_bits >> i) & 1 == 1 for i in range(n)]
            if sum(h_mask) >= 1:
                res = _compute(pairs, plan_mask, h_mask, source_crs, target_crs,
                               src_action, tgt_action, apply_correction)
                if res is not None:
                    results.append(_to_result_split(res, plan_mask, h_mask))
            step += 1
            if progress_callback:
                progress_callback(step, total)

    results.sort(key=lambda x: x.rms_error)
    return results


# ---------------------------------------------------------------------------
# Жадный алгоритм — полное исключение
# ---------------------------------------------------------------------------

def greedy_optimize(
    pairs: List[PointPair],
    source_crs, target_crs,
    src_action: GeoidAction,
    tgt_action: GeoidAction,
    apply_correction: bool,
    max_excluded: int = 4,
    progress_callback: ProgressCallback = None,
) -> List[OptimizationResult]:
    """
    На каждом шаге пробуем исключить каждую из оставшихся точек,
    берём ту, что даёт минимальный RMSE. Останавливаемся, если
    RMSE не улучшается или достигнут max_excluded.
    """
    n = len(pairs)
    mask = [True] * n
    results: List[OptimizationResult] = []

    # Верхняя оценка числа вызовов _compute
    total = 1 + sum(max(n - k, 0) for k in range(max_excluded))
    step = 0

    res = _compute(pairs, mask, mask, source_crs, target_crs,
                   src_action, tgt_action, apply_correction)
    step += 1
    if progress_callback:
        progress_callback(step, total)
    if res is None:
        return []

    current_rms = res.params.rms_error
    results.append(_to_result_full(res, mask[:]))

    for _ in range(max_excluded):
        candidates = [i for i, inc in enumerate(mask) if inc]
        best_rms = current_rms
        best_mask = None
        best_res = None

        for i in candidates:
            trial = mask[:]
            trial[i] = False
            res = _compute(pairs, trial, trial, source_crs, target_crs,
                           src_action, tgt_action, apply_correction)
            step += 1
            if progress_callback:
                progress_callback(step, total)
            if res is not None and res.params.rms_error < best_rms:
                best_rms = res.params.rms_error
                best_mask = trial
                best_res = res

        if best_mask is None:
            break

        mask = best_mask
        current_rms = best_rms
        results.append(_to_result_full(best_res, mask[:]))

    results.sort(key=lambda x: x.rms_error)
    return results


# ---------------------------------------------------------------------------
# Жадный алгоритм — раздельный режим
# ---------------------------------------------------------------------------

def greedy_optimize_split(
    pairs: List[PointPair],
    source_crs, target_crs,
    src_action: GeoidAction,
    tgt_action: GeoidAction,
    apply_correction: bool,
    max_excluded: int = 4,
    progress_callback: ProgressCallback = None,
) -> List[OptimizationResult]:
    """
    На каждом шаге для каждой точки проверяем три варианта:
      - выключить только план
      - выключить только высоту
      - выключить оба
    Берём вариант с минимальным RMSE.
    """
    n = len(pairs)
    plan_mask = [True] * n
    h_mask = [True] * n
    results: List[OptimizationResult] = []

    # Верхняя оценка: базовый + max_excluded шагов по 3n вариантам
    total = 1 + max_excluded * 3 * n
    step = 0

    res = _compute(pairs, plan_mask, h_mask, source_crs, target_crs,
                   src_action, tgt_action, apply_correction)
    step += 1
    if progress_callback:
        progress_callback(step, total)
    if res is None:
        return []

    current_rms = res.params.rms_error
    results.append(_to_result_split(res, plan_mask[:], h_mask[:]))

    for _ in range(max_excluded):
        best_rms = current_rms
        best_plan = None
        best_h = None
        best_res = None

        for i in range(n):
            variants = []

            if plan_mask[i]:
                tp = plan_mask[:]
                tp[i] = False
                if sum(tp) >= 3:
                    variants.append((tp, h_mask[:]))

            if h_mask[i]:
                th = h_mask[:]
                th[i] = False
                if sum(th) >= 1:
                    variants.append((plan_mask[:], th))

            if plan_mask[i] and h_mask[i]:
                tp = plan_mask[:]
                th = h_mask[:]
                tp[i] = False
                th[i] = False
                if sum(tp) >= 3 and sum(th) >= 1:
                    variants.append((tp, th))

            for tp, th in variants:
                res = _compute(pairs, tp, th, source_crs, target_crs,
                               src_action, tgt_action, apply_correction)
                step += 1
                if progress_callback:
                    progress_callback(step, total)
                if res is not None and res.params.rms_error < best_rms:
                    best_rms = res.params.rms_error
                    best_plan = tp
                    best_h = th
                    best_res = res

        if best_plan is None:
            break

        plan_mask = best_plan
        h_mask = best_h
        current_rms = best_rms
        results.append(_to_result_split(best_res, plan_mask[:], h_mask[:]))

    results.sort(key=lambda x: x.rms_error)
    return results


# ---------------------------------------------------------------------------
# Высокоуровневая функция
# ---------------------------------------------------------------------------

def optimize_combinations(
    pairs: List[PointPair],
    source_crs, target_crs,
    split_mode: bool = False,
    src_action: GeoidAction = GeoidAction.NOTHING,
    tgt_action: GeoidAction = GeoidAction.NOTHING,
    apply_correction: bool = False,
    method: str = 'auto',
    max_excluded: int = 4,
    progress_callback: ProgressCallback = None,
) -> List[OptimizationResult]:
    """
    Главная функция оптимизации. Возвращает список результатов,
    отсортированных по RMSE (лучший — первый).

    method:
        'auto'       — exhaustive при N <= 8, иначе greedy
        'exhaustive' — полный перебор (только для малых N)
        'greedy'     — жадный алгоритм
    """
    n = len(pairs)
    cb = progress_callback

    if split_mode:
        if method == 'auto':
            use_exhaustive = n <= 8
        elif method == 'exhaustive':
            use_exhaustive = True
        elif method == 'greedy':
            use_exhaustive = False
        else:
            raise ValueError(f"Unknown method: {method}")

        if use_exhaustive:
            return exhaustive_optimize_split(
                pairs, source_crs, target_crs, src_action, tgt_action,
                apply_correction, progress_callback=cb,
            )
        else:
            return greedy_optimize_split(
                pairs, source_crs, target_crs, src_action, tgt_action,
                apply_correction, max_excluded, progress_callback=cb,
            )
    else:
        if method == 'auto':
            use_exhaustive = n <= 8
        elif method == 'exhaustive':
            use_exhaustive = True
        elif method == 'greedy':
            use_exhaustive = False
        else:
            raise ValueError(f"Unknown method: {method}")

        if use_exhaustive:
            return exhaustive_optimize(
                pairs, source_crs, target_crs, src_action, tgt_action,
                apply_correction, max_excluded, progress_callback=cb,
            )
        else:
            return greedy_optimize(
                pairs, source_crs, target_crs, src_action, tgt_action,
                apply_correction, max_excluded, progress_callback=cb,
            )
