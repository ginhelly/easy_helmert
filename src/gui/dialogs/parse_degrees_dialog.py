from __future__ import annotations

import wx
import wx.grid as gridlib

from gui.utils.degrees_parser import DegreesParseMode, parse_value


class ParseDegreesDialog(wx.Dialog):
    COL_ENABLED = 0
    DATA_COLS = [
        ("Север исх.", "y1"),
        ("Восток исх.", "x1"),
        ("Север опорн.", "y2"),
        ("Восток опорн.", "x2"),
    ]

    def __init__(self, parent, rows_payload: list[dict]):
        super().__init__(
            parent,
            title="Парсинг форматов градусов",
            size=(1250, 760),
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.rows_payload = rows_payload
        self._updates: dict[tuple[int, str], str] = {}
        self._busy = False

        # активность строки по index rows_payload
        self._row_enabled = [True] * len(self.rows_payload)

        root = wx.BoxSizer(wx.VERTICAL)

        self.rb_mode = wx.RadioBox(
            self,
            label="Режим парсинга",
            choices=[
                "1) DD.MMmmmm -> десятичные градусы",
                "2) DD.MMSSss -> десятичные градусы",
                "3) Обратная: десятичные градусы -> DD.MMmmmm",
                "4) Обратная: десятичные градусы -> DD.MMSSss",
            ],
            majorDimension=1,
            style=wx.RA_SPECIFY_COLS,
        )
        self.rb_mode.SetSelection(1)  # дефолт: DMS -> DD
        root.Add(self.rb_mode, 0, wx.ALL | wx.EXPAND, 8)

        top = wx.BoxSizer(wx.HORIZONTAL)

        self.chk_all_rows = wx.CheckBox(
            self,
            label="Задействовать все строки",
            style=wx.CHK_3STATE,  # третье состояние ставим программно
        )
        self.chk_all_rows.Set3StateValue(wx.CHK_CHECKED)
        top.Add(self.chk_all_rows, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        top.AddStretchSpacer(1)

        self.chk_cols: dict[str, wx.CheckBox] = {}
        for lbl, key in self.DATA_COLS:
            c = wx.CheckBox(self, label=f"Парсить: {lbl}")
            c.SetValue(False)
            self.chk_cols[key] = c
            top.Add(c, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        root.Add(top, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM | wx.EXPAND, 6)

        self.grid = gridlib.Grid(self)
        self.grid.CreateGrid(len(self.rows_payload), 1 + len(self.DATA_COLS))
        self.grid.SetColLabelValue(self.COL_ENABLED, "✓")
        self.grid.SetColSize(self.COL_ENABLED, 40)

        for i, (lbl, _) in enumerate(self.DATA_COLS, start=1):
            self.grid.SetColLabelValue(i, lbl)

        self.grid.SetRowLabelSize(170)
        self.grid.EnableEditing(False)

        # чекбокс-рендер в первой колонке
        for r in range(self.grid.GetNumberRows()):
            self.grid.SetCellRenderer(r, self.COL_ENABLED, gridlib.GridCellBoolRenderer())
            self.grid.SetCellEditor(r, self.COL_ENABLED, gridlib.GridCellBoolEditor())
            self.grid.SetCellAlignment(r, self.COL_ENABLED, wx.ALIGN_CENTER, wx.ALIGN_CENTER)
            self.grid.SetCellValue(r, self.COL_ENABLED, "1")

        root.Add(self.grid, 1, wx.ALL | wx.EXPAND, 8)

        btns = wx.StdDialogButtonSizer()
        self.btn_apply = wx.Button(self, wx.ID_OK, "Применить")
        self.btn_cancel = wx.Button(self, wx.ID_CANCEL, "Отмена")
        btns.AddButton(self.btn_apply)
        btns.AddButton(self.btn_cancel)
        btns.Realize()
        root.Add(btns, 0, wx.ALL | wx.ALIGN_RIGHT, 8)

        self.SetSizer(root)

        # bind
        self.rb_mode.Bind(wx.EVT_RADIOBOX, self._on_any_change)
        self.chk_all_rows.Bind(wx.EVT_CHECKBOX, self._on_toggle_all_rows)

        for c in self.chk_cols.values():
            c.Bind(wx.EVT_CHECKBOX, self._on_any_change)

        self.grid.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self._on_grid_left_click)
        self.grid.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK, self._on_grid_right_click)
        self.grid.Bind(gridlib.EVT_GRID_LABEL_RIGHT_CLICK, self._on_grid_right_click)

        self._refresh_preview()

    # ---------- selection helpers ----------

    def _get_selected_rows(self) -> list[int]:
        rows = set(self.grid.GetSelectedRows())

        tl = self.grid.GetSelectionBlockTopLeft()
        br = self.grid.GetSelectionBlockBottomRight()
        if tl and br:
            for i in range(len(tl)):
                for r in range(tl[i].GetRow(), br[i].GetRow() + 1):
                    rows.add(r)

        for cell in self.grid.GetSelectedCells():
            rows.add(cell.GetRow())

        if not rows:
            cur = self.grid.GetGridCursorRow()
            if cur >= 0:
                rows.add(cur)

        return sorted(rows)

    def _set_rows_enabled(self, rows: list[int], enabled: bool):
        for r in rows:
            if 0 <= r < len(self._row_enabled):
                self._row_enabled[r] = enabled
                self.grid.SetCellValue(r, self.COL_ENABLED, "1" if enabled else "")
        self._sync_master_checkbox()
        self._refresh_preview()

    # ---------- events ----------

    def _on_any_change(self, event):
        self._refresh_preview()
        event.Skip()

    def _on_toggle_all_rows(self, event):
        if self._busy:
            return
        st = self.chk_all_rows.Get3StateValue()
        # Пользовательский клик: трактуем так
        # checked -> все вкл
        # unchecked/undetermined -> все выкл
        enable_all = (st == wx.CHK_CHECKED)
        self._set_rows_enabled(list(range(len(self._row_enabled))), enable_all)

    def _on_grid_left_click(self, event):
        r, c = event.GetRow(), event.GetCol()
        if c == self.COL_ENABLED and r >= 0:
            self._row_enabled[r] = not self._row_enabled[r]
            self.grid.SetCellValue(r, c, "1" if self._row_enabled[r] else "")
            self._sync_master_checkbox()
            self._refresh_preview()
            return
        event.Skip()

    def _on_grid_right_click(self, event):
        rows = self._get_selected_rows()
        if not rows:
            return

        menu = wx.Menu()
        id_on = wx.NewIdRef()
        id_off = wx.NewIdRef()
        menu.Append(id_on, "Активировать выбранные строки")
        menu.Append(id_off, "Деактивировать выбранные строки")

        self.Bind(wx.EVT_MENU, lambda e: self._set_rows_enabled(rows, True), id=id_on)
        self.Bind(wx.EVT_MENU, lambda e: self._set_rows_enabled(rows, False), id=id_off)

        self.PopupMenu(menu)
        menu.Destroy()

    # ---------- core ----------

    def _sync_master_checkbox(self):
        total = len(self._row_enabled)
        checked = sum(1 for v in self._row_enabled if v)

        self._busy = True
        try:
            if checked == 0:
                self.chk_all_rows.Set3StateValue(wx.CHK_UNCHECKED)
            elif checked == total:
                self.chk_all_rows.Set3StateValue(wx.CHK_CHECKED)
            else:
                self.chk_all_rows.Set3StateValue(wx.CHK_UNDETERMINED)
        finally:
            self._busy = False

    def _refresh_preview(self):
        self._updates.clear()
        mode = DegreesParseMode(self.rb_mode.GetSelection())

        for r, row in enumerate(self.rows_payload):
            row_name = row.get("name", "").strip() or f"Строка {row['grid_row'] + 1}"
            self.grid.SetRowLabelValue(r, row_name)

            enabled_row = self._row_enabled[r]
            self.grid.SetCellValue(r, self.COL_ENABLED, "1" if enabled_row else "")

            for c, (_, key) in enumerate(self.DATA_COLS, start=1):
                raw = (row.get(key, "") or "").strip()
                self.grid.SetCellTextColour(r, c, wx.Colour(30, 30, 30))
                self.grid.SetCellBackgroundColour(r, c, wx.Colour(255, 255, 255))

                if not raw:
                    self.grid.SetCellValue(r, c, "")
                    continue

                # если строка/колонка не выбраны — просто показываем исходное
                if (not enabled_row) or (not self.chk_cols[key].GetValue()):
                    self.grid.SetCellValue(r, c, raw)
                    continue

                try:
                    new_val, preview = parse_value(raw, mode)
                    self.grid.SetCellValue(r, c, preview)
                    self._updates[(row["grid_row"], key)] = new_val
                except Exception:
                    self.grid.SetCellValue(r, c, f"{raw} -> [ошибка]")
                    self.grid.SetCellTextColour(r, c, wx.Colour(160, 0, 0))
                    self.grid.SetCellBackgroundColour(r, c, wx.Colour(255, 235, 235))

        # автоширина
        self.grid.AutoSizeColumns(False)
        self.grid.ForceRefresh()

    def get_updates(self) -> dict[tuple[int, str], str]:
        return dict(self._updates)