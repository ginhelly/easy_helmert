import wx
from typing import Dict, List, Optional
from pyproj import CRS

from core.models import *
from gui.forms.easy_helmert_base import BaseMainFrame
from gui.widgets.coordinate_grid import CoordinateGrid
from gui.controllers.dirty_state import DirtyStateManager
from gui.controllers.import_service import ImportService
from gui.controllers.export_service import ExportService
from gui.controllers.calculation_service import CalculationService, CalculationRunResult
from utils.xrc_loader import xrc
from utils.resources import get_resource


class MainFrame(BaseMainFrame):
    """Главное окно приложения. Контроллер в паттерне MVC."""

    def __init__(self):
        if not xrc.load("icons.xrc", "icons"):
            wx.MessageBox(
                "Не удалось загрузить иконки. Проверь resources/icons/icons.xrc",
                "Предупреждение", wx.OK | wx.ICON_WARNING
            )

        super().__init__(None)

        self.point_pairs: List[PointPair] = []
        self.calc_result: Optional[CalculationResult] = None
        self.dirty = DirtyStateManager(debug=True)

        self._init_ui()

        self.import_service = ImportService(
            parent=self,
            coord_grid=self.coord_grid,
            mark_modified=self._mark_modified,
            clear_residuals=self.coord_grid.clear_residuals,
            clear_result_text=lambda: self._set_result_text(""),
        )
        self.export_service = ExportService(
            parent=self,
            coord_grid=self.coord_grid,
            get_source_crs=lambda: getattr(self, "source_crs", None),
            get_target_crs=lambda: getattr(self, "target_crs", None),
            get_calc_result=lambda: self.calc_result,
            get_source_label=lambda: getattr(self, "_source_crs_label", "") or "",
            get_src_name=self._src_crs_name,
            get_tgt_name=self._tgt_crs_name,
            clear_modified=self._clear_modified,
        )

        self.calc_service = CalculationService(
            parent=self,
            coord_grid=self.coord_grid,
            get_source_crs=lambda: getattr(self, "source_crs", None),
            get_target_crs=lambda: getattr(self, "target_crs", None),
            read_geoid_actions=self._read_geoid_actions,
            is_geoid_correction_enabled=lambda: (
                self.m_chk_correction.IsEnabled() and self.m_chk_correction.GetValue()
            ),
            set_delta_zeta_mean=lambda v: setattr(self, "_last_delta_zeta_mean", v),
            update_results_view=self.update_results,
            get_threshold_m=self._get_threshold_m,
            autofill_missing_coordinates=self._autofill_missing_coordinates,
            mark_modified=self._mark_modified,
        )

        self._setup_layout()
        self._bind_events()
        self._setup_toolbar_icons()
        wx.CallAfter(self.adjust_menu_icons)
        self._bind_hints()

        self.Centre()
        self.Show()

    # ── Dirty state helpers ────────────────────────────────────────────────

    @property
    def is_modified(self) -> bool:
        return self.dirty.is_modified

    def _mark_modified(self, reason: str = ""):
        self.dirty.mark(reason)

    def _clear_modified(self, reason: str = ""):
        self.dirty.clear(reason)

    # ── UI init ───────────────────────────────────────────────────────────────

    def _init_ui(self):
        """Создание виджетов, которые нельзя/неудобно делать в FormBuilder."""
        import sys
        from utils.resources import get_resource

        # Windows 11: привязка иконки к приложению, а не к python.exe
        if sys.platform == "win32":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "easyhelmert.app.1.0"
            )

        icon_path = get_resource("icons/easy_helmert.ico")
        if icon_path:
            # IconBundle передаёт ВСЕ размеры из .ico → Windows выбирает нужный
            bundle = wx.IconBundle(str(icon_path), wx.BITMAP_TYPE_ICO)
            self.SetIcons(bundle)

        # 1. Вставляем CoordinateGrid в placeholder-панель из FormBuilder
        self.coord_grid = CoordinateGrid(
            self.m_grid_placeholder,
            on_data_changed=self._on_grid_data_changed
        )

        grid_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer.Add(self.coord_grid, 1, wx.EXPAND)
        self.m_grid_placeholder.SetSizer(grid_sizer)

        # 2. Разделитель — FormBuilder не всегда добавляет SplitHorizontally
        #    в Python-коде, поэтому делаем сами (если уже не сделан)
        if not self.m_splitter.IsSplit():
            self.m_splitter.SplitHorizontally(
                self.m_panel_input,
                self.m_panel_result,
                sashPosition=0   # 0 → FormBuilder/gravity подберёт сам
            )
        self.m_splitter.SetMinimumPaneSize(120)

        # 3. Целевая СК по умолчанию — WGS 84 (3D)
        self.source_crs = None
        self.target_crs = CRS.from_epsg(4979)
        self.m_lbl_tgt_crs.SetLabel("WGS 84 [EPSG:4979]")
        wx.CallAfter(self._update_geoid_controls)

    def _setup_layout(self):
        self.Layout()
        # Устанавливаем разделитель на 65% высоты клиентской области
        wx.CallAfter(self._set_initial_sash)

    def _set_initial_sash(self):
        h = self.GetClientSize().height
        self.m_splitter.SetSashPosition(int(h * 0.65))

    # ── Events ────────────────────────────────────────────────────────────────

    def _bind_events(self):
        # Меню / закрытие
        self.Bind(wx.EVT_MENU,  self.on_exit,      self.m_exit_item)
        self.Bind(wx.EVT_CLOSE, self.on_exit)

        # ── Новый расчёт ───────────────────────────────────────────────────
        self.Bind(wx.EVT_MENU,  self.on_new_calc,  self.m_menuItem_new_calc)
        self.Bind(wx.EVT_TOOL,  self.on_new_calc,  self.m_tool_new_calc)

        # ── Импорт ────────────────────────────────────────────────────────
        self.Bind(wx.EVT_MENU, self.on_import_txt,  self.m_menuItem_import_txt)
        self.Bind(wx.EVT_TOOL, self.on_import_txt,  self.m_tool_import_txt)

        # Импорт калибровки
        self.Bind(wx.EVT_MENU, self.on_import_calibration, self.m_menuItem_import_calibration)
        self.Bind(wx.EVT_TOOL, self.on_import_calibration, self.m_tool_import_calibration)

        # Кнопки шапки таблицы
        self.Bind(wx.EVT_BUTTON, self.on_add_row,    self.m_btn_add_row)
        self.Bind(wx.EVT_BUTTON, self.on_del_row,    self.m_btn_del_row)
        self.Bind(wx.EVT_BUTTON, self.on_swap_src,   self.m_btn_swap_src)
        self.Bind(wx.EVT_BUTTON, self.on_swap_dst,   self.m_btn_swap_dst)
        self.Bind(wx.EVT_MENU, self.on_swap_src,   self.m_menuItem_swapxy_src)
        self.Bind(wx.EVT_MENU, self.on_swap_dst,   self.m_menuItem_swapxy_tgt)
        self.Bind(wx.EVT_BUTTON, self.on_calculate,  self.m_btn_calc)

        self.Bind(wx.EVT_MENU, self.on_parse_degrees, self.m_menuItem_parse_degrees)

        # Кнопки установки систем координат
        self.Bind(wx.EVT_BUTTON, self.on_select_source_crs,    self.m_btn_set_src_crs)
        self.Bind(wx.EVT_BUTTON, self.on_select_target_crs,    self.m_btn_set_tgt_crs)

        for ctrl in (
            self.m_rb_method,
            self.m_rb_direction,
            self.m_choice_rotation_units,
            self.m_choice_scale_units,
        ):
            ctrl.Bind(
                wx.EVT_RADIOBOX if isinstance(ctrl, wx.RadioBox) else wx.EVT_CHOICE,
                self._on_display_settings_changed,
            )
        
        self.m_spin_bad_threshold.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_threshold_changed)
        self.m_choice_bad_units.Bind(wx.EVT_CHOICE, self._on_threshold_changed)
        self.m_spin_bad_threshold.Bind(wx.EVT_TEXT_ENTER, self._on_threshold_enter)

            # ── Экспорт результата (меню) ────────────────────────────────────────
        self.Bind(wx.EVT_MENU, lambda e: self._save_crs_to_file("wkt1"),        self.m_menuItem_save_wkt1)
        self.Bind(wx.EVT_MENU, lambda e: self._save_crs_to_file("wkt2"),        self.m_menuItem_save_wkt2)
        self.Bind(wx.EVT_MENU, lambda e: self._save_crs_to_file("proj4"),       self.m_menuItem_save_proj4)
        self.Bind(wx.EVT_MENU, lambda e: self._copy_crs_to_clipboard("wkt1"),   self.m_menuItem_copy_wkt1)
        self.Bind(wx.EVT_MENU, lambda e: self._copy_crs_to_clipboard("wkt2"),   self.m_menuItem_copy_wkt2)
        self.Bind(wx.EVT_MENU, lambda e: self._copy_crs_to_clipboard("proj4"),  self.m_menuItem_copy_proj4)

        # WKT2 — только наличие результата
        for item in (self.m_menuItem_save_wkt2, self.m_menuItem_copy_wkt2, self.m_tool_copy_wkt2):
            self.Bind(wx.EVT_UPDATE_UI, self._on_update_export_ui, item)

        # WKT1 и Proj4 — результат + целевая WGS84
        for item in (
            self.m_menuItem_save_wkt1,  self.m_menuItem_save_proj4,
            self.m_menuItem_copy_wkt1,  self.m_menuItem_copy_proj4,
            self.m_tool_copy_wkt1,      self.m_tool_copy_proj4
        ):
            self.Bind(wx.EVT_UPDATE_UI, self._on_update_towgs84_ui, item)
        
        self.Bind(wx.EVT_MENU, self._save_table_to_file, self.m_menuItem_save_table)
        self.Bind(wx.EVT_MENU, self.on_export_calibration, self.m_menuItem_export_calibration)
        self.Bind(wx.EVT_MENU, self.on_about, self.m_menuItem_about)

        self.Bind(wx.EVT_TOOL, self.on_calculate, self.m_tool_calculate)
        self.Bind(wx.EVT_TOOL, lambda e: self._copy_crs_to_clipboard("wkt1"), self.m_tool_copy_wkt1)
        self.Bind(wx.EVT_TOOL, lambda e: self._copy_crs_to_clipboard("wkt2"), self.m_tool_copy_wkt2)
        self.Bind(wx.EVT_TOOL, lambda e: self._copy_crs_to_clipboard("proj4"), self.m_tool_copy_proj4)
        self.Bind(wx.EVT_TOOL, self._save_table_to_file, self.m_tool_save_table)
        self.Bind(wx.EVT_TOOL, self.on_export_calibration, self.m_tool_export_calibration)
        self.m_rb_src_action.Bind(
            wx.EVT_RADIOBOX,
            lambda e: (self._update_geoid_controls(), e.Skip()),
        )
        
        self.Bind(wx.EVT_MENU, self.show_on_map, self.m_menuItem_show_on_map)
        self.Bind(wx.EVT_TOOL, self.show_on_map, self.m_tool_show_on_map)
        self.Bind(wx.EVT_UPDATE_UI, self._on_update_show_on_map_ui, self.m_menuItem_show_on_map)
        self.Bind(wx.EVT_UPDATE_UI, self._on_update_show_on_map_ui, self.m_tool_show_on_map)

        self.Bind(wx.EVT_BUTTON, self.on_row_move_up,   self.m_btn_row_move_up)
        self.Bind(wx.EVT_BUTTON, self.on_row_move_down, self.m_btn_row_move_down)

    def _on_update_export_ui(self, event):
        event.Enable(self.calc_result is not None)

    def _on_update_towgs84_ui(self, event):
        from utils.crs_export import is_wgs84_target
        ok = (
            self.calc_result is not None
            and getattr(self, "target_crs", None) is not None
            and is_wgs84_target(self.target_crs)
        )
        event.Enable(ok)

    def _on_display_settings_changed(self, event):
        if self.calc_result is not None:
            self.update_results(self.calc_result)
        event.Skip()

    def _on_grid_data_changed(self):
        """
        Вызывается CoordinateGrid при ЛЮБОМ изменении данных:
        редактирование ячейки, переключение чекбокса, swap, дублирование, удаление.
        """
        self._mark_modified("grid_data_changed")
        self._set_result_text("")
        wx.CallAfter(self.coord_grid.clear_residuals)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def on_add_row(self, event):
        self.coord_grid.add_row()

    def on_del_row(self, event):
        self.coord_grid.delete_selected_rows()

    def on_swap_src(self, event):
        self.coord_grid.swap_source_xy()
        self._mark_modified("swap_src")

    def on_swap_dst(self, event):
        self.coord_grid.swap_target_xy()
        self._mark_modified("swap_dst")

    def on_calculate(self, event):
        run_out = self.calc_service.run()
        if run_out is None:
            return

        self.calc_result = run_out.result
        self.point_pairs = run_out.pairs
        self._last_all_residuals = run_out.all_residuals
        self._last_all_metric = run_out.all_metric
    
    def _read_display_settings(self) -> DisplaySettings:
        src_note, tgt_note, warn_note = self._build_geoid_notes()

        rms_all = self._rms_from_grid()
        rms_active = self._rms_enu_active_from_grid()
        sigma0_active = self._sigma0_enu_active_from_grid()

        return DisplaySettings(
            method=HelmertMethod(self.m_rb_method.GetSelection()),
            direction=HelmertDirection(self.m_rb_direction.GetSelection()),
            rotation_unit=RotationUnit(self.m_choice_rotation_units.GetSelection()),
            scale_unit=ScaleUnit(self.m_choice_scale_units.GetSelection()),
            source_name=self._src_crs_name(),
            target_name=self._tgt_crs_name(),
            rms_metric_m=rms_all if rms_all is not None else 0.0,
            rms_metric_active_m=rms_active if rms_active is not None else 0.0,
            rms_metric_sigma0_m=sigma0_active if sigma0_active is not None else 0.0,
            geoid_src_note=src_note,
            geoid_tgt_note=tgt_note,
            geoid_warn_note=warn_note,
        )

    def _update_geoid_controls(self):
        """
        Включает/отключает контролы геоида.

        Основные радиобоксы + кнопка высот: активны если хотя бы одна СК
        связана с WGS-84.

        Чекбокс поправки Балтика→EGM: только когда
        • target_crs связана с WGS-84  (высоты опорных точек — в WGS)
        • src_action == ADD             (к исходным точкам прибавляем EGM)
        Если условия не выполнены — чекбокс сбрасывается и блокируется.
        """
        from core.geoid_correction import (
            GeoidAction, geoid_controls_active, crs_is_wgs84_related,
        )
        src_crs = getattr(self, "source_crs", None)
        tgt_crs = getattr(self, "target_crs", None)

        active = geoid_controls_active(src_crs, tgt_crs)
        for ctrl in (
            self.m_rb_src_action,
            self.m_rb_tgt_action,
        ):
            ctrl.Enable(active)

        # Чекбокс поправки
        correction_ok = (
            active
            and tgt_crs is not None
            and crs_is_wgs84_related(tgt_crs)
            and self.m_rb_src_action.GetSelection() == int(GeoidAction.ADD)
        )
        self.m_chk_correction.Enable(correction_ok)
        if not correction_ok:
            self.m_chk_correction.SetValue(False)

    def _read_geoid_actions(self):
        """
        Читает настройки геоида из UI.
        Возвращает (src_action, tgt_action) — оба GeoidAction.
        Если контролы неактивны — принудительно NOTHING для обоих.
        """
        from core.geoid_correction import GeoidAction, geoid_controls_active
        if not geoid_controls_active(
            getattr(self, "source_crs", None),
            getattr(self, "target_crs", None),
        ):
            return GeoidAction.NOTHING, GeoidAction.NOTHING
        return (
            GeoidAction(self.m_rb_src_action.GetSelection()),
            GeoidAction(self.m_rb_tgt_action.GetSelection()),
        )

    def _rms_from_grid(self) -> Optional[float]:
        """СКО по ENU-невязкам из последнего результата расчёта."""
        import numpy as np
        if self.calc_result is None or not self.calc_result.residuals_enu:
            return None
        arr = np.array(self.calc_result.residuals_enu)
        return float(np.sqrt(np.mean(arr ** 2)))

    def update_results(self, result: CalculationResult):
        display = result.params.as_display(self._read_display_settings())
        text    = display.to_text()

        dz = getattr(self, "_last_delta_zeta_mean", None)
        if dz is not None:
            text += (
                f"\n\n"
                f"  Δζ (Квазигеоид − EGM2008) = {dz:+.4f} м  "
                f"({dz * 100:+.2f} см)"
            )

        self._set_result_text(text)

    def _src_crs_name(self) -> str:
        if getattr(self, "source_crs", None):
            return getattr(self, "_source_crs_label",
                        self.source_crs.name)
        return "исходная"

    def _tgt_crs_name(self) -> str:
        if getattr(self, "target_crs", None):
            return getattr(self, "_target_crs_label",
                        self.target_crs.name)
        return "целевая"

    def _save_table_to_file(self, event):
        return self.export_service.save_table_to_file()

    # ── View update ───────────────────────────────────────────────────────────

    def update_table(self, pairs: List[PointPair], result=None):
        """Обновить таблицу: данные + невязки после расчёта."""
        data = [
            {
                "enabled_plan": p.enabled_plan,  # или p.enabled если модель не менялась
                "enabled_h":    p.enabled_h,
                "name": p.name,
                "x1": str(p.x1), "y1": str(p.y1), "h1": str(getattr(p, "h1", "")),
                "x2": str(p.x2), "y2": str(p.y2), "h2": str(getattr(p, "h2", "")),
            }
            for p in pairs
        ]
        self.coord_grid.set_data(data)
        if result is not None:
            self.coord_grid.update_residuals(result.residuals)

    def _set_result_text(self, text: str):
        self.m_txt_result.SetValue(text)

    # ── Toolbar / Menu icons (без изменений) ──────────────────────────────────

    def _setup_toolbar_icons(self):
        tool_icons = {
            "Импорт калибровки...": "import_icon",
            "Копировать WKT1": "copy_wkt1_icon",
            "Копировать WKT2": "copy_wkt2_icon",
            "Копировать Proj4": "copy_proj4_icon",
            "Показать на карте": "show_on_map_icon"
        }
        for pos in range(self.m_toolbar.GetToolsCount()):
            tool = self.m_toolbar.GetToolByPos(pos)
            if tool and tool.GetLabel() in tool_icons:
                bmp = xrc.get_bitmap(tool_icons[tool.GetLabel()], (32, 32))
                if bmp.IsOk():
                    self.m_toolbar.SetToolNormalBitmap(tool.GetId(), bmp)
        self.m_toolbar.Realize()

    def adjust_menu_icons(self):
        menubar = self.GetMenuBar()
        if not menubar:
            return
        for i in range(menubar.GetMenuCount()):
            for item in menubar.GetMenu(i).GetMenuItems():
                if item.GetBitmap().IsOk():
                    bmp = item.GetBitmap()
                    if bmp.GetSize() != (16, 16):
                        img = bmp.ConvertToImage().Scale(16, 16, wx.IMAGE_QUALITY_HIGH)
                        item.SetBitmap(wx.Bitmap(img))

    def on_load_file(self, event):
        # TODO
        wx.MessageBox("Загрузка из файла — заглушка", "Инфо")
    
    def _ask_save_if_modified(self) -> bool:
        return self.dirty.ask_save_if_modified(
            parent=self,
            has_data=lambda: bool(self.coord_grid.get_data()),
            save_callable=lambda: self._save_table_to_file(None),
        )

    def on_exit(self, event):
        """Закрытие приложения с проверкой несохранённых данных."""
        if not self._ask_save_if_modified():
            return          # пользователь нажал «Отмена» — остаёмся
        self.Destroy()

    def on_new_calc(self, event):
        """Новый расчёт: очистить таблицу и результаты."""
        if not self._ask_save_if_modified():
            return

        # Сбрасываем таблицу до MIN_ROWS пустых строк
        self.coord_grid.set_data([])
        self.coord_grid.clear_residuals()

        # Сбрасываем состояние
        self.point_pairs  = []
        self.calc_result  = None
        self._last_all_residuals = []
        self._last_all_metric    = []
        self._last_delta_zeta_mean = None
        self._clear_modified("new_calc")

        # Очищаем панель результатов
        self._set_result_text("")

    def on_import_txt(self, event):
        self.import_service.import_from_text_dialog()
    
    def on_import_calibration(self, event):
        self.import_service.import_calibration_dialog()
    
    def on_select_source_crs(self, event):
        from gui.dialogs.crs_picker_dialog import CrsPickerDialog
        with CrsPickerDialog(self, "Исходная система координат") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.source_crs = dlg.get_selected_crs()
                self._source_crs_label  = dlg.get_selected_name()
                self.m_lbl_src_crs.SetLabel(dlg.get_selected_name())
                self._update_geoid_controls()

    def on_select_target_crs(self, event):
        from gui.dialogs.crs_picker_dialog import CrsPickerDialog
        with CrsPickerDialog(self, "Целевая система координат") as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.target_crs = dlg.get_selected_crs()
                self._target_crs_label  = dlg.get_selected_name()
                self.m_lbl_tgt_crs.SetLabel(dlg.get_selected_name())
                self._update_geoid_controls()
    
    def _get_threshold_m(self) -> float:
        """
        Возвращает порог подсветки в метрах.
        «метров» → значение спинера напрямую.
        «СКО»    → значение спинера × СКО_ENU из последнего результата.
        """
        value = self.m_spin_bad_threshold.GetValue()
        if self.m_choice_bad_units.GetSelection() == 1:
            # абсолютные метры
            return value
        else:
            # кратно СКО
            rms = self._rms_from_grid()
            if rms and rms > 0:
                return value * rms
            # СКО ещё не посчитано — fallback на абсолютное значение
            return value

    def _on_threshold_changed(self, event):
        if self.calc_result is None:
            event.Skip()
            return
        threshold = self._get_threshold_m()
        # Перекрашиваем невязки с новым порогом без пересчёта
        if hasattr(self, '_last_all_residuals'):
            self.coord_grid.update_residuals(
                self._last_all_residuals, threshold=threshold
            )
        if hasattr(self, '_last_all_metric'):
            self.coord_grid.update_metric_residuals(
                self._last_all_metric, threshold=threshold
            )
        event.Skip()
    
    def _on_threshold_enter(self, event):
        wx.CallAfter(self._apply_threshold_from_spin_text)
        event.Skip()

    def _apply_threshold_from_spin_text(self):
        # 1) коммитим текст в value
        try:
            txt = self.m_spin_bad_threshold.GetTextValue()  # важно
            if txt:
                self.m_spin_bad_threshold.SetValue(float(txt.replace(",", ".")))
        except Exception:
            pass

        # 2) перерисовываем сразу
        if self.calc_result is not None:
            threshold = self._get_threshold_m()
            if hasattr(self, "_last_all_residuals"):
                self.coord_grid.update_residuals(self._last_all_residuals, threshold=threshold)
            if hasattr(self, "_last_all_metric"):
                self.coord_grid.update_metric_residuals(self._last_all_metric, threshold=threshold)

    def _bind_statusbar_hint(self, ctrl: wx.Window, text: str):
        """
        Показывает подсказку в статусбаре при наведении мыши на контрол.
        Восстанавливает пустую строку при уходе курсора.
        """
        ctrl.Bind(wx.EVT_ENTER_WINDOW,
                lambda e, t=text: (self.m_statusBar1.SetStatusText(t), e.Skip()))
        ctrl.Bind(wx.EVT_LEAVE_WINDOW,
                lambda e: (self.m_statusBar1.SetStatusText(""), e.Skip()))
    
    def _bind_hints(self):
        self._bind_statusbar_hint(
            self.m_btn_calc,
            "Вычислить 7 параметров преобразования Гельмерта по введённым точкам"
        )
        self._bind_statusbar_hint(
            self.m_btn_set_src_crs,
            "Выбрать исходную систему координат из базы или задать вручную (WKT/Proj4)"
        )
        self._bind_statusbar_hint(
            self.m_btn_set_tgt_crs,
            "Выбрать целевую систему координат (по умолчанию WGS 84)"
        )
        self._bind_statusbar_hint(
            self.m_spin_bad_threshold,
            "Порог подсветки красным — невязки выше этого значения отмечаются как грубые"
        )
        self._bind_statusbar_hint(
            self.m_choice_bad_units,
            "Единицы порога: в метрах или кратно СКО по контрольным невязкам dE/dN/dU"
        )
        self._bind_statusbar_hint(
            self.m_rb_method,
            "EPSG:1033 Position Vector и EPSG:1032 Coordinate Frame — "
            "одни и те же параметры с инвертированными знаками вращения"
        )
        self._bind_statusbar_hint(
            self.m_rb_direction,
            "Направление параметров: прямое (исходная→целевая) или обратное"
        )

        self._bind_statusbar_hint(
            self.m_rb_src_action,
            "Если высоты ортометрические (или с натяжкой нормальные), ПРИБАВЛЯЙТЕ высоту геоида, чтобы получить геодезические высоты"
        )

        self._bind_statusbar_hint(
            self.m_rb_tgt_action,
            "Так как EGM2008 определён относительно WGS-84, если WGS-84 не задана как одна из СК, коррекция высот недоступна"
        )

    def _format_crs(self, fmt: str):
        return self.export_service.format_crs(fmt)


    def _save_crs_to_file(self, fmt: str):
        return self.export_service.save_crs_to_file(fmt)


    def _copy_crs_to_clipboard(self, fmt: str):
        return self.export_service.copy_crs_to_clipboard(fmt)
            
    def on_export_calibration(self, event):
        self.export_service.export_calibration_dialog()

    def on_about(self, event):
        from gui.dialogs.about_dialog import AboutDialog
        with AboutDialog(self) as dlg:
            dlg.ShowModal()

    def _format_coord_value(self, value: float, crs: CRS, is_height: bool = False) -> str:
        """
        Форматирование координат для автозаполнения таблицы.
        Для географических СК:
        - lon/lat: 8 знаков
        Для проецированных:
        - X/Y: 4 знака
        Для высоты:
        - 4 знака
        """
        return self.calc_service._format_coord_value(value, crs, is_height)

    
    def _autofill_missing_coordinates(self, raw_items, result, geoid_info) -> int:
        """
        Достраивает отсутствующую сторону координат у неполных строк.

        Правила:
        - если сторона ЗАДАНА пользователем, её H сначала переводится
        из табличной в расчётную (table_to_calc)
        - после трансформации H на ВЫЧИСЛЯЕМОЙ стороне переводится
        из расчётной в табличную (calc_to_table)
        - H ... скорр. заполняется для тех сторон, где action != NOTHING
        """
        src_action, tgt_action = self._read_geoid_actions()

        predictions, geo_src, geo_tgt = self.calc_service.prepare_autofill_payload(
            raw_items=raw_items,
            result=result,
            geoid_info=geoid_info,
            source_crs=self.source_crs,
            target_crs=self.target_crs,
            src_action=src_action,
            tgt_action=tgt_action,
        )

        filled = self.coord_grid.fill_missing_coordinates(predictions)
        if geo_src or geo_tgt:
            self.coord_grid.update_geoid_heights_partial(geo_src, geo_tgt)
        return filled

    def _is_row_usable_for_calculation(self, row: int, r: dict) -> bool:
        """
        Строка пригодна для расчёта, если:
        - есть координаты в обеих СК по плану (x1,y1,x2,y2),
        - строка не содержит автодостроенных координат.

        ВАЖНО:
        - даже если enabled_plan=False и enabled_h=False, строка всё равно
        включается в pairs (для вывода невязок XYZ/ENU),
        но не влияет на решение из-за нулевых весов в ядре.
        """
        has_both_xy = (
            bool(r.get("x1")) and bool(r.get("y1")) and
            bool(r.get("x2")) and bool(r.get("y2"))
        )
        not_computed = not self.coord_grid.row_has_computed_coordinates(row)
        return has_both_xy and not_computed
    
    def show_on_map(self, event=None):

        if self.calc_result is None:
            wx.MessageBox("Сначала выполните расчёт.", "Нет результата", wx.OK | wx.ICON_INFORMATION)
            return

        from gui.dialogs.map_dialog import MapDialog
        from gui.utils.map_points_builder import can_show_map, build_points_for_map

        # Здесь вы формируете списки уже в WGS84 lon/lat
        raw_items = self.coord_grid.get_data_with_row_indices()
        src_points, tgt_points = build_points_for_map(
            raw_items, self.source_crs, self.target_crs, self.calc_result
        )

        dlg = MapDialog(self)
        dlg.set_points(src_points, tgt_points, "Точки калибровки")
        dlg.ShowModal()
        dlg.Destroy()

    def _on_update_show_on_map_ui(self, event):
        from core.geoid_correction import crs_is_wgs84_related

        has_result = self.calc_result is not None
        src_ok = getattr(self, "source_crs", None) is not None and crs_is_wgs84_related(self.source_crs)
        tgt_ok = getattr(self, "target_crs", None) is not None and crs_is_wgs84_related(self.target_crs)

        event.Enable(has_result and (src_ok or tgt_ok))
    
    def on_parse_degrees(self, event):
        from gui.dialogs.parse_degrees_dialog import ParseDegreesDialog

        # Собираем данные для превью (только строки, где есть хоть что-то)
        rows_payload = []
        for row in range(self.coord_grid.GetNumberRows()):
            y1 = self.coord_grid.GetCellValue(row, 4).strip()  # _Col.Y1
            x1 = self.coord_grid.GetCellValue(row, 3).strip()  # _Col.X1
            y2 = self.coord_grid.GetCellValue(row, 8).strip()  # _Col.Y2
            x2 = self.coord_grid.GetCellValue(row, 7).strip()  # _Col.X2
            if not (y1 or x1 or y2 or x2):
                continue
            rows_payload.append({
                "grid_row": row,
                "name": self.coord_grid.GetCellValue(row, 2).strip(),  # _Col.NAME
                "y1": y1, "x1": x1, "y2": y2, "x2": x2,
            })

        if not rows_payload:
            wx.MessageBox("Нет данных для парсинга.", "Информация", wx.OK | wx.ICON_INFORMATION)
            return

        with ParseDegreesDialog(self, rows_payload) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            updates = dlg.get_updates()

        if not updates:
            return

        key_to_col = {"y1": 4, "x1": 3, "y2": 8, "x2": 7}
        self.coord_grid.begin_batch()
        try:
            for (grid_row, key), new_val in updates.items():
                self.coord_grid.SetCellValue(grid_row, key_to_col[key], new_val)
        finally:
            self.coord_grid.end_batch(notify=False)

        self.coord_grid.ForceRefresh()

        self._mark_modified("parse_degrees")
        self._set_result_text("")
        self.coord_grid.clear_residuals()

    def _build_geoid_notes(self) -> tuple[str, str, str]:
        src_action, tgt_action = self._read_geoid_actions()
        return self.calc_service.build_geoid_notes(
            getattr(self, "source_crs", None),
            getattr(self, "target_crs", None),
            src_action,
            tgt_action,
        )
    
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
    
    def on_row_move_up(self, event):
        self.coord_grid.move_selected_rows_up()

    def on_row_move_down(self, event):
        self.coord_grid.move_selected_rows_down()