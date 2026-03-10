import wx
from typing import List, Optional

from core.models import PointPair, CalculationResult
from gui.forms.easy_helmert_base import BaseMainFrame
from gui.widgets.coordinate_grid import CoordinateGrid
from utils.xrc_loader import xrc


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

        self.Centre()
        self.Show()

    # ── UI init ───────────────────────────────────────────────────────────────

    def _init_ui(self):
        """Создание виджетов, которые нельзя/неудобно делать в FormBuilder."""

        # 1. Вставляем CoordinateGrid в placeholder-панель из FormBuilder
        self.coord_grid = CoordinateGrid(self.m_grid_placeholder)

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

        # Кнопки шапки таблицы
        self.Bind(wx.EVT_BUTTON, self.on_add_row,    self.m_btn_add_row)
        self.Bind(wx.EVT_BUTTON, self.on_del_row,    self.m_btn_del_row)
        self.Bind(wx.EVT_BUTTON, self.on_swap_src,   self.m_btn_swap_src)
        self.Bind(wx.EVT_BUTTON, self.on_swap_dst,   self.m_btn_swap_dst)
        self.Bind(wx.EVT_BUTTON, self.on_calculate,  self.m_btn_calc)

        # Кнопки результатов
        self.Bind(wx.EVT_BUTTON, self.on_copy_wkt,   self.m_btn_copy_wkt)
        self.Bind(wx.EVT_BUTTON, self.on_copy_proj4, self.m_btn_copy_proj4)
        self.Bind(wx.EVT_BUTTON, self.on_save_result,self.m_btn_save_result)

        # Отслеживаем изменение данных в таблице → сбрасываем невязки
        import wx.grid as gridlib
        self.coord_grid.Bind(
            gridlib.EVT_GRID_CELL_CHANGED,
            self._on_grid_changed
        )

    def _on_grid_changed(self, event):
        self.is_modified = True
        from gui.widgets.coordinate_grid import _Col, _READONLY_COLS
        if event.GetCol() not in _READONLY_COLS:
            self.coord_grid.clear_residuals()
            self._set_result_text("")
        event.Skip()

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
        """Запуск расчёта параметров Гельмерта."""
        raw = self.coord_grid.get_data()
        if len([r for r in raw if r["enabled"]]) < 4:
            wx.MessageBox(
                "Для 7-параметрического преобразования нужно минимум 4 точки.",
                "Недостаточно данных", wx.OK | wx.ICON_WARNING
            )
            return

        # Преобразуем в PointPair
        try:
            from core.models import PointPair
            pairs = [
                PointPair(
                    name    = r["name"],
                    x1      = float(r["x1"]),
                    y1      = float(r["y1"]),
                    x2      = float(r["x2"]),
                    y2      = float(r["y2"]),
                    enabled = r["enabled"],
                )
                for r in raw
            ]
        except ValueError as e:
            wx.MessageBox(
                f"Ошибка в данных таблицы:\n{e}",
                "Ошибка", wx.OK | wx.ICON_ERROR
            )
            return

        self.point_pairs = pairs

        # TODO: вызов core.transformation.calculate_helmert(pairs)
        # self.calc_result = calculate_helmert(pairs)
        # self.update_table(pairs, self.calc_result)
        # self.update_results(self.calc_result)
        wx.MessageBox("Расчёт: заглушка. Подключи core.transformation.", "Инфо")

    def on_copy_wkt(self, event):
        text = self.m_txt_result.GetValue()
        if not text:
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()

    def on_copy_proj4(self, event):
        # TODO: форматировать как Proj4 строку из self.calc_result
        wx.MessageBox("Proj4 экспорт: заглушка", "Инфо")

    def on_save_result(self, event):
        with wx.FileDialog(
            self, "Сохранить параметры",
            wildcard="WKT (*.wkt)|*.wkt|Proj4 (*.txt)|*.txt|Все файлы (*.*)|*.*",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.m_txt_result.GetValue())
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

    def update_results(self, result: CalculationResult):
        """Показать параметры преобразования в текстовом поле."""
        # TODO: форматировать result в текст (WKT / читаемый вид)
        self._set_result_text(str(result))
        self.is_modified = False

    def _set_result_text(self, text: str):
        self.m_txt_result.SetValue(text)

    # ── Toolbar / Menu icons (без изменений) ──────────────────────────────────

    def _setup_toolbar_icons(self):
        tool_icons = {"Импорт калибровки...": "import_icon"}
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

    def on_exit(self, event):
        if self.is_modified and self.point_pairs:
            dlg = wx.MessageDialog(
                self, "Данные изменены. Сохранить перед выходом?",
                "Выход", wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION
            )
            res = dlg.ShowModal()
            dlg.Destroy()
            if res == wx.ID_YES:
                self.on_save_result(None)
                self.Destroy()
            elif res == wx.ID_NO:
                self.Destroy()
        else:
            self.Destroy()