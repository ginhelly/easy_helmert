import wx
from typing import Dict, List, Optional

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

        # Кнопки результатов
        self.Bind(wx.EVT_BUTTON, self.on_copy_wkt,   self.m_btn_copy_wkt)
        self.Bind(wx.EVT_BUTTON, self.on_copy_proj4, self.m_btn_copy_proj4)
        self.Bind(wx.EVT_BUTTON, self.on_save_result,self.m_btn_save_result)

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
        # get_data() возвращает "enabled_plan" и "enabled_h", а не "enabled"
        if len([r for r in raw if r["enabled_plan"]]) < 4:
            wx.MessageBox(
                "Для 7-параметрического преобразования нужно минимум 4 точки.",
                "Недостаточно данных", wx.OK | wx.ICON_WARNING
            )
            return

        try:
            pairs = [
                PointPair(
                    name         = r["name"],
                    x1           = float(r["x1"]),
                    y1           = float(r["y1"]),
                    h1           = float(r["h1"]) if r["h1"] else None,
                    x2           = float(r["x2"]),
                    y2           = float(r["y2"]),
                    h2           = float(r["h2"]) if r["h2"] else None,
                    enabled_plan = r["enabled_plan"],
                    enabled_h    = r["enabled_h"],
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
            self.on_save_result(None)
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