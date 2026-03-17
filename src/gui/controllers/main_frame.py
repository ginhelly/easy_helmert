import wx
from typing import Dict, List, Optional
from pyproj import CRS

from core.models import *
from gui.forms.easy_helmert_base import BaseMainFrame
from gui.widgets.coordinate_grid import CoordinateGrid
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
        self.is_modified = False

        self._init_ui()
        self._setup_layout()
        self._bind_events()
        self._setup_toolbar_icons()
        wx.CallAfter(self.adjust_menu_icons)
        self._bind_hints()

        self.Centre()
        self.Show()

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
        self.Bind(wx.EVT_BUTTON, self.on_calculate,  self.m_btn_calc)

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
        self.m_spin_bad_threshold.Bind(wx.EVT_TEXT_ENTER, self._on_threshold_changed)

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
        self.is_modified = True
        self._set_result_text("")
        # clear_residuals через CallAfter — чтобы не ломать текущую операцию грида
        wx.CallAfter(self.coord_grid.clear_residuals)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def on_add_row(self, event):
        self.coord_grid.add_row()

    def on_del_row(self, event):
        self.coord_grid.delete_selected_rows()

    def on_swap_src(self, event):
        self.coord_grid.swap_source_xy()
        self.is_modified = True

    def on_swap_dst(self, event):
        self.coord_grid.swap_target_xy()
        self.is_modified = True

    def on_calculate(self, event):
        raw = self.coord_grid.get_data()

        valid_raw = [
            r for r in raw
            if r.get("x1") and r.get("y1")
            and r.get("x2") and r.get("y2")
        ]

        # Считаем уравнения здесь же, чтобы показать понятную ошибку до вызова ядра
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
            )
            return

        if not getattr(self, "source_crs", None):
            wx.MessageBox("Задайте исходную систему координат.",
                        "Нет исходной СК", wx.OK | wx.ICON_WARNING)
            return

        if not getattr(self, "target_crs", None):
            wx.MessageBox("Задайте целевую систему координат.",
                        "Нет целевой СК", wx.OK | wx.ICON_WARNING)
            return

        # Предупреждение о малом числе точек (решение есть, но невязки неинформативны)
        if n_eq < 12:
            if wx.MessageBox(
                f"Доступно уравнений: {n_eq} (рекомендуется ≥ 12).\n"
                "Невязки по активным точкам будут близки к нулю.\n\n"
                "Продолжить?",
                "Мало данных",
                wx.YES_NO | wx.ICON_QUESTION,
            ) != wx.YES:
                return

        try:
            pairs = [
                PointPair(
                    name         = r["name"],
                    x1           = float(r["x1"]),
                    y1           = float(r["y1"]),
                    h1           = float(r["h1"]) if r.get("h1") else None,
                    x2           = float(r["x2"]),
                    y2           = float(r["y2"]),
                    h2           = float(r["h2"]) if r.get("h2") else None,
                    enabled_plan = r["enabled_plan"],
                    enabled_h    = r["enabled_h"],
                )
                for r in valid_raw
            ]
        except ValueError as e:
            wx.MessageBox(f"Ошибка в данных таблицы:\n{e}",
                        "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        from core.transformation import calculate_helmert
        from core.geoid_correction import (
            calculate_helmert_with_geoid, geoid_needed,
        )
        src_action, tgt_action = self._read_geoid_actions()
        apply_correction = (
            self.m_chk_correction.IsEnabled()
            and self.m_chk_correction.GetValue()
        )
        try:
            if geoid_needed(src_action, tgt_action):
                result, geoid_info = calculate_helmert_with_geoid(
                    pairs, self.source_crs, self.target_crs,
                    src_action, tgt_action,
                    apply_correction=apply_correction,
                )
                all_geoid_src = [None] * len(raw)
                all_geoid_tgt = [None] * len(raw)
                j = 0
                for i, r in enumerate(raw):
                    if r.get("x1") and r.get("y1") and r.get("x2") and r.get("y2"):
                        all_geoid_src[i] = geoid_info.src[j]
                        all_geoid_tgt[i] = geoid_info.tgt[j]
                        j += 1
                self.coord_grid.update_geoid_heights(all_geoid_src, all_geoid_tgt)
                self._last_delta_zeta_mean = geoid_info.delta_zeta_mean
            else:
                result = calculate_helmert(pairs, self.source_crs, self.target_crs)
                self.coord_grid.clear_geoid_heights()
                self._last_delta_zeta_mean = None
        except FileNotFoundError as e:
            wx.MessageBox(
                f"Файл геоида не найден:\n{e}\n\n"
                "Убедитесь, что egm08_25.gtx или us_nga_egm2008_1.tif "
                "присутствует в папке resources/",
                "Геоид не найден", wx.OK | wx.ICON_ERROR,
            )
            return
        except Exception as e:
            wx.MessageBox(f"Ошибка расчёта:\n{e}", "Ошибка", wx.OK | wx.ICON_ERROR)
            return

        self.calc_result = result
        self.point_pairs = pairs

        # Разворачиваем невязки на все строки таблицы
        # valid_raw и result.residuals имеют одинаковую длину
        all_residuals = [None] * len(raw)
        j = 0
        for i, r in enumerate(raw):
            if r.get("x1") and r.get("y1") and r.get("x2") and r.get("y2"):
                all_residuals[i] = result.residuals[j]
                j += 1

        self.update_results(result)
        
        # Метрические невязки dE / dN / dU
        # ENU-невязки уже в result.residuals_enu
        all_metric = [None] * len(raw)
        j = 0
        for i, r in enumerate(raw):
            if r.get("x1") and r.get("y1") and r.get("x2") and r.get("y2"):
                all_metric[i] = result.residuals_enu[j]
                j += 1
        
        threshold = self._get_threshold_m()

        self._last_all_residuals = all_residuals
        self.coord_grid.update_residuals(all_residuals, threshold=threshold)

        self._last_all_metric = all_metric
        self.coord_grid.update_metric_residuals(all_metric, threshold=threshold)
    
    def _read_display_settings(self) -> DisplaySettings:
        return DisplaySettings(
            method        = HelmertMethod(self.m_rb_method.GetSelection()),
            direction     = HelmertDirection(self.m_rb_direction.GetSelection()),
            rotation_unit = RotationUnit(self.m_choice_rotation_units.GetSelection()),
            scale_unit    = ScaleUnit(self.m_choice_scale_units.GetSelection()),
            source_name   = self._src_crs_name(),
            target_name   = self._tgt_crs_name(),
            rms_metric_m  = self._rms_from_grid(),
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

    def _on_display_settings_changed(self, event):
        if self.calc_result is not None:
            self.update_results(self.calc_result)
        event.Skip()

    def update_results(self, result: CalculationResult):
        display = result.params.as_display(self._read_display_settings())
        text    = display.to_text()

        dz = getattr(self, "_last_delta_zeta_mean", None)
        if dz is not None:
            text += (
                f"\n\n"
                f"  Δζ (Балтика − EGM2008) = {dz:+.4f} м  "
                f"({dz * 100:+.2f} см)"
            )

        self._set_result_text(text)
        self.is_modified = False

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
        """Сохраняет таблицу координат в CSV-файл."""
        data = self.coord_grid.get_data()
        if not data:
            wx.MessageBox("Таблица пуста — нечего сохранять.",
                        "Нет данных", wx.OK | wx.ICON_INFORMATION)
            return

        with wx.FileDialog(
            self,
            "Сохранить таблицу точек",
            wildcard=(
                "CSV файл (*.csv)|*.csv"
                "|Текстовый файл (*.txt)|*.txt"
                "|Все файлы (*.*)|*.*"
            ),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            dlg.SetFilename("points.csv")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()

        # Определяем разделитель по расширению
        ext = path.rsplit(".", 1)[-1].lower()
        sep = ";" if ext == "csv" else "\t"

        src_name = self._src_crs_name()
        tgt_name = self._tgt_crs_name()

        header = sep.join([
            "Включён (план)",
            "Включён (высота)",
            "Имя",
            f"Восток исх. ({src_name})",
            f"Север исх. ({src_name})",
            f"Высота исх. ({src_name})",
            f"Восток опорн. ({tgt_name})",
            f"Север опорн. ({tgt_name})",
            f"Высота опорн. ({tgt_name})",
        ])

        rows = [header]
        for d in data:
            row = sep.join([
                "1" if d.get("enabled_plan") else "0",
                "1" if d.get("enabled_h")    else "0",
                str(d.get("name", "")),
                str(d.get("x1",   "")),
                str(d.get("y1",   "")),
                str(d.get("h1",   "")),
                str(d.get("x2",   "")),
                str(d.get("y2",   "")),
                str(d.get("h2",   "")),
            ])
            rows.append(row)

        try:
            with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
                # utf-8-sig добавляет BOM — Excel открывает без вопросов
                f.write("\n".join(rows))
        except IOError as e:
            wx.MessageBox(str(e), "Ошибка записи", wx.OK | wx.ICON_ERROR)

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
            "Пересчитать высоты относительно геоида": "calculate_heights_icon"
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
        """
        Если данные изменены, спрашивает пользователя о сохранении.

        Возвращает:
            True  — можно продолжать (данные не менялись, либо сохранены,
                    либо пользователь выбрал «Не сохранять»).
            False — пользователь нажал «Отмена», операцию надо прервать.

        Использование::

            def on_something(self, event):
                if not self._ask_save_if_modified():
                    return          # пользователь передумал
                ... # выполняем действие
        """
        if not self.is_modified:
            return True

        # Проверяем, есть ли вообще что сохранять
        if not self.coord_grid.get_data():# not self.point_pairs and not self.coord_grid.get_data():
            return True

        dlg = wx.MessageDialog(
            self,
            "Данные были изменены.\nСохранить перед продолжением?",
            "Несохранённые изменения",
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_YES:
            self._save_table_to_file(None)
            return True
        if result == wx.ID_NO:
            return True
        return False   # wx.ID_CANCEL — прерываем операцию

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
        self.is_modified  = False
        self._last_all_residuals = []
        self._last_all_metric    = []
        self._last_delta_zeta_mean = None

        # Очищаем панель результатов
        self._set_result_text("")

    def on_import_txt(self, event):
        """Импорт координат из текстового файла — добавление и обновление точек."""
        with wx.FileDialog(
            self,
            "Открыть файл с координатами",
            wildcard=(
                "Текстовые файлы (*.txt;*.csv;*.tsv)|*.txt;*.csv;*.tsv"
                "|Все файлы (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dlg:
            if file_dlg.ShowModal() == wx.ID_CANCEL:
                return
            filepath = file_dlg.GetPath()

        from gui.dialogs.import_dialog import ImportDialog
        with ImportDialog(self, filepath) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            imported = dlg.get_import_data()

        if not imported:
            wx.MessageBox(
                "Нет данных для импорта — возможно, не назначен ни один столбец\n"
                "или файл пустой.",
                "Импорт",
                wx.OK | wx.ICON_INFORMATION,
            )
            return

        n_added, n_updated = self._merge_imported_data(imported)

        self.is_modified = True
        self.coord_grid.clear_residuals()
        self._set_result_text("")

        wx.MessageBox(
            f"Импорт завершён:\n"
            f"  • обновлено точек: {n_updated}\n"
            f"  • добавлено точек: {n_added}",
            "Импорт завершён",
            wx.OK | wx.ICON_INFORMATION,
        )

    def _merge_imported_data(self, imported: List[dict]) -> tuple[int, int]:
        """
        Сливает импортированные строки с текущим содержимым таблицы.

        Правила слияния:
        - Ключ совпадения — поле «name».
        - Обновляются только непустые поля из импорта.
        - Флаги enabled_plan / enabled_h обновляются, если присутствуют в импорте
            (текстовый импорт через ImportDialog их не содержит — там они не трогаются).
        - Если несколько строк с одним именем — обновляются все.
        - Новые точки добавляются в конец.
        - Минимум MIN_ROWS строк гарантирует coord_grid.set_data().
        """
        _COORD_KEYS = ("x1", "y1", "h1", "x2", "y2", "h2")
        _FLAG_KEYS  = ("enabled_plan", "enabled_h")

        current: List[dict] = self.coord_grid.get_data()

        name_idx: Dict[str, List[int]] = {}
        for i, row in enumerate(current):
            name = row.get("name", "").strip()
            if name:
                name_idx.setdefault(name, []).append(i)

        n_added, n_updated = 0, 0
        new_rows: List[dict] = []

        for imp in imported:
            imp_name = imp.get("name", "").strip()
            if not imp_name:
                continue

            if imp_name in name_idx:
                for idx in name_idx[imp_name]:
                    # Обновляем координатные поля (только непустые)
                    for key in _COORD_KEYS:
                        val = imp.get(key, "")
                        if val:
                            current[idx][key] = val
                    # Обновляем флаги включения (только если явно заданы в импорте)
                    for flag in _FLAG_KEYS:
                        if flag in imp:
                            current[idx][flag] = imp[flag]
                n_updated += 1
            else:
                blank: dict = {
                    "enabled_plan": imp.get("enabled_plan", True),
                    "enabled_h":    imp.get("enabled_h",    True),
                    "name": imp_name,
                    "x1": "", "y1": "", "h1": "",
                    "x2": "", "y2": "", "h2": "",
                }
                for key in _COORD_KEYS:
                    if imp.get(key):
                        blank[key] = imp[key]
                name_idx[imp_name] = [len(current) + len(new_rows)]
                new_rows.append(blank)
                n_added += 1

        self.coord_grid.set_data(current + new_rows)
        return n_added, n_updated
    
    def on_import_calibration(self, event):
        """Импорт файла калибровки геодезического контроллера."""
        from core.calibration_importers import (
            load_calibration_file, UnsupportedFormatError, WILDCARD
        )

        with wx.FileDialog(
            self,
            "Открыть файл калибровки",
            wildcard=WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            filepath = dlg.GetPath()

        try:
            points = load_calibration_file(filepath)
        except UnsupportedFormatError as e:
            wx.MessageBox(str(e), "Неподдерживаемый формат",
                        wx.OK | wx.ICON_WARNING, self)
            return
        except (ValueError, IOError) as e:
            wx.MessageBox(str(e), "Ошибка импорта",
                        wx.OK | wx.ICON_ERROR, self)
            return

        imported = [pt.to_dict() for pt in points]
        n_added, n_updated = self._merge_imported_data(imported)

        self.is_modified = True
        self.coord_grid.clear_residuals()
        self._set_result_text("")

        wx.MessageBox(
            f"Импорт завершён:\n"
            f"  • обновлено точек: {n_updated}\n"
            f"  • добавлено точек: {n_added}",
            "Импорт калибровки",
            wx.OK | wx.ICON_INFORMATION,
        )
    
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

    def _format_crs(self, fmt: str) -> Optional[str]:
        if self.calc_result is None or self.source_crs is None:
            wx.MessageBox("Сначала выполните расчёт.",
                        "Нет результата", wx.OK | wx.ICON_INFORMATION)
            return None

        display_name = getattr(self, '_source_crs_label', '') or ''

        from utils.crs_export import to_wkt1, to_wkt2, to_proj4
        try:
            if fmt == "wkt1":
                return to_wkt1(self.source_crs, self.calc_result.params, display_name)
            elif fmt == "wkt2":
                return to_wkt2(self.source_crs, self.calc_result.params, display_name, self.target_crs)
            elif fmt == "proj4":
                return to_proj4(self.source_crs, self.calc_result.params)
        except Exception as e:
            wx.MessageBox(f"Не удалось сформировать {fmt.upper()}:\n{e}",
                        "Ошибка", wx.OK | wx.ICON_ERROR)
        return None


    def _save_crs_to_file(self, fmt: str):
        text = self._format_crs(fmt)
        if text is None:
            return

        if fmt in ("wkt1", "wkt2"):
            wildcard = (
                "PRJ файл (*.prj)|*.prj"
                "|WKT файл (*.wkt)|*.wkt"
                "|Текстовый файл (*.txt)|*.txt"
                "|Все файлы (*.*)|*.*"
            )
        else:
            wildcard = (
                "PRJ файл (*.prj)|*.prj"
                "|Текстовый файл (*.txt)|*.txt"
                "|Все файлы (*.*)|*.*"
            )

        with wx.FileDialog(
            self, f"Сохранить {fmt.upper()}",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            dlg.SetFilename(f"result.prj")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
        except IOError as e:
            wx.MessageBox(str(e), "Ошибка записи", wx.OK | wx.ICON_ERROR)


    def _copy_crs_to_clipboard(self, fmt: str):
        text = self._format_crs(fmt)
        if text is None:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.MessageBox(f"Описание проекции в формате {fmt} скопировано в буфер обмена",
                        "Копирование успешно", wx.OK | wx.ICON_ASTERISK)
            finally:
                wx.TheClipboard.Close()
            
    def on_export_calibration(self, event):
        """Экспорт текущей таблицы в файл калибровки."""
        from core.calibration_importers import (
            save_calibration_file, export_wildcard,
            UnsupportedFormatError, CalibrationPoint,
        )

        data = self.coord_grid.get_data()
        if not data:
            wx.MessageBox("Таблица пуста.", "Нет данных", wx.OK | wx.ICON_INFORMATION)
            return

        with wx.FileDialog(
            self, "Экспорт файла калибровки",
            wildcard=export_wildcard(),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            dlg.SetFilename("calibration.loc")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            filepath = dlg.GetPath()

        points = [
            CalibrationPoint(
                name         = d.get("name", ""),
                x1           = d.get("x1",   ""),
                y1           = d.get("y1",   ""),
                h1           = d.get("h1",   ""),
                x2           = d.get("x2",   ""),
                y2           = d.get("y2",   ""),
                h2           = d.get("h2",   ""),
                enabled_plan = d.get("enabled_plan", True),
                enabled_h    = d.get("enabled_h",    True),
            )
            for d in data
        ]

        try:
            save_calibration_file(filepath, points)
        except (UnsupportedFormatError, IOError, ValueError) as e:
            wx.MessageBox(str(e), "Ошибка экспорта", wx.OK | wx.ICON_ERROR)

    def on_about(self, event):
        from gui.dialogs.about_dialog import AboutDialog
        with AboutDialog(self) as dlg:
            dlg.ShowModal()