# -*- coding: utf-8 -*-
"""
gui/controllers/main_frame.py — главный контроллер Easy Helmert (PySide6).

Только инициализация состояния, UI и сервисов.
Все сигналы (бинды) намеренно убраны — подключать по мере готовности.
"""

import sys
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QVBoxLayout, QApplication
from pyproj import CRS

from core.models import PointPair, CalculationResult
from gui.forms.easy_helmert_base import BaseMainFrame
# ↓ Раскомментировать, когда PySide6-версии будут готовы:
# from gui.widgets.coordinate_grid import CoordinateGrid
# from gui.controllers.dirty_state import DirtyStateManager
# from gui.controllers.import_service import ImportService
# from gui.controllers.export_service import ExportService
# from gui.controllers.calculation_service import CalculationService, CalculationRunResult


class MainFrame(BaseMainFrame):
    """Главное окно приложения. Контроллер в паттерне MVC."""

    def __init__(self) -> None:
        super().__init__()

        # ── Состояние приложения ───────────────────────────────────────────
        self.point_pairs: List[PointPair] = []
        self.calc_result: Optional[CalculationResult] = None

        self._last_all_residuals: list = []
        self._last_all_metric: list = []
        self._last_delta_zeta_mean: Optional[float] = None

        self.source_crs: Optional[CRS] = None
        self.target_crs: Optional[CRS] = CRS.from_epsg(4979)
        self._source_crs_label: str = ""
        self._target_crs_label: str = ""

        # ── Dirty state ────────────────────────────────────────────────────
        # TODO: заменить заглушку на DirtyStateManager(debug=True)
        self._is_modified: bool = False

        # ── Инициализация UI и сервисов ────────────────────────────────────
        self._init_app_icon()
        self._init_grid_placeholder()
        self._init_default_crs_labels()
        self._init_services()

        # Финальный layout + позиция разделителя
        QTimer.singleShot(0, self._set_initial_splitter)

        # TODO: self._bind_events()
        # TODO: self._bind_hints()

    # ═══════════════════════════════════════════════════════════════════════
    # Инициализация
    # ═══════════════════════════════════════════════════════════════════════

    def _init_app_icon(self) -> None:
        """Иконка приложения (Windows 11: AppUserModelID)."""
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "easyhelmert.app.1.0"
            )
        # Иконка окна — подключить через QIcon, когда ресурсы будут перенесены:
        # from PySide6.QtGui import QIcon
        # icon_path = get_resource("icons/easy_helmert.ico")
        # if icon_path:
        #     self.setWindowIcon(QIcon(str(icon_path)))

    def _init_grid_placeholder(self) -> None:
        """
        Вставляем CoordinateGrid в self.grid_placeholder.

        Сейчас — заглушка (QWidget пустой).
        Когда coordinate_grid.py будет портирован:
            from gui.widgets.coordinate_grid import CoordinateGrid
            self.coord_grid = CoordinateGrid(
                self.grid_placeholder,
                on_data_changed=self._on_grid_data_changed,
            )
            layout = QVBoxLayout(self.grid_placeholder)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            layout.addWidget(self.coord_grid)
        """
        self.coord_grid = None  # заглушка

    def _init_default_crs_labels(self) -> None:
        """Выставляем подписи СК по умолчанию."""
        self.lbl_src_crs.setText("Не задана")
        self.lbl_src_crs.setEnabled(False)

        self.lbl_tgt_crs.setText("WGS 84 [EPSG:4979]")
        self.lbl_tgt_crs.setEnabled(True)

    def _init_services(self) -> None:
        """
        Инициализация сервисов.
        Сервисы ждут готовой CoordinateGrid — пока заглушки.
        """
        # TODO: раскомментировать после переноса coord_grid
        #
        # self.dirty = DirtyStateManager(debug=True)
        #
        # self.import_service = ImportService(
        #     parent=self,
        #     coord_grid=self.coord_grid,
        #     mark_modified=self._mark_modified,
        #     clear_residuals=self.coord_grid.clear_residuals,
        #     clear_result_text=lambda: self._clear_results_panel(),
        # )
        # self.export_service = ExportService(
        #     parent=self,
        #     coord_grid=self.coord_grid,
        #     get_source_crs=lambda: self.source_crs,
        #     get_target_crs=lambda: self.target_crs,
        #     get_calc_result=lambda: self.calc_result,
        #     get_source_label=lambda: self._source_crs_label,
        #     get_src_name=self._src_crs_name,
        #     get_tgt_name=self._tgt_crs_name,
        #     clear_modified=self._clear_modified,
        # )
        # self.calc_service = CalculationService(
        #     parent=self,
        #     coord_grid=self.coord_grid,
        #     get_source_crs=lambda: self.source_crs,
        #     get_target_crs=lambda: self.target_crs,
        #     read_geoid_actions=self._read_geoid_actions,
        #     is_geoid_correction_enabled=lambda: (
        #         self.chk_correction.isEnabled()
        #         and self.chk_correction.isChecked()
        #     ),
        #     set_delta_zeta_mean=lambda v: setattr(self, "_last_delta_zeta_mean", v),
        #     update_results_view=self.update_results,
        #     get_threshold_m=self._get_threshold_m,
        #     autofill_missing_coordinates=self._autofill_missing_coordinates,
        #     mark_modified=self._mark_modified,
        # )
        pass

    def _set_initial_splitter(self) -> None:
        """65% высоты окна под таблицу, 35% под нижнюю панель."""
        h = self.centralWidget().height()
        self.right_splitter.setSizes([int(h * 0.65), int(h * 0.35)])

    # ═══════════════════════════════════════════════════════════════════════
    # Dirty state helpers
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def is_modified(self) -> bool:
        return self._is_modified

    def _mark_modified(self, reason: str = "") -> None:
        self._is_modified = True
        # TODO: self.dirty.mark(reason)

    def _clear_modified(self, reason: str = "") -> None:
        self._is_modified = False
        # TODO: self.dirty.clear(reason)

    def _ask_save_if_modified(self) -> bool:
        """True → продолжить действие, False → пользователь нажал Отмена."""
        if not self._is_modified:
            return True
        # TODO: заменить на DirtyStateManager.ask_save_if_modified(...)
        # Пока просто разрешаем продолжить
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # Чтение UI (без событий)
    # ═══════════════════════════════════════════════════════════════════════

    def _read_geoid_actions(self):
        """
        Читает настройки геоида из UI.
        Возвращает (src_action, tgt_action) — оба GeoidAction.
        Если контролы неактивны — принудительно NOTHING.
        """
        from core.geoid_correction import GeoidAction, geoid_controls_active
        if not geoid_controls_active(self.source_crs, self.target_crs):
            return GeoidAction.NOTHING, GeoidAction.NOTHING
        return (
            GeoidAction(self.cmb_src_geoid.currentIndex()),
            GeoidAction(self.cmb_tgt_geoid.currentIndex()),
        )

    def _read_display_settings(self):
        """Собирает DisplaySettings из текущего состояния UI."""
        from core.models import (
            DisplaySettings, HelmertMethod, HelmertDirection,
            RotationUnit, ScaleUnit,
        )
        rms_all    = self._rms_from_grid()
        rms_active = self._rms_enu_active_from_grid()
        sigma0     = self._sigma0_enu_active_from_grid()
        src_note, tgt_note, warn_note = self._build_geoid_notes()

        return DisplaySettings(
            method=HelmertMethod(0 if self.rb_method_pv.isChecked() else 1),
            direction=HelmertDirection(0 if self.rb_dir_fwd.isChecked() else 1),
            rotation_unit=RotationUnit(self.cmb_rotation_units.currentIndex()),
            scale_unit=ScaleUnit(self.cmb_scale_units.currentIndex()),
            source_name=self._src_crs_name(),
            target_name=self._tgt_crs_name(),
            rms_metric_m=rms_all or 0.0,
            rms_metric_active_m=rms_active or 0.0,
            rms_metric_sigma0_m=sigma0 or 0.0,
            geoid_src_note=src_note,
            geoid_tgt_note=tgt_note,
            geoid_warn_note=warn_note,
        )

    def _get_threshold_m(self) -> float:
        """Порог подсветки невязок в метрах."""
        value = self.spin_threshold.value()
        if self.cmb_threshold_units.currentIndex() == 0:
            return value  # абсолютные метры
        rms = self._rms_from_grid()
        return value * rms if (rms and rms > 0) else value

    def _src_crs_name(self) -> str:
        if self.source_crs:
            return self._source_crs_label or self.source_crs.name
        return "исходная"

    def _tgt_crs_name(self) -> str:
        if self.target_crs:
            return self._target_crs_label or self.target_crs.name
        return "целевая"

    # ═══════════════════════════════════════════════════════════════════════
    # Вычисление RMS (вспомогательные)
    # ═══════════════════════════════════════════════════════════════════════

    def _rms_from_grid(self) -> Optional[float]:
        import numpy as np
        if self.calc_result is None or not self.calc_result.residuals_enu:
            return None
        arr = np.array(self.calc_result.residuals_enu)
        return float(np.sqrt(np.mean(arr ** 2)))

    def _rms_enu_active_from_grid(self) -> Optional[float]:
        if self.calc_result is None or not self.calc_result.residuals_enu:
            return None
        from core.transformation import compute_rms_enu_active
        return compute_rms_enu_active(self.point_pairs, self.calc_result.residuals_enu)

    def _sigma0_enu_active_from_grid(self) -> Optional[float]:
        if self.calc_result is None or not self.calc_result.residuals_enu:
            return None
        from core.transformation import compute_sigma0_enu_active
        return compute_sigma0_enu_active(self.point_pairs, self.calc_result.residuals_enu)

    def _build_geoid_notes(self) -> tuple[str, str, str]:
        src_action, tgt_action = self._read_geoid_actions()
        # TODO: self.calc_service.build_geoid_notes(...)
        return "", "", ""

    # ═══════════════════════════════════════════════════════════════════════
    # Обновление геоидных контролов (вызывается при смене СК)
    # ═══════════════════════════════════════════════════════════════════════

    def _update_geoid_controls(self) -> None:
        from core.geoid_correction import (
            GeoidAction, geoid_controls_active, crs_is_wgs84_related,
        )
        active = geoid_controls_active(self.source_crs, self.target_crs)
        self.cmb_src_geoid.setEnabled(active)
        self.cmb_tgt_geoid.setEnabled(active)

        correction_ok = (
            active
            and self.target_crs is not None
            and crs_is_wgs84_related(self.target_crs)
            and self.cmb_src_geoid.currentIndex() == int(GeoidAction.ADD)
        )
        self.chk_correction.setEnabled(correction_ok)
        if not correction_ok:
            self.chk_correction.setChecked(False)

    # ═══════════════════════════════════════════════════════════════════════
    # Обновление View — результаты
    # ═══════════════════════════════════════════════════════════════════════

    def update_results(self, result: CalculationResult) -> None:
        """
        Заполняет нижнюю панель результатами вычисления.
        wx: self._set_result_text(display.to_text())
        """
        display = result.params.as_display(self._read_display_settings())

        dz = self._last_delta_zeta_mean
        dz_note = (
            f"\n\nΔζ (Квазигеоид − EGM2008) = {dz:+.4f} м ({dz * 100:+.2f} см)"
            if dz is not None else ""
        )

        # 1. Текстовый блок (пока в params_table через заглушку)
        self._fill_params_table(display)

        # 2. Карточка точности
        rms = display.rms_metric_m
        self.lbl_rms_big.setText(f"RMS: {rms:.3f} м")
        threshold = self._get_threshold_m()
        if rms <= threshold:
            self.lbl_rms_badge.setText("● В ДОПУСКЕ")
            self.lbl_rms_badge.setObjectName("badge_ok")
        else:
            self.lbl_rms_badge.setText("● ПРЕВЫШЕНИЕ")
            self.lbl_rms_badge.setObjectName("badge_bad")
        # Перечитать стиль после смены objectName
        for w in (self.lbl_rms_badge,):
            w.style().unpolish(w)
            w.style().polish(w)

        # 3. История
        from datetime import datetime
        n_pts = len(self.point_pairs)
        method_str = "7 пар." if (self.rb_method_pv.isChecked()) else "CF"
        entry = f"{datetime.now():%d.%m.%Y %H:%M}  ·  {method_str}  ·  {n_pts} т.  ·  RMS {rms:.3f}"
        self.history_list.insertItem(0, entry)
        self.history_list.setCurrentRow(0)

        # 4. Счётчик точек в тулбаре
        self._update_point_count()

    def _fill_params_table(self, display) -> None:
        """Заполняет таблицу параметров трансформации в нижней панели."""
        # TODO: распарсить display.params и вставить построчно в self.params_table
        # Пример структуры: dX, dY, dZ, rX, rY, rZ, dS
        # self.params_table.setItem(row, 1, QTableWidgetItem(f"{value:.6f}"))
        pass

    def _clear_results_panel(self) -> None:
        """Сбрасывает нижнюю панель в исходное состояние."""
        self.lbl_rms_big.setText("RMS: —")
        self.lbl_rms_badge.setText("")
        self.params_table.clearContents()

    def _update_point_count(self) -> None:
        """Обновляет счётчик точек в тулбаре."""
        if self.coord_grid is not None:
            # TODO: self.coord_grid.get_row_count() и т.п.
            pass
        # self.lbl_point_count.setText(f"Точек: {total} · Используется: {active}")

    # ═══════════════════════════════════════════════════════════════════════
    # Handlers — ЗАГЛУШКИ (бинды не подключены)
    # ═══════════════════════════════════════════════════════════════════════
    # Порядок — как в wx-версии _bind_events.
    # Каждый метод помечен TODO с указанием, что нужно раскомментировать.

    def on_exit(self) -> None:
        if not self._ask_save_if_modified():
            return
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._ask_save_if_modified():
            event.ignore()
        else:
            event.accept()

    # ── Файл ──────────────────────────────────────────────────────────────

    def on_new_calc(self) -> None:
        if not self._ask_save_if_modified():
            return
        # TODO: self.coord_grid.set_data([])
        # TODO: self.coord_grid.clear_residuals()
        self.point_pairs = []
        self.calc_result = None
        self._last_all_residuals = []
        self._last_all_metric = []
        self._last_delta_zeta_mean = None
        self._clear_modified("new_calc")
        self._clear_results_panel()

    def on_import_txt(self) -> None:
        pass  # TODO: self.import_service.import_from_text_dialog()

    def on_import_calibration(self) -> None:
        pass  # TODO: self.import_service.import_calibration_dialog()

    def on_export_calibration(self) -> None:
        pass  # TODO: self.export_service.export_calibration_dialog()

    def on_save_table(self) -> None:
        pass  # TODO: self.export_service.save_table_to_file()

    # ── Меню «Вычисленные параметры» ──────────────────────────────────────

    def on_save_wkt1(self) -> None:
        pass  # TODO: self.export_service.save_crs_to_file("wkt1")

    def on_save_wkt2(self) -> None:
        pass  # TODO: self.export_service.save_crs_to_file("wkt2")

    def on_save_proj4(self) -> None:
        pass  # TODO: self.export_service.save_crs_to_file("proj4")

    def on_copy_wkt1(self) -> None:
        pass  # TODO: self.export_service.copy_crs_to_clipboard("wkt1")

    def on_copy_wkt2(self) -> None:
        pass  # TODO: self.export_service.copy_crs_to_clipboard("wkt2")

    def on_copy_proj4(self) -> None:
        pass  # TODO: self.export_service.copy_crs_to_clipboard("proj4")

    # ── Тулбар таблицы ────────────────────────────────────────────────────

    def on_add_row(self) -> None:
        pass  # TODO: self.coord_grid.add_row()

    def on_del_row(self) -> None:
        pass  # TODO: self.coord_grid.delete_selected_rows()

    def on_row_move_up(self) -> None:
        pass  # TODO: self.coord_grid.move_selected_rows_up()

    def on_row_move_down(self) -> None:
        pass  # TODO: self.coord_grid.move_selected_rows_down()

    def on_swap_src(self) -> None:
        # TODO: self.coord_grid.swap_source_xy()
        self._mark_modified("swap_src")

    def on_swap_dst(self) -> None:
        # TODO: self.coord_grid.swap_target_xy()
        self._mark_modified("swap_dst")

    def on_parse_degrees(self) -> None:
        """Конвертация DMS → DD в таблице."""
        # TODO: собрать rows_payload из coord_grid и показать ParseDegreesDialog
        pass

    # ── СК ────────────────────────────────────────────────────────────────

    def on_select_source_crs(self) -> None:
        from gui.dialogs.crs_picker_dialog import CrsPickerDialog
        dlg = CrsPickerDialog(self, "Исходная система координат")
        if dlg.exec():
            self.source_crs = dlg.get_selected_crs()
            self._source_crs_label = dlg.get_selected_name()
            self.lbl_src_crs.setText(dlg.get_selected_name())
            self.lbl_src_crs.setEnabled(True)
            self._update_geoid_controls()

    def on_select_target_crs(self) -> None:
        from gui.dialogs.crs_picker_dialog import CrsPickerDialog
        dlg = CrsPickerDialog(self, "Целевая система координат")
        if dlg.exec():
            self.target_crs = dlg.get_selected_crs()
            self._target_crs_label = dlg.get_selected_name()
            self.lbl_tgt_crs.setText(dlg.get_selected_name())
            self._update_geoid_controls()

    # ── Расчёт ────────────────────────────────────────────────────────────

    def on_calculate(self) -> None:
        # TODO:
        # run_out = self.calc_service.run()
        # if run_out is None:
        #     return
        # self.calc_result = run_out.result
        # self.point_pairs = run_out.pairs
        # self._last_all_residuals = run_out.all_residuals
        # self._last_all_metric = run_out.all_metric
        pass

    def on_find_optimum(self) -> None:
        pairs = self._get_current_pairs_from_grid()
        if len(pairs) < 3:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Нет данных",
                                    "Недостаточно точек для оптимизации (минимум 3).")
            return
        if self.source_crs is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Нет исходной СК",
                                "Задайте исходную систему координат.")
            return
        src_action, tgt_action = self._read_geoid_actions()
        apply_correction = self.chk_correction.isChecked()
        # TODO:
        # from gui.dialogs.optimize_dialog import OptimizeDialog
        # dlg = OptimizeDialog(self, pairs, self.source_crs, self.target_crs,
        #                      src_action, tgt_action, apply_correction)
        # if dlg.exec() and hasattr(dlg, "applied_plan"):
        #     for i, (plan, h) in enumerate(zip(dlg.applied_plan, dlg.applied_height)):
        #         self.coord_grid.set_enabled_plan(i, plan)
        #         self.coord_grid.set_enabled_h(i, h)
        #     self._mark_modified("optimize_apply")
        #     self.on_calculate()

    # ── Карта ─────────────────────────────────────────────────────────────

    def show_on_map(self) -> None:
        if self.calc_result is None:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(self, "Нет результата",
                                    "Сначала выполните расчёт.")
            return
        # TODO:
        # from gui.dialogs.map_dialog import MapDialog
        # from gui.utils.map_points_builder import build_points_for_map
        # raw_items = self.coord_grid.get_data_with_row_indices()
        # src_pts, tgt_pts = build_points_for_map(
        #     raw_items, self.source_crs, self.target_crs, self.calc_result
        # )
        # dlg = MapDialog(self)
        # dlg.set_points(src_pts, tgt_pts, "Точки калибровки")
        # dlg.exec()

    # ── О программе ───────────────────────────────────────────────────────

    def on_about(self) -> None:
        pass  # TODO: from gui.dialogs.about_dialog import AboutDialog; AboutDialog(self).exec()

    # ═══════════════════════════════════════════════════════════════════════
    # Внутренние события от CoordinateGrid
    # ═══════════════════════════════════════════════════════════════════════

    def _on_grid_data_changed(self) -> None:
        """
        Вызывается CoordinateGrid при ЛЮБОМ изменении данных.
        wx: EVT_GRID_CELL_CHANGED + флаги чекбоксов.
        """
        self._mark_modified("grid_data_changed")
        self._clear_results_panel()
        if self.coord_grid is not None:
            QTimer.singleShot(0, self.coord_grid.clear_residuals)

    # ── Реакция на изменение настроек отображения ─────────────────────────

    def _on_display_settings_changed(self) -> None:
        """Перерисовать результаты без пересчёта."""
        if self.calc_result is not None:
            self.update_results(self.calc_result)

    def _on_threshold_changed(self) -> None:
        if self.calc_result is None:
            return
        threshold = self._get_threshold_m()
        if self.coord_grid is None:
            return
        # TODO:
        # if self._last_all_residuals:
        #     self.coord_grid.update_residuals(self._last_all_residuals, threshold=threshold)
        # if self._last_all_metric:
        #     self.coord_grid.update_metric_residuals(self._last_all_metric, threshold=threshold)

    # ═══════════════════════════════════════════════════════════════════════
    # Вспомогательные (перенесены без изменения логики)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_current_pairs_from_grid(self) -> List[PointPair]:
        """Текущий список PointPair из таблицы (для on_find_optimum)."""
        if self.coord_grid is None:
            return []
        # TODO: data = self.coord_grid.get_data()
        data = []
        pairs = []
        for r in data:
            try:
                x1 = float(str(r.get("x1", "")).replace(",", "."))
                y1 = float(str(r.get("y1", "")).replace(",", "."))
                x2 = float(str(r.get("x2", "")).replace(",", "."))
                y2 = float(str(r.get("y2", "")).replace(",", "."))
            except (ValueError, TypeError):
                continue
            h1 = None
            h2 = None
            try:
                h1 = float(str(r.get("h1", "")).replace(",", ".")) if r.get("h1") else None
                h2 = float(str(r.get("h2", "")).replace(",", ".")) if r.get("h2") else None
            except (ValueError, TypeError):
                pass
            pairs.append(PointPair(
                name=r.get("name", ""),
                x1=x1, y1=y1, h1=h1,
                x2=x2, y2=y2, h2=h2,
                enabled_plan=r.get("enabled_plan", True),
                enabled_h=r.get("enabled_h", True),
            ))
        return pairs

    def _autofill_missing_coordinates(self, raw_items, result, geoid_info) -> int:
        """Достройка отсутствующей стороны координат."""
        src_action, tgt_action = self._read_geoid_actions()
        # TODO: self.calc_service.prepare_autofill_payload(...)
        # TODO: self.coord_grid.fill_missing_coordinates(predictions)
        return 0
