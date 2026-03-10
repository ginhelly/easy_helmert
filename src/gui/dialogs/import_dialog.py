"""
ImportDialog — диалог импорта координат из текстового файла.

Возможности:
  - Автоопределение разделителя
  - Динамический предпросмотр (обновляется при смене разделителя / skip)
  - Назначение столбцов через ПКМ по заголовку
  - Нормализация и DMS→DD конвертация числовых значений
  - Проверка обязательного столбца «Имя»
"""

from __future__ import annotations

import os
import wx
import wx.grid as gridlib
from typing import Dict, List, Optional, Tuple

from gui.widgets.coordinate_grid import _parse_coordinate, _sys_dec_sep

# ── Целевые столбцы основной таблицы ─────────────────────────────────────────

_TARGET_COLS: List[Tuple[str, Optional[str]]] = [
    ("—  (не импортировать)", None),
    ("Имя",                   "name"),
    ("Восток исх.",           "x1"),
    ("Север исх.",            "y1"),
    ("Высота исх.",           "h1"),
    ("Восток цел.",           "x2"),
    ("Север цел.",            "y2"),
    ("Высота цел.",           "h2"),
]

_NUMERIC_KEYS = frozenset({"x1", "y1", "h1", "x2", "y2", "h2"})

# ── Варианты разделителей ─────────────────────────────────────────────────────

_DELIM_OPTIONS: List[Tuple[str, Optional[str]]] = [
    ("Табуляция  (\\t)",   "\t"),
    ("Точка с зап.  (;)", ";"),
    ("Запятая  (,)",       ","),
    ("Пробел",             " "),
    ("Другой:",            None),   # custom
]

MAX_PREVIEW_ROWS = 100

# Цвета
_CLR_ASSIGNED   = wx.Colour(210, 235, 255)   # голубой — назначен
_CLR_UNASSIGNED = wx.Colour(255, 255, 255)   # белый   — не назначен
_CLR_NAME_COL   = wx.Colour(255, 243, 205)   # жёлтый  — столбец «Имя»


class ImportDialog(wx.Dialog):
    """
    Диалог импорта координат из текстового файла.

    После ShowModal() == wx.ID_OK вызывайте get_import_data().
    """

    def __init__(self, parent: wx.Window, filepath: str):
        super().__init__(
            parent,
            title=f"Импорт: {os.path.basename(filepath)}",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(940, 660),
        )
        self.SetMinSize((640, 480))

        self._filepath  = filepath
        self._raw_lines: List[str]                = []
        self._col_map:   Dict[int, Optional[str]] = {}   # {file_col: target_key}
        self._dec_sep   = _sys_dec_sep()

        self._load_file()
        self._build_ui()
        self._bind_events()
        self._auto_detect_delimiter()   # выбирает radio до первого refresh
        self._refresh_preview()

        self.Centre()

    # ── Загрузка файла ────────────────────────────────────────────────────────

    def _load_file(self):
        for enc in ("utf-8-sig", "utf-8", "cp1251", "cp1252", "latin-1"):
            try:
                with open(self._filepath, "r", encoding=enc) as fh:
                    self._raw_lines = fh.read().splitlines()
                return
            except (UnicodeDecodeError, IOError):
                continue
        self._raw_lines = []

    # ── Построение UI ─────────────────────────────────────────────────────────

    def _build_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        # ── Путь к файлу ──────────────────────────────────────────────────
        path_row = wx.BoxSizer(wx.HORIZONTAL)
        path_row.Add(
            wx.StaticText(self, label="Файл:"),
            0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6,
        )
        lbl = wx.StaticText(
            self, label=self._filepath,
            style=wx.ST_ELLIPSIZE_START | wx.ALIGN_LEFT,
        )
        lbl.SetForegroundColour(wx.Colour(60, 60, 60))
        lbl.SetToolTip(self._filepath)
        path_row.Add(lbl, 1, wx.ALIGN_CENTER_VERTICAL)
        root.Add(path_row, 0, wx.EXPAND | wx.ALL, 8)

        # ── Панель настроек ───────────────────────────────────────────────
        cfg_box   = wx.StaticBox(self, label="Параметры импорта")
        cfg_sizer = wx.StaticBoxSizer(cfg_box, wx.HORIZONTAL)

        # Разделитель
        delim_vbox = wx.BoxSizer(wx.VERTICAL)
        delim_vbox.Add(wx.StaticText(self, label="Разделитель:"), 0, wx.BOTTOM, 6)

        self._rb_map: Dict[int, Tuple[wx.RadioButton, Optional[str]]] = {}
        first = True
        for i, (label, char) in enumerate(_DELIM_OPTIONS):
            style = wx.RB_GROUP if first else 0
            rb    = wx.RadioButton(self, label=label, style=style)
            first = False
            self._rb_map[i] = (rb, char)

            if char is None:
                self._rb_custom  = rb
                row = wx.BoxSizer(wx.HORIZONTAL)
                row.Add(rb, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
                self._txt_custom = wx.TextCtrl(self, value="|", size=(44, -1))
                row.Add(self._txt_custom, 0, wx.ALIGN_CENTER_VERTICAL)
                delim_vbox.Add(row, 0, wx.BOTTOM, 3)
            else:
                delim_vbox.Add(rb, 0, wx.BOTTOM, 3)

        cfg_sizer.Add(delim_vbox, 0, wx.ALL, 8)
        cfg_sizer.Add(
            wx.StaticLine(self, style=wx.LI_VERTICAL),
            0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8,
        )

        # Пропустить строк
        skip_vbox = wx.BoxSizer(wx.VERTICAL)
        skip_vbox.Add(
            wx.StaticText(self, label="Пропустить\nстрок в начале:"),
            0, wx.BOTTOM, 6,
        )
        self._spin_skip = wx.SpinCtrl(self, min=0, max=9999, initial=0, size=(74, -1))
        skip_vbox.Add(self._spin_skip, 0)
        cfg_sizer.Add(skip_vbox, 0, wx.ALL, 8)
        cfg_sizer.Add(
            wx.StaticLine(self, style=wx.LI_VERTICAL),
            0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8,
        )

        # Подсказка
        hint = wx.StaticText(
            self,
            label=(
                "Как назначить столбцы:\n"
                "щёлкните правой кнопкой мыши\n"
                "по заголовку столбца\n"
                "в таблице предпросмотра.\n\n"
                "Столбец «Имя» — обязателен.\n"
                "Остальные — по необходимости."
            ),
        )
        hint.SetForegroundColour(wx.Colour(80, 80, 80))
        cfg_sizer.Add(hint, 1, wx.ALL, 8)

        root.Add(cfg_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        # ── Предпросмотр ──────────────────────────────────────────────────
        root.Add(
            wx.StaticText(
                self,
                label=(
                    "Предпросмотр  "
                    "(правая кнопка мыши по заголовку → назначить столбец):"
                ),
            ),
            0, wx.LEFT | wx.BOTTOM, 8,
        )

        self._grid = gridlib.Grid(self)
        self._grid.CreateGrid(0, 0)
        self._grid.EnableEditing(False)
        self._grid.SetDefaultRowSize(21)
        self._grid.SetColLabelSize(40)   # двухстрочный: «  N  \nНазначение»
        self._grid.SetRowLabelSize(40)
        self._grid.DisableDragRowSize()
        self._grid.SetSelectionMode(
            gridlib.Grid.GridSelectionModes.GridSelectColumns
        )
        root.Add(self._grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        # ── Кнопки ────────────────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        self._btn_ok     = wx.Button(self, wx.ID_OK,     "Импортировать")
        self._btn_cancel = wx.Button(self, wx.ID_CANCEL, "Отмена")
        self._btn_ok.SetDefault()
        btn_sizer.AddButton(self._btn_ok)
        btn_sizer.AddButton(self._btn_cancel)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(root)

    # ── Привязка событий ──────────────────────────────────────────────────────

    def _bind_events(self):
        for rb, _ in self._rb_map.values():
            rb.Bind(wx.EVT_RADIOBUTTON, self._on_settings_changed)
        self._txt_custom.Bind(wx.EVT_TEXT, self._on_settings_changed)
        self._spin_skip.Bind(wx.EVT_SPINCTRL, self._on_settings_changed)
        self._grid.Bind(
            gridlib.EVT_GRID_LABEL_RIGHT_CLICK,
            self._on_label_rclick,
        )
        self._btn_ok.Bind(wx.EVT_BUTTON, self._on_ok)

    # ── Обработчики ───────────────────────────────────────────────────────────

    def _on_settings_changed(self, event):
        self._refresh_preview()
        event.Skip()

    def _on_label_rclick(self, event):
        col = event.GetCol()
        if col >= 0:
            self._show_mapping_menu(col)
        # col == -1 — клик по угловой ячейке, игнорируем

    def _on_ok(self, event):
        if "name" not in self._col_map.values():
            wx.MessageBox(
                "Назначьте столбец «Имя» — он используется для\n"
                "сопоставления точек с уже существующими в таблице.",
                "Не назначен столбец «Имя»",
                wx.OK | wx.ICON_WARNING,
                self,
            )
            return
        event.Skip()   # диалог закрывается с wx.ID_OK

    # ── Контекстное меню назначения ───────────────────────────────────────────

    def _show_mapping_menu(self, file_col: int):
        current_key = self._col_map.get(file_col)
        menu = wx.Menu()

        for label, key in _TARGET_COLS:
            item = menu.AppendRadioItem(wx.ID_ANY, label)
            if key == current_key:
                item.Check(True)
            menu.Bind(
                wx.EVT_MENU,
                lambda e, k=key, c=file_col: self._assign_col(c, k),
                id=item.GetId(),
            )

        self._grid.PopupMenu(menu)
        menu.Destroy()

    def _assign_col(self, file_col: int, target_key: Optional[str]):
        # Один ключ — один столбец файла (снимаем предыдущее назначение)
        if target_key is not None:
            for fc in list(self._col_map):
                if self._col_map[fc] == target_key and fc != file_col:
                    self._col_map[fc] = None
        self._col_map[file_col] = target_key
        self._update_col_labels()

    # ── Парсинг и предпросмотр ────────────────────────────────────────────────

    def _get_delimiter(self) -> str:
        for rb, char in self._rb_map.values():
            if rb.GetValue():
                if char is not None:
                    return char
                return self._txt_custom.GetValue() or "\t"
        return "\t"

    def _parse_lines(self, limit: int = MAX_PREVIEW_ROWS) -> List[List[str]]:
        delim = self._get_delimiter()
        skip  = self._spin_skip.GetValue()
        rows: List[List[str]] = []
        for line in self._raw_lines[skip:]:
            if not line.strip():
                continue
            cells = line.split() if delim == " " else line.split(delim)
            rows.append([c.strip() for c in cells])
            if limit and len(rows) >= limit:
                break
        return rows

    def _auto_detect_delimiter(self):
        """Выбирает наиболее вероятный разделитель по первым строкам файла."""
        sample = [l for l in self._raw_lines[:30] if l.strip()][:15]
        if not sample:
            return

        best_idx, best_score = 0, -1.0

        for rb_idx, (_, char) in enumerate(_DELIM_OPTIONS[:-1]):   # без «Другой»
            counts = []
            for line in sample:
                n = len(line.split()) if char == " " else len(line.split(char))
                counts.append(n)
            if not counts or max(counts) <= 1:
                continue
            avg         = sum(counts) / len(counts)
            consistency = 1.0 - (max(counts) - min(counts)) / max(max(counts), 1)
            score       = avg * consistency
            if score > best_score:
                best_score = score
                best_idx   = rb_idx

        self._rb_map[best_idx][0].SetValue(True)

    def _refresh_preview(self):
        rows = self._parse_lines()
        grid = self._grid

        if grid.GetNumberRows():
            grid.DeleteRows(0, grid.GetNumberRows())
        if grid.GetNumberCols():
            grid.DeleteCols(0, grid.GetNumberCols())

        if not rows:
            return

        n_cols = max(len(r) for r in rows)

        grid.AppendCols(n_cols)
        grid.AppendRows(len(rows))

        # Удаляем маппинги несуществующих столбцов
        self._col_map = {k: v for k, v in self._col_map.items() if k < n_cols}

        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                if c < n_cols:
                    grid.SetCellValue(r, c, val)

        self._update_col_labels()
        grid.AutoSizeColumns(setAsMin=False)
        grid.ForceRefresh()

    def _update_col_labels(self):
        grid = self._grid
        for c in range(grid.GetNumberCols()):
            key   = self._col_map.get(c)
            label = next((lbl for lbl, k in _TARGET_COLS if k == key), "—")
            grid.SetColLabelValue(c, f"  {c + 1}  \n{label}")

            attr = gridlib.GridCellAttr()
            if key == "name":
                attr.SetBackgroundColour(_CLR_NAME_COL)
            elif key is not None:
                attr.SetBackgroundColour(_CLR_ASSIGNED)
            else:
                attr.SetBackgroundColour(_CLR_UNASSIGNED)
            grid.SetColAttr(c, attr)

        grid.ForceRefresh()

    # ── Публичный метод ───────────────────────────────────────────────────────

    def get_import_data(self) -> List[dict]:
        """
        Возвращает все строки файла (без ограничения предпросмотра) в виде
        списка словарей {name, x1, y1, h1, x2, y2, h2}.

        - Числовые поля нормализуются и конвертируются из DMS при необходимости.
        - Строки без поля «name» пропускаются.
        """
        rows   = self._parse_lines(limit=0)   # 0 = без ограничения
        result: List[dict] = []

        for cells in rows:
            row_dict: dict = {}
            for file_col, target_key in self._col_map.items():
                if target_key is None:
                    continue
                val = cells[file_col].strip() if file_col < len(cells) else ""
                if val and target_key in _NUMERIC_KEYS:
                    val = _parse_coordinate(val, self._dec_sep)
                row_dict[target_key] = val

            if not row_dict.get("name", "").strip():
                continue

            result.append(row_dict)

        return result