from __future__ import annotations

from typing import Callable, Optional, Tuple, List
from dataclasses import dataclass

import wx

from core.models import PointPair, CalculationResult


@dataclass
class CalculationRunResult:
    result: CalculationResult
    pairs: list[PointPair]
    all_residuals: list
    all_metric: list


class CalculationService:
    """
    Сервис расчёта 7-параметрового преобразования.
    UI-контролы не трогает напрямую — всё через callback'и.
    """

    def __init__(
        self,
        parent: wx.Window,
        coord_grid,
        get_source_crs: Callable[[], object],
        get_target_crs: Callable[[], object],
        read_geoid_actions: Callable[[], Tuple[object, object]],
        is_geoid_correction_enabled: Callable[[], bool],
        set_delta_zeta_mean: Callable[[Optional[float]], None],
        update_results_view: Callable[[CalculationResult], None],
        get_threshold_m: Callable[[], float],
        autofill_missing_coordinates: Callable[[list, CalculationResult, object], int],
        mark_modified: Callable[[str], None],
    ):
        self.parent = parent
        self.coord_grid = coord_grid
        self.get_source_crs = get_source_crs
        self.get_target_crs = get_target_crs
        self.read_geoid_actions = read_geoid_actions
        self.is_geoid_correction_enabled = is_geoid_correction_enabled
        self.set_delta_zeta_mean = set_delta_zeta_mean
        self.update_results_view = update_results_view
        self.get_threshold_m = get_threshold_m
        self.autofill_missing_coordinates = autofill_missing_coordinates
        self.mark_modified = mark_modified

        # state, который раньше жил в MainFrame
        self.last_all_residuals = []
        self.last_all_metric = []

    def _is_row_usable_for_calculation(self, row: int, r: dict) -> bool:
        has_both_xy = (
            bool(str(r.get("x1", "")).strip()) and
            bool(str(r.get("y1", "")).strip()) and
            bool(str(r.get("x2", "")).strip()) and
            bool(str(r.get("y2", "")).strip())
        )
        not_computed = not self.coord_grid.row_has_computed_coordinates(row)
        return has_both_xy and not_computed

    def run(self) -> Optional[CalculationRunResult]:
        geoid_info = None

        # перед расчётом очищаем автодостройку
        self.coord_grid.clear_autofilled_coordinates()

        raw_items = self.coord_grid.get_data_with_row_indices()
        valid_items = [
            (row, r)
            for row, r in raw_items
            if self._is_row_usable_for_calculation(row, r)
        ]
        valid_raw = [r for _, r in valid_items]

        n_eq = sum(
            (2 if r["enabled_plan"] else 0) + (1 if r["enabled_h"] else 0)
            for r in valid_raw
        )

        if n_eq < 7:
            wx.MessageBox(
                "Недостаточно данных.\n\n"
                "Минимальные варианты:\n"
                "  • 3 точки с планом и высотой\n"
                "  • 4 точки только с планом\n"
                "  • 3 плановых + 1 высотная\n\n"
                f"Сейчас доступно уравнений: {n_eq} из 7.",
                "Недостаточно данных",
                wx.OK | wx.ICON_WARNING,
                self.parent,
            )
            return None

        source_crs = self.get_source_crs()
        target_crs = self.get_target_crs()

        if not source_crs:
            wx.MessageBox("Задайте исходную систему координат.", "Нет исходной СК", wx.OK | wx.ICON_WARNING, self.parent)
            return None

        if not target_crs:
            wx.MessageBox("Задайте целевую систему координат.", "Нет целевой СК", wx.OK | wx.ICON_WARNING, self.parent)
            return None

        if n_eq < 12:
            if wx.MessageBox(
                f"Доступно уравнений: {n_eq} (рекомендуется ≥ 12).\n"
                "Невязки по активным точкам будут близки к нулю.\n\n"
                "Продолжить?",
                "Мало данных",
                wx.YES_NO | wx.ICON_QUESTION,
                self.parent,
            ) != wx.YES:
                return None

        try:
            pairs = [
                PointPair(
                    name=r["name"],
                    x1=float(r["x1"]),
                    y1=float(r["y1"]),
                    h1=float(r["h1"]) if r.get("h1") else None,
                    x2=float(r["x2"]),
                    y2=float(r["y2"]),
                    h2=float(r["h2"]) if r.get("h2") else None,
                    enabled_plan=r["enabled_plan"],
                    enabled_h=r["enabled_h"],
                )
                for r in valid_raw
            ]
        except ValueError as e:
            wx.MessageBox(f"Ошибка в данных таблицы:\n{e}", "Ошибка", wx.OK | wx.ICON_ERROR, self.parent)
            return None

        from core.transformation import calculate_helmert
        from core.geoid_correction import calculate_helmert_with_geoid, geoid_needed

        src_action, tgt_action = self.read_geoid_actions()
        apply_correction = self.is_geoid_correction_enabled()

        try:
            if geoid_needed(src_action, tgt_action):
                result, geoid_info = calculate_helmert_with_geoid(
                    pairs,
                    source_crs,
                    target_crs,
                    src_action,
                    tgt_action,
                    apply_correction=apply_correction,
                )

                if len(geoid_info.src) != len(valid_items) or len(geoid_info.tgt) != len(valid_items):
                    raise RuntimeError(
                        "Рассинхронизация геоидных данных: "
                        f"src={len(geoid_info.src)}, tgt={len(geoid_info.tgt)}, valid={len(valid_items)}"
                    )

                all_geoid_src = [None] * self.coord_grid.GetNumberRows()
                all_geoid_tgt = [None] * self.coord_grid.GetNumberRows()
                for j, (grid_row, _) in enumerate(valid_items):
                    all_geoid_src[grid_row] = geoid_info.src[j]
                    all_geoid_tgt[grid_row] = geoid_info.tgt[j]

                self.coord_grid.update_geoid_heights(all_geoid_src, all_geoid_tgt)
                self.set_delta_zeta_mean(geoid_info.delta_zeta_mean)
            else:
                result = calculate_helmert(pairs, source_crs, target_crs)
                self.coord_grid.clear_geoid_heights()
                self.set_delta_zeta_mean(None)

        except FileNotFoundError as e:
            wx.MessageBox(
                f"Файл геоида не найден:\n{e}\n\n"
                "Убедитесь, что egm08_25.gtx или us_nga_egm2008_1.tif "
                "присутствует в папке resources/",
                "Геоид не найден",
                wx.OK | wx.ICON_ERROR,
                self.parent,
            )
            return None
        except Exception as e:
            # оставляем поведение дебага, как ты и хотел
            raise e

        # разворот невязок на физические строки
        all_residuals = [None] * self.coord_grid.GetNumberRows()
        all_metric = [None] * self.coord_grid.GetNumberRows()

        if len(result.residuals) != len(valid_items) or len(result.residuals_enu) != len(valid_items):
            wx.MessageBox("Внутренняя ошибка: рассинхронизация размеров невязок.", "Ошибка", wx.OK | wx.ICON_ERROR, self.parent)
            return None

        for j, (grid_row, _) in enumerate(valid_items):
            all_residuals[grid_row] = result.residuals[j]
            all_metric[grid_row] = result.residuals_enu[j]

        self.update_results_view(result)

        filled_cells = self.autofill_missing_coordinates(raw_items, result, geoid_info)
        if filled_cells > 0:
            self.mark_modified("autofill_missing_coordinates")

        threshold = self.get_threshold_m()
        self.last_all_residuals = all_residuals
        self.last_all_metric = all_metric

        self.coord_grid.update_residuals(all_residuals, threshold=threshold)
        self.coord_grid.update_metric_residuals(all_metric, threshold=threshold)

        return CalculationRunResult(
            result=result,
            pairs=pairs,
            all_residuals=all_residuals,
            all_metric=all_metric,
        )