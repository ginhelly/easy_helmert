import threading
import wx
import wx.grid
from typing import List, Optional

from core.models import PointPair
from core.optimizer import optimize_combinations, OptimizationResult


class OptimizeDialog(wx.Dialog):
    def __init__(self, parent, pairs, source_crs, target_crs,
                 src_action, tgt_action, apply_correction):
        super().__init__(parent, title="Поиск оптимального набора точек",
                         size=(900, 700),
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.pairs = pairs
        self.source_crs = source_crs
        self.target_crs = target_crs
        self.src_action = src_action
        self.tgt_action = tgt_action
        self.apply_correction = apply_correction

        self.result: Optional[OptimizationResult] = None
        self._optimizer_thread: Optional[threading.Thread] = None

        # Возвращаемые маски после Apply
        self.applied_plan: Optional[List[bool]] = None
        self.applied_height: Optional[List[bool]] = None

        self._init_ui()
        self._fill_grid()
        self.Layout()
        self.Centre()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self):
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        # Режим
        mode_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Режим оптимизации"), wx.HORIZONTAL)
        self.rb_full = wx.RadioButton(self, label="Полное исключение (план и высота вместе)", style=wx.RB_GROUP)
        self.rb_split = wx.RadioButton(self, label="Раздельное исключение плана и высоты")
        self.rb_full.SetValue(True)
        mode_box.Add(self.rb_full, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        mode_box.Add(self.rb_split, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)
        main_sizer.Add(mode_box, 0, wx.EXPAND | wx.ALL, 5)

        # Метод
        method_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Метод"), wx.HORIZONTAL)
        self.rb_auto = wx.RadioButton(self, label="Авто (≤8 точек — перебор, иначе жадный)", style=wx.RB_GROUP)
        self.rb_exhaustive = wx.RadioButton(self, label="Полный перебор")
        self.rb_greedy = wx.RadioButton(self, label="Жадный")
        self.rb_auto.SetValue(True)
        method_box.Add(self.rb_auto, 0, wx.ALL, 5)
        method_box.Add(self.rb_exhaustive, 0, wx.ALL, 5)
        method_box.Add(self.rb_greedy, 0, wx.ALL, 5)
        main_sizer.Add(method_box, 0, wx.EXPAND | wx.ALL, 5)

        # Параметры
        param_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Параметры"), wx.HORIZONTAL)
        param_box.Add(wx.StaticText(self, label="Макс. исключаемых точек:"),
                      0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 5)
        self.spin_max_excluded = wx.SpinCtrl(self, value="4", min=1, max=10)
        param_box.Add(self.spin_max_excluded, 0)
        main_sizer.Add(param_box, 0, wx.EXPAND | wx.ALL, 5)

        # Таблица
        self.grid = wx.grid.Grid(self, style=wx.BORDER_SUNKEN)
        self.grid.CreateGrid(len(self.pairs), 6)
        for col, label in enumerate(["Имя", "План", "Высота", "dE (м)", "dN (м)", "dU (м)"]):
            self.grid.SetColLabelValue(col, label)
        for col in (1, 2):
            self.grid.SetColFormatBool(col)
        for col in (3, 4, 5):
            attr = wx.grid.GridCellAttr()
            attr.SetReadOnly(True)
            self.grid.SetColAttr(col, attr)
        self.grid.Bind(wx.grid.EVT_GRID_CELL_LEFT_CLICK, self._on_cell_click)
        main_sizer.Add(self.grid, 1, wx.EXPAND | wx.ALL, 5)

        # Результаты
        result_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Результат"), wx.VERTICAL)
        self.result_text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, size=(-1, 120))
        result_box.Add(self.result_text, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(result_box, 0, wx.EXPAND | wx.ALL, 5)

        # Прогресс
        progress_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Прогресс"), wx.VERTICAL)
        self.progress_label = wx.StaticText(self, label="")
        self.progress = wx.Gauge(self, range=1000, style=wx.GA_HORIZONTAL | wx.GA_SMOOTH)
        progress_box.Add(self.progress_label, 0, wx.LEFT, 5)
        progress_box.Add(self.progress, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(progress_box, 0, wx.EXPAND | wx.ALL, 5)

        # Кнопки
        btn_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.calc_btn = wx.Button(self, label="Рассчитать")
        self.calc_btn.Bind(wx.EVT_BUTTON, self._on_calculate)
        self.apply_btn = wx.Button(self, label="Применить")
        self.apply_btn.Bind(wx.EVT_BUTTON, self._on_apply)
        self.apply_btn.Disable()
        self.cancel_btn = wx.Button(self, label="Отмена")
        self.cancel_btn.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CANCEL))
        btn_sizer.Add(self.calc_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.apply_btn, 0, wx.ALL, 5)
        btn_sizer.Add(self.cancel_btn, 0, wx.ALL, 5)
        main_sizer.Add(btn_sizer, 0, wx.ALIGN_CENTER_HORIZONTAL | wx.ALL, 5)

        self.SetSizer(main_sizer)

    # ------------------------------------------------------------------
    # Заполнение таблицы
    # ------------------------------------------------------------------

    def _fill_grid(self):
        for i, p in enumerate(self.pairs):
            self.grid.SetCellValue(i, 0, p.name)
            self.grid.SetCellValue(i, 1, "1" if p.enabled_plan else "0")
            self.grid.SetCellValue(i, 2, "1" if p.enabled_h else "0")
            for col in (3, 4, 5):
                self.grid.SetCellValue(i, col, "")
        self.grid.AutoSizeColumns()

    def _on_cell_click(self, evt):
        row, col = evt.GetRow(), evt.GetCol()
        if col in (1, 2):
            val = self.grid.GetCellValue(row, col)
            self.grid.SetCellValue(row, col, "0" if val == "1" else "1")
        evt.Skip()

    def _get_current_masks(self):
        """Возвращает (plan_mask, h_mask) из текущего состояния таблицы."""
        plan, height = [], []
        for i in range(self.grid.GetNumberRows()):
            plan.append(self.grid.GetCellValue(i, 1) == "1")
            height.append(self.grid.GetCellValue(i, 2) == "1")
        return plan, height

    # ------------------------------------------------------------------
    # Расчёт
    # ------------------------------------------------------------------

    def _on_calculate(self, _evt):
        if self._optimizer_thread and self._optimizer_thread.is_alive():
            return

        split_mode = self.rb_split.GetValue()
        if self.rb_auto.GetValue():
            method = 'auto'
        elif self.rb_exhaustive.GetValue():
            method = 'exhaustive'
        else:
            method = 'greedy'
        max_excluded = self.spin_max_excluded.GetValue()

        self.calc_btn.Disable()
        self.apply_btn.Disable()
        self.progress.SetValue(0)
        self.progress_label.SetLabel("Выполняется расчёт…")
        self.result_text.SetValue("")

        def progress_callback(current, total):
            # Вызывается из фонового потока — передаём в GUI через CallAfter
            pct = int(current / total * 1000) if total > 0 else 0
            label = f"Шаг {current} из {total}"
            wx.CallAfter(self._update_progress, pct, label)

        def run():
            try:
                results = optimize_combinations(
                    self.pairs,
                    self.source_crs,
                    self.target_crs,
                    split_mode=split_mode,
                    src_action=self.src_action,
                    tgt_action=self.tgt_action,
                    apply_correction=self.apply_correction,
                    method=method,
                    max_excluded=max_excluded,
                    progress_callback=progress_callback,
                )
                wx.CallAfter(self._on_done, results, None)
            except Exception as e:
                wx.CallAfter(self._on_done, None, e)

        self._optimizer_thread = threading.Thread(target=run, daemon=True)
        self._optimizer_thread.start()

    def _update_progress(self, pct: int, label: str):
        self.progress.SetValue(pct)
        self.progress_label.SetLabel(label)

    def _on_done(self, results, error):
        self.calc_btn.Enable()
        self.progress.SetValue(1000)

        if error is not None:
            self.progress_label.SetLabel("Ошибка")
            wx.MessageBox(f"Ошибка оптимизации:\n{error}", "Ошибка",
                          wx.OK | wx.ICON_ERROR, self)
            return

        if not results:
            self.progress_label.SetLabel("Нет допустимых результатов")
            wx.MessageBox("Не удалось найти допустимый набор точек.",
                          "Ошибка", wx.OK | wx.ICON_ERROR, self)
            return

        best = results[0]
        self.result = best
        self.progress_label.SetLabel("Готово")

        split_mode = self.rb_split.GetValue()
        if split_mode:
            for i, (plan, h) in enumerate(zip(best.enabled_plan_mask, best.enabled_h_mask)):
                self.grid.SetCellValue(i, 1, "1" if plan else "0")
                self.grid.SetCellValue(i, 2, "1" if h else "0")
        else:
            for i, inc in enumerate(best.included_mask):
                self.grid.SetCellValue(i, 1, "1" if inc else "0")
                self.grid.SetCellValue(i, 2, "1" if inc else "0")

        self._update_grid_residuals(best)
        self._update_result_text(best)
        self.apply_btn.Enable()

    # ------------------------------------------------------------------
    # Отображение результатов
    # ------------------------------------------------------------------

    def _update_grid_residuals(self, result: OptimizationResult):
        if not result.residuals_enu:
            return
        for i, (de, dn, du) in enumerate(result.residuals_enu):
            self.grid.SetCellValue(i, 3, f"{de:.4f}")
            self.grid.SetCellValue(i, 4, f"{dn:.4f}")
            self.grid.SetCellValue(i, 5, f"{du:.4f}")
        self.grid.AutoSizeColumns()

    def _update_result_text(self, result: OptimizationResult):
        if not result.params:
            self.result_text.SetValue("Ошибка расчёта")
            return
        included = (sum(result.included_mask) if result.included_mask
                    else None)
        plan_on = (sum(result.enabled_plan_mask) if result.enabled_plan_mask
                   else None)
        h_on = (sum(result.enabled_h_mask) if result.enabled_h_mask
                else None)

        lines = [f"RMSE: {result.rms_error:.5f} м", f"Уравнений: {result.equations}"]
        if included is not None:
            lines.append(f"Включено точек: {included} из {len(self.pairs)}")
        else:
            lines.append(f"План: {plan_on} из {len(self.pairs)},  "
                         f"Высота: {h_on} из {len(self.pairs)}")
        self.result_text.SetValue("\n".join(lines))

    # ------------------------------------------------------------------
    # Применить
    # ------------------------------------------------------------------

    def _on_apply(self, _evt):
        self.applied_plan, self.applied_height = self._get_current_masks()
        self.EndModal(wx.ID_OK)
