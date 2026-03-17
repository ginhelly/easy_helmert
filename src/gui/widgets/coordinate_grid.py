"""
CoordinateGrid — таблица координат для 7-параметрического преобразования Гельмерта.

Столбцы:
  ✓пл | ✓выс | Имя | X исх. | Y исх. | H исх. | X цел. | Y цел. | H цел. | dX | dY | dH

Возможности:
  - Два чекбокса: отдельно для плановых XY и высотных H
  - Редактирование с одного клика (без двойного)
  - Ctrl+V из Excel/TSV/CSV с автодобавлением строк
  - Ctrl+C в Excel-совместимый TSV
  - Автораспределение ширины столбцов по ширине окна
  - Нормализация десятичного разделителя по системной локали
  - Валидация: числовые столбцы принимают только цифры / разделитель / минус
  - Подсветка невязок (зелёный / красный)
"""

from __future__ import annotations

import locale
import wx
import wx.grid as gridlib
from typing import List, Optional, Tuple

from gui.utils.dms import _try_dms_to_dd, _DMS_TYPEABLE_CHARS


# ── Локаль и нормализация чисел ───────────────────────────────────────────────

def _sys_dec_sep() -> str:
    """Системный разделитель дробной части ('.' или ',')."""
    try:
        sep = locale.localeconv().get("decimal_point", ".")
        return sep if sep in (".", ",") else "."
    except Exception:
        return "."

def _parse_coordinate(raw: str, dec_sep: str) -> str:
    """
    Универсальная нормализация значения в числовой ячейке координат:
      1. Пробует DMS → DD конвертацию.
      2. Если не DMS — стандартная числовая нормализация (_normalize_number).

    Используется вместо _normalize_number для всех столбцов _EDITABLE_NUM.
    """
    raw = raw.strip()
    if not raw:
        return raw
    dms = _try_dms_to_dd(raw, dec_sep)
    return dms if dms is not None else _normalize_number(raw, dec_sep)


def _normalize_number(raw: str, dec_sep: str) -> str:
    """
    Нормализует строку числа:
      - заменяет альтернативный разделитель (. ↔ ,)
      - удаляет все нечисловые символы, кроме dec_sep и ведущего минуса
    """
    raw = raw.strip()
    if not raw:
        return raw
    alt = "," if dec_sep == "." else "."
    raw = raw.replace(alt, dec_sep)
    result = ""
    has_sep = False
    for i, ch in enumerate(raw):
        if ch.isdigit():
            result += ch
        elif ch == dec_sep and not has_sep:
            result += ch
            has_sep = True
        elif ch == "-" and i == 0 and not result:
            result += ch
    return result


# ── Определение столбцов ─────────────────────────────────────────────────────

class _Col:
    USE_PLAN = 0
    USE_H    = 1
    NAME     = 2
    X1       = 3
    Y1       = 4
    H1       = 5
    H1_CORR  = 6   # скорректированная высота исходной СК (readonly)
    X2       = 7
    Y2       = 8
    H2       = 9
    H2_CORR  = 10  # скорректированная высота опорной СК (readonly)
    DX       = 11
    DY       = 12
    DH       = 13
    DE       = 14
    DN       = 15
    DU       = 16
    COUNT    = 17


# (заголовок, мин. ширина px, readonly, flex-вес для авторастяжки)
# flex-вес == 0  →  фиксированная ширина, не растягивается
_COL_DEFS: List[Tuple[str, int, bool, float]] = [
    ("✓ пл",            40,  False, 0.0),   # USE_PLAN
    ("✓ выс",           40,  False, 0.0),   # USE_H
    ("Имя",             90,  False, 0.0),   # NAME
    ("Восток исх.",     90,  False, 1.2),   # X1
    ("Север исх.",      90,  False, 1.2),   # Y1
    ("Высота исх.",     82,  False, 1.0),   # H1
    ("H исх. скорр.",  130,  True,  0.0),   # H1_CORR ← новый, фиксированная ширина
    ("Восток опорн.",   90,  False, 1.2),   # X2
    ("Север опорн.",    90,  False, 1.2),   # Y2
    ("Высота опорн.",   82,  False, 1.0),   # H2
    ("H опорн. скорр.", 130, True,  0.0),   # H2_CORR ← новый, фиксированная ширина
    ("ΔX, м",           72,  True,  0.8),   # DX
    ("ΔY, м",           72,  True,  0.8),   # DY
    ("ΔZ, м",           72,  True,  0.8),   # DH
    ("dE, м",           72,  True,  0.8),   # DE
    ("dN, м",           72,  True,  0.8),   # DN
    ("dU, м",           72,  True,  0.8),   # DU
]

_READONLY_COLS = frozenset({
    _Col.H1_CORR, _Col.H2_CORR,
    _Col.DX, _Col.DY, _Col.DH,
    _Col.DE, _Col.DN, _Col.DU,
})

_CHECKBOX_COLS  = frozenset({_Col.USE_PLAN, _Col.USE_H})
_NUMERIC_COLS   = frozenset({
    _Col.X1, _Col.Y1, _Col.H1,
    _Col.X2, _Col.Y2, _Col.H2,
    _Col.DX, _Col.DY, _Col.DH,
})
_EDITABLE_NUM   = _NUMERIC_COLS - _READONLY_COLS   # числовые редактируемые

# Цвета невязок
_CLR_OK  = wx.Colour(198, 239, 206)   # зелёный — норма
_CLR_BAD = wx.Colour(255, 199, 206)   # красный — превышение
_CLR_NA  = wx.Colour(235, 235, 235)   # серый   — нет данных
_CLR_GEOID = wx.Colour(210, 232, 252) # светло-голубой: есть данные геоида

_DEFAULT_THRESHOLD = 0.1              # порог подсветки (единицы СК)

def _row_noun_ru(n: int) -> str:
    """'строку' / '2 строки' / '5 строк' — склонение для меню."""
    if n == 1:
        return "строку"
    if 2 <= n % 10 <= 4 and not (11 <= n % 100 <= 14):
        return f"{n} строки"
    return f"{n} строк"

# Numpad-диапазон для проверки в EVT_CHAR
_NUMPAD0     = wx.WXK_NUMPAD0
_NUMPAD9     = wx.WXK_NUMPAD9
_NUMPAD_DEC  = wx.WXK_NUMPAD_DECIMAL


# ── Класс таблицы ────────────────────────────────────────────────────────────

class CoordinateGrid(gridlib.Grid):
    """Главная таблица ввода координат с невязками."""

    MIN_ROWS = 3

    def __init__(self, parent: wx.Window, on_data_changed=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._busy    = False          # флаг «идёт массовое обновление»
        self._resize_pending   = False   # ← новый флаг
        self._dec_sep = _sys_dec_sep() # системный разделитель
        self._on_data_changed   = on_data_changed   
        self._text_editor_ctrl = None
        self._computed_cells: set[tuple[int, int]] = set()
        self._normal_cell_font = wx.Font(self.GetDefaultCellFont())
        self._bold_cell_font = wx.Font(self.GetDefaultCellFont())
        self._bold_cell_font.SetWeight(wx.FONTWEIGHT_BOLD)
        self._setup_grid()
        self._bind_events()

    # ── Инициализация ─────────────────────────────────────────────────────────

    def _setup_grid(self):
        self._busy = True

        self.CreateGrid(self.MIN_ROWS, _Col.COUNT)

        # Заголовки и начальные ширины
        for i, (label, min_w, _ro, _fw) in enumerate(_COL_DEFS):
            self.SetColLabelValue(i, label)
            self.SetColSize(i, min_w)

        # Атрибуты для readonly-столбцов (невязки)
        ro_attr = gridlib.GridCellAttr()
        ro_attr.SetReadOnly(True)
        ro_attr.SetBackgroundColour(_CLR_NA)
        ro_attr.SetTextColour(wx.Colour(60, 60, 60))
        for col in _READONLY_COLS:
            self.SetColAttr(col, ro_attr.Clone())

        # Начальная инициализация строк
        for row in range(self.MIN_ROWS):
            self._init_row(row)

        # Внешний вид
        self.SetDefaultRowSize(24, resizeExistingRows=True)
        self.SetRowLabelSize(32)
        self.SetColLabelSize(22)
        self.DisableDragRowSize()
        self.DisableDragColMove()

        # ✅ Правильные enum-пути (wxPython 4.1+)
        self.SetSelectionMode(gridlib.Grid.GridSelectionModes.GridSelectCells)
        self.SetTabBehaviour(gridlib.Grid.TabBehaviour.Tab_Wrap)

        self._busy = False

        # Первичное распределение ширин после встраивания в layout
        wx.CallAfter(self._distribute_col_widths)

    def _init_row(self, row: int, plan: bool = True, h: bool = True):
        """Инициализация строки: чекбоксы + выравнивание числовых ячеек."""
        # Чекбоксы
        for col in _CHECKBOX_COLS:
            self.SetCellRenderer(row, col, gridlib.GridCellBoolRenderer())
            self.SetCellEditor(row, col, gridlib.GridCellBoolEditor())
            self.SetCellAlignment(row, col, wx.ALIGN_CENTRE, wx.ALIGN_CENTRE)
        self.SetCellValue(row, _Col.USE_PLAN, "1" if plan else "")
        self.SetCellValue(row, _Col.USE_H,    "1" if h    else "")

        # Числовые ячейки — выравнивание вправо
        for col in _NUMERIC_COLS:
            self.SetCellAlignment(row, col, wx.ALIGN_RIGHT, wx.ALIGN_CENTRE)

        # Цвет фона для невязок
        for col in _READONLY_COLS:
            self.SetCellBackgroundColour(row, col, _CLR_NA)

    # ── Авторастяжка столбцов ─────────────────────────────────────────────────

    def _on_size(self, event):
        event.Skip()
        # Ставим в очередь не более одного вызова за раз.
        # Без этой проверки EndBatch() внутри _distribute_col_widths
        # триггерит EVT_SIZE снова, очередь растёт бесконечно.
        if self and not self._resize_pending:
            self._resize_pending = True
            wx.CallAfter(self._distribute_col_widths)

    def _distribute_col_widths(self):
        """
        Распределяет ширину гибких столбцов пропорционально их flex-весу,
        заполняя всю доступную ширину клиентской области.
        """
        self._resize_pending = False   # сбрасываем до любых операций с размерами
        if not self:
            return
        total = self.GetClientSize().width
        if total <= 0:
            return

        row_label_w = self.GetRowLabelSize()
        # Небольшой запас, чтобы не появлялся горизонтальный скроллбар
        available = total - row_label_w - 4

        # Сумма фиксированных ширин
        fixed_sum = sum(
            _COL_DEFS[i][1]
            for i in range(_Col.COUNT)
            if _COL_DEFS[i][3] == 0.0
        )

        # Сумма flex-весов
        flex_total = sum(d[3] for d in _COL_DEFS if d[3] > 0.0)
        if flex_total == 0.0:
            return

        flex_pool = max(available - fixed_sum, 0)
        unit      = flex_pool / flex_total

        self.BeginBatch()
        for i, (_, min_w, _ro, weight) in enumerate(_COL_DEFS):
            if weight == 0.0:
                self.SetColSize(i, min_w)
            else:
                self.SetColSize(i, max(int(weight * unit), min_w))
        self.EndBatch()
        self.ForceRefresh()

    # ── Привязка событий ──────────────────────────────────────────────────────

    def _bind_events(self):
        self.Bind(gridlib.EVT_GRID_SELECT_CELL,    self._on_select_cell)
        self.Bind(gridlib.EVT_GRID_CELL_LEFT_CLICK, self._on_left_click)
        self.Bind(gridlib.EVT_GRID_CELL_CHANGED,    self._on_cell_changed)
        self.Bind(gridlib.EVT_GRID_EDITOR_CREATED,  self._on_editor_created)
        self.Bind(wx.EVT_KEY_DOWN,                   self._on_key_down)
        self.Bind(wx.EVT_SIZE,                       self._on_size)
        self.Bind(gridlib.EVT_GRID_CELL_RIGHT_CLICK,  self._on_right_click)
        self.Bind(gridlib.EVT_GRID_LABEL_RIGHT_CLICK, self._on_right_click)
    
    def _notify_changed(self):
        """
        Вызывается при любом изменении данных пользователем.
        Уведомляет владельца (main_frame) через переданный callback.
        """
        if self._busy:
            return
        if callable(self._on_data_changed):
            self._on_data_changed()

    # Одиночный клик → сразу в режим редактирования (не двойной)
    def _on_select_cell(self, event):
        event.Skip()
        col = event.GetCol()
        if col not in _CHECKBOX_COLS:
            wx.CallAfter(self._safe_enable_edit)
            #wx.CallAfter(self._rebind_editor_filter, col)   # ← каждый раз перепривязываем

    def _rebind_editor_filter(self, col: int):
        """
        Перепривязывает числовой фильтр к кэшированному TextCtrl
        в зависимости от текущего столбца.

        Вызывается при каждом переходе между ячейками, чтобы компенсировать
        переиспользование редактора wxGrid.
        """
        return
        if not self or self._text_editor_ctrl is None:
            return
        try:
            ctrl = self._text_editor_ctrl
            ctrl.Unbind(wx.EVT_CHAR, handler=self._on_numeric_char)
            if col in _EDITABLE_NUM:
                ctrl.Bind(wx.EVT_CHAR, self._on_numeric_char)
        except Exception:
            pass

    def _safe_enable_edit(self):
        if self and not self.IsCellEditControlEnabled():
            self.EnableCellEditControl()

    # Одиночный клик по чекбоксу — toggle без открытия редактора
    def _on_left_click(self, event):
        row, col = event.GetRow(), event.GetCol()
        if col in _CHECKBOX_COLS:
            cur = self.GetCellValue(row, col)
            self.SetCellValue(row, col, "" if cur == "1" else "1")
            self.ForceRefresh()
            self._notify_changed()
            return   # НЕ Skip — редактор не открывается
        event.Skip()

    # Нормализация после сохранения ячейки
    def _on_cell_changed(self, event):
        row, col = event.GetRow(), event.GetCol()
        if not self._busy and (row, col) in self._computed_cells:
            self._clear_computed_cell(row, col)
        self._notify_changed()
        if col in _EDITABLE_NUM:
            raw        = self.GetCellValue(row, col)
            try:
                normalized = _parse_coordinate(raw, self._dec_sep)  # ← было _normalize_number
                if normalized != raw:
                    wx.CallAfter(self.SetCellValue, row, col, normalized)
            except Exception:
                pass
        event.Skip()

    # Привязка char-фильтра к текстовому контролу редактора
    def _on_editor_created(self, event):
        ctrl = event.GetControl()
        if ctrl:
            self._text_editor_ctrl = ctrl
            # Привязываем фильтр один раз навсегда.
            # Какой столбец сейчас редактируется — проверяется внутри фильтра.
            ctrl.Bind(wx.EVT_CHAR, self._on_numeric_char)
        event.Skip()

    def _on_numeric_char(self, event):
        """
        Фильтр нажатий для числовых столбцов:
        пропускает цифры, оба разделителя, ведущий минус,
        управляющие клавиши и Ctrl/Alt-комбинации.
        """
        # Если это нечисловой столбец — пропускаем всё без проверок
        col = self.GetGridCursorCol()
        if col not in _EDITABLE_NUM:
            event.Skip()
            return

        key = event.GetKeyCode()

        if event.ControlDown() or event.AltDown():
            event.Skip()
            return

        if key < wx.WXK_SPACE:
            event.Skip()
            return

        if key in (
            wx.WXK_DELETE, wx.WXK_BACK,
            wx.WXK_LEFT,   wx.WXK_RIGHT,
            wx.WXK_HOME,   wx.WXK_END,
            wx.WXK_UP,     wx.WXK_DOWN,
        ):
            event.Skip()
            return

        if _NUMPAD0 <= key <= _NUMPAD9:
            event.Skip()
            return

        if key == _NUMPAD_DEC:
            event.Skip()
            return

        # Unicode DMS-символы > 255 (∘ ′ ″ 度 分 秒 …) через EVT_CHAR не приходят —
        # они обрабатываются только в _paste_clipboard. Блокируем.
        if key > 255:
            return

        ch = chr(key)

        if ch.isdigit():
            event.Skip()
            return

        if ch in ('.', ','):
            event.Skip()
            return

        # ✅ DMS-символы: °, ', ", `, ´, *, пробел, N/S/E/W
        if ch in _DMS_TYPEABLE_CHARS:
            event.Skip()
            return

        # Минус только в начале строки
        if ch == '-':
            ctrl = event.GetEventObject()
            if hasattr(ctrl, 'GetInsertionPoint') and hasattr(ctrl, 'GetValue'):
                pos = ctrl.GetInsertionPoint()
                val = ctrl.GetValue()
                sel = ctrl.GetSelection()
                at_start     = (pos == 0)
                all_selected = (sel[0] == 0 and sel[1] == len(val))
                no_minus_yet = '-' not in val
                if (at_start or all_selected) and no_minus_yet:
                    event.Skip()
            return

        # Всё остальное — блокируем (event.Skip() не вызываем)

    def _on_key_down(self, event):
        ctrl = event.ControlDown()
        key  = event.GetKeyCode()
        if ctrl and key == ord("V"):
            self._paste_clipboard()
        elif ctrl and key == ord("C"):
            self._copy_clipboard()
        elif ctrl and key == ord("A"):
            self.SelectAll()
        elif key == wx.WXK_DELETE:
            self._clear_selection()
        else:
            event.Skip()

    # ── Буфер обмена ─────────────────────────────────────────────────────────

    def _paste_clipboard(self):
        """Вставка TSV / CSV / текст из буфера обмена (Excel-совместимо)."""
        if not wx.TheClipboard.Open():
            return
        try:
            obj = wx.TextDataObject()
            ok  = wx.TheClipboard.GetData(obj)
        finally:
            wx.TheClipboard.Close()
        if not ok:
            return

        text = obj.GetText().strip()
        if not text:
            return

        rows_data = self._parse_tabular(text)
        if not rows_data:
            return

        # Начальная ячейка: верхний левый угол выделения или курсор
        tl = self.GetSelectionBlockTopLeft()
        if tl:
            start_row, start_col = tl[0].GetRow(), tl[0].GetCol()
        else:
            start_row = self.GetGridCursorRow()
            start_col = self.GetGridCursorCol()

        # Автодобавление строк
        needed  = start_row + len(rows_data)
        current = self.GetNumberRows()
        if needed > current:
            self.AppendRows(needed - current)
            for r in range(current, needed):
                self._init_row(r)

        # Вставка
        for r_off, row_cells in enumerate(rows_data):
            for c_off, val in enumerate(row_cells):
                col = start_col + c_off
                row = start_row + r_off
                if col >= _Col.COUNT:
                    break
                if col in _READONLY_COLS:
                    continue
                if col in _CHECKBOX_COLS:
                    v = val.strip().lower()
                    self.SetCellValue(row, col, "" if v in ("0", "false", "") else "1")
                elif col in _NUMERIC_COLS:
                    self.SetCellValue(row, col, _parse_coordinate(val, self._dec_sep))
                else:
                    self.SetCellValue(row, col, val.strip())

        self.ForceRefresh()
        self._notify_changed()

    def _copy_clipboard(self):
        """Копирование выделенного блока в TSV (совместимо с Excel)."""
        tl = self.GetSelectionBlockTopLeft()
        br = self.GetSelectionBlockBottomRight()
        if tl and br:
            r1, c1 = tl[0].GetRow(), tl[0].GetCol()
            r2, c2 = br[0].GetRow(), br[0].GetCol()
            lines = [
                "\t".join(self.GetCellValue(r, c) for c in range(c1, c2 + 1))
                for r in range(r1, r2 + 1)
            ]
            text = "\n".join(lines)
        else:
            text = self.GetCellValue(self.GetGridCursorRow(), self.GetGridCursorCol())

        if text and wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()

    def _clear_selection(self):
        """Delete — очистить содержимое выделенных ячеек."""
        tl = self.GetSelectionBlockTopLeft()
        br = self.GetSelectionBlockBottomRight()
        if tl and br:
            r1, c1 = tl[0].GetRow(), tl[0].GetCol()
            r2, c2 = br[0].GetRow(), br[0].GetCol()
            for r in range(r1, r2 + 1):
                for c in range(c1, c2 + 1):
                    if c not in _READONLY_COLS:
                        self.SetCellValue(r, c, "")
        else:
            row, col = self.GetGridCursorRow(), self.GetGridCursorCol()
            if col not in _READONLY_COLS:
                self.SetCellValue(row, col, "")
        self.ForceRefresh()
        self._notify_changed()

    # ── Публичное API ─────────────────────────────────────────────────────────

    def add_row(self):
        """Добавить пустую строку в конец."""
        self.AppendRows(1)
        row = self.GetNumberRows() - 1
        self._init_row(row)
        self.MakeCellVisible(row, 0)
        self.SetGridCursor(row, _Col.NAME)
        self._notify_changed()

    def delete_selected_rows(self, rows: List[int] = None):
        """Удалить строки. Если rows=None — берёт выделение / курсор."""
        if rows is None:
            rows = self._get_affected_rows()
        for row in sorted(rows, reverse=True):
            if self.GetNumberRows() > self.MIN_ROWS:
                self.DeleteRows(row, 1)
            else:
                for col in range(_Col.COUNT):
                    if col not in _READONLY_COLS:
                        self.SetCellValue(row, col, "")
                self.SetCellValue(row, _Col.USE_PLAN, "1")
                self.SetCellValue(row, _Col.USE_H,    "1")
        self.ForceRefresh()
        self._notify_changed()

    # ── Контекстное меню ──────────────────────────────────────────────────────

    def _get_affected_rows(self) -> List[int]:
        """
        Возвращает отсортированный список уникальных строк, затронутых
        текущим выделением (ячейки, блоки, целые строки) или курсором.
        """
        rows: set[int] = set()

        # 1. Строки, выделенные целиком (клик по метке строки)
        rows.update(self.GetSelectedRows())

        # 2. Блоки выделенных ячеек
        tl = self.GetSelectionBlockTopLeft()
        br = self.GetSelectionBlockBottomRight()
        if tl and br:
            for i in range(len(tl)):
                for r in range(tl[i].GetRow(), br[i].GetRow() + 1):
                    rows.add(r)

        # 3. Индивидуально выделенные ячейки
        for cell in self.GetSelectedCells():
            rows.add(cell.GetRow())

        # 4. Фолбэк — строка под курсором
        if not rows:
            cursor_row = self.GetGridCursorRow()
            if cursor_row >= 0:
                rows.add(cursor_row)

        return sorted(rows)

    def _on_right_click(self, event):
        """Правый клик по ячейке или метке строки → контекстное меню."""
        clicked_row = event.GetRow()

        # Если кликнули по строке вне текущего выделения — переключаемся на неё
        affected = self._get_affected_rows()
        if clicked_row >= 0 and clicked_row not in affected:
            self.ClearSelection()
            self.SetGridCursor(clicked_row, max(event.GetCol(), 0))
            affected = [clicked_row]

        if affected:
            self._show_context_menu(affected)

        # event.Skip() не вызываем — иначе стандартный обработчик
        # может сбросить выделение перед показом меню

    def _show_context_menu(self, rows: List[int]):
        """Построить и показать контекстное меню для указанных строк."""
        n          = len(rows)
        noun_del   = _row_noun_ru(n)
        noun_dup   = noun_del  # те же формы

        menu = wx.Menu()

        # ── Удалить ──────────────────────────────────────────────────────
        id_del = wx.NewIdRef()
        item_del = menu.Append(id_del, f"🗑  Удалить {noun_del}")

        # ── Дублировать ──────────────────────────────────────────────────
        id_dup = wx.NewIdRef()
        menu.Append(id_dup, f"📋  Дублировать {noun_dup}")

        menu.AppendSeparator()

        # ── Swap X↔Y ─────────────────────────────────────────────────────
        id_swap_src = wx.NewIdRef()
        id_swap_dst = wx.NewIdRef()
        menu.Append(id_swap_src, "Север ↔ Восток   подгоняемые  (выделенные строки)")
        menu.Append(id_swap_dst, "Север ↔ Восток   опорные   (выделенные строки)")

        # ── Разделитель + глобальный swap для удобства ───────────────────
        menu.AppendSeparator()
        id_swap_src_all = wx.NewIdRef()
        id_swap_dst_all = wx.NewIdRef()
        menu.Append(id_swap_src_all, "Север ↔ Восток   подгоняемые  (все строки)")
        menu.Append(id_swap_dst_all, "Север ↔ Восток   опорные   (все строки)")

        # Недоступность «Удалить», если строк и так минимум
        if self.GetNumberRows() <= self.MIN_ROWS:
            item_del.Enable(False)

        # ── Привязка обработчиков ─────────────────────────────────────────
        # Захватываем rows через замыкание — безопасно, т.к. PopupMenu
        # обрабатывает все события до возврата управления.
        _rows = list(rows)   # копия, чтобы не зависеть от внешнего состояния

        self.Bind(wx.EVT_MENU, lambda _: self.delete_selected_rows(_rows),  id=id_del)
        self.Bind(wx.EVT_MENU, lambda _: self.duplicate_rows(_rows),         id=id_dup)
        self.Bind(wx.EVT_MENU, lambda _: self.swap_source_xy(_rows),         id=id_swap_src)
        self.Bind(wx.EVT_MENU, lambda _: self.swap_target_xy(_rows),         id=id_swap_dst)
        self.Bind(wx.EVT_MENU, lambda _: self.swap_source_xy(),              id=id_swap_src_all)
        self.Bind(wx.EVT_MENU, lambda _: self.swap_target_xy(),              id=id_swap_dst_all)

        self.PopupMenu(menu)
        menu.Destroy()

    def duplicate_rows(self, rows: List[int] = None):
        """
        Дублирует указанные строки, вставляя копии сразу после последней
        из выбранных строк. Порядок дублей совпадает с порядком оригиналов.
        """
        if rows is None:
            rows = self._get_affected_rows()
        if not rows:
            return

        rows = sorted(rows)
        insert_pos = rows[-1] + 1   # вставляем после последней выбранной строки

        # Снимок данных ДО вставки (индексы не съедут)
        snapshots: List[dict] = []
        for row in rows:
            snap = {}
            for col in range(_Col.COUNT):
                if col not in _READONLY_COLS:
                    snap[col] = self.GetCellValue(row, col)
            snapshots.append(snap)

        # Вставляем пустые строки
        self.InsertRows(insert_pos, len(rows))

        # Инициализируем и заполняем новые строки
        for i, snap in enumerate(snapshots):
            new_row = insert_pos + i
            # plan/h берём из снимка
            plan = snap.get(_Col.USE_PLAN, "1") == "1"
            h    = snap.get(_Col.USE_H,    "1") == "1"
            self._init_row(new_row, plan=plan, h=h)
            for col, val in snap.items():
                if col not in _CHECKBOX_COLS:   # чекбоксы уже выставлены в _init_row
                    self.SetCellValue(new_row, col, val)

        # Выделяем только что вставленные строки
        self.ClearSelection()
        if snapshots:
            self.SelectBlock(
                insert_pos, 0,
                insert_pos + len(rows) - 1, _Col.COUNT - 1,
            )
            self.SetGridCursor(insert_pos, _Col.NAME)
            self.MakeCellVisible(insert_pos, 0)

        self.ForceRefresh()
        self._notify_changed()

    def swap_source_xy(self, rows: List[int] = None):
        """Меняет X₁ ↔ Y₁. Если rows=None — во всех строках."""
        if rows is None:
            rows = range(self.GetNumberRows())
        for row in rows:
            x = self.GetCellValue(row, _Col.X1)
            y = self.GetCellValue(row, _Col.Y1)
            self.SetCellValue(row, _Col.X1, y)
            self.SetCellValue(row, _Col.Y1, x)
        self.ForceRefresh()
        self._notify_changed()

    def swap_target_xy(self, rows: List[int] = None):
        """Меняет X₂ ↔ Y₂. Если rows=None — во всех строках."""
        if rows is None:
            rows = range(self.GetNumberRows())
        for row in rows:
            x = self.GetCellValue(row, _Col.X2)
            y = self.GetCellValue(row, _Col.Y2)
            self.SetCellValue(row, _Col.X2, y)
            self.SetCellValue(row, _Col.Y2, x)
        self.ForceRefresh()
        self._notify_changed()

    def set_data(self, data: List[dict]):
        """
        Загрузить данные в таблицу.

        Каждый элемент списка — словарь::

            {
                'enabled_plan': bool,   # чекбокс план
                'enabled_h':    bool,   # чекбокс высота
                'name': str,
                'x1': str,  'y1': str,  'h1': str,
                'x2': str,  'y2': str,  'h2': str,
            }
        """
        self._busy = True
        self._computed_cells.clear()
        if self.GetNumberRows():
            self.DeleteRows(0, self.GetNumberRows())

        n = max(len(data), self.MIN_ROWS)
        self.AppendRows(n)
        for row in range(n):
            self._init_row(row)

        for row, d in enumerate(data):
            self.SetCellValue(row, _Col.USE_PLAN, "1" if d.get("enabled_plan", True) else "")
            self.SetCellValue(row, _Col.USE_H,    "1" if d.get("enabled_h",    True) else "")
            self.SetCellValue(row, _Col.NAME, str(d.get("name", "")))
            self.SetCellValue(row, _Col.X1,   str(d.get("x1",   "")))
            self.SetCellValue(row, _Col.Y1,   str(d.get("y1",   "")))
            self.SetCellValue(row, _Col.H1,   str(d.get("h1",   "")))
            self.SetCellValue(row, _Col.X2,   str(d.get("x2",   "")))
            self.SetCellValue(row, _Col.Y2,   str(d.get("y2",   "")))
            self.SetCellValue(row, _Col.H2,   str(d.get("h2",   "")))

        self._busy = False
        self.ForceRefresh()
        self._notify_changed()

    def get_data(self) -> List[dict]:
        """
        Вернуть данные таблицы (пустые строки пропускаются).
        Формат словарей — тот же, что принимает :meth:`set_data`.
        """
        result = []
        for row in range(self.GetNumberRows()):
            x1 = self.GetCellValue(row, _Col.X1).strip()
            y1 = self.GetCellValue(row, _Col.Y1).strip()
            x2 = self.GetCellValue(row, _Col.X2).strip()
            y2 = self.GetCellValue(row, _Col.Y2).strip()
            if not (x1 or y1 or x2 or y2):
                continue
            result.append({
                "enabled_plan": self.GetCellValue(row, _Col.USE_PLAN) == "1",
                "enabled_h":    self.GetCellValue(row, _Col.USE_H)    == "1",
                "name": self.GetCellValue(row, _Col.NAME).strip(),
                "x1": x1, "y1": y1,
                "h1": self.GetCellValue(row, _Col.H1).strip(),
                "x2": x2, "y2": y2,
                "h2": self.GetCellValue(row, _Col.H2).strip(),
            })
        return result

    def update_residuals(
        self,
        residuals: List[Optional[Tuple]],
        threshold: float = _DEFAULT_THRESHOLD,
    ):
        """
        Обновить **только** столбцы dX / dY / dH — остальные ячейки не трогает.

        ``residuals[i]`` — кортеж для i-й физической строки таблицы:

        - ``(dx, dy)``        — только плановые невязки
        - ``(dx, dy, dh)``    — плановые + высотная
        - ``None``            — строка не участвовала в расчёте
        """
        for row, res in enumerate(residuals):
            if row >= self.GetNumberRows():
                break
            if res is None:
                for col in (_Col.DX, _Col.DY, _Col.DH):   # ← только свои колонки
                    self.SetCellValue(row, col, "")
                    self.SetCellBackgroundColour(row, col, _CLR_NA)
                continue

            dx = res[0] if len(res) > 0 else None
            dy = res[1] if len(res) > 1 else None
            dh = res[2] if len(res) > 2 else None

            plan_bad = (dx is not None and abs(dx) > threshold) or \
                       (dy is not None and abs(dy) > threshold)
            h_bad    = (dh is not None and abs(dh) > threshold)

            for col, val, bad in (
                (_Col.DX, dx, plan_bad),
                (_Col.DY, dy, plan_bad),
                (_Col.DH, dh, h_bad),
            ):
                if val is None:
                    self.SetCellValue(row, col, "")
                    self.SetCellBackgroundColour(row, col, _CLR_NA)
                else:
                    self.SetCellValue(row, col, f"{val:+.4f}")
                    clr = _CLR_BAD if bad else _CLR_OK
                    self.SetCellBackgroundColour(row, col, clr)

        self.ForceRefresh()

    def update_metric_residuals(
        self,
        residuals: List[Optional[Tuple]],
        threshold: float = _DEFAULT_THRESHOLD,
    ):
        """
        Обновить столбцы dE / dN / dU (невязки в метрах).
        Формат residuals[i]: (de, dn, du) или None.
        """
        for row, res in enumerate(residuals):
            if row >= self.GetNumberRows():
                break
            if res is None:
                for col in (_Col.DE, _Col.DN, _Col.DU):   # ← только свои колонки
                    self.SetCellValue(row, col, "")
                    self.SetCellBackgroundColour(row, col, _CLR_NA)
                continue

            de = res[0] if len(res) > 0 else None
            dn = res[1] if len(res) > 1 else None
            du = res[2] if len(res) > 2 else None

            plan_bad = (de is not None and abs(de) > threshold) or \
                    (dn is not None and abs(dn) > threshold)
            h_bad    =  du is not None and abs(du) > threshold

            for col, val, bad in (
                (_Col.DE, de, plan_bad),
                (_Col.DN, dn, plan_bad),
                (_Col.DU, du, h_bad),
            ):
                if val is None:
                    self.SetCellValue(row, col, "")
                    self.SetCellBackgroundColour(row, col, _CLR_NA)
                else:
                    self.SetCellValue(row, col, f"{val:+.4f}")
                    self.SetCellBackgroundColour(row, col, _CLR_BAD if bad else _CLR_OK)

        self.ForceRefresh()

    def clear_residuals(self):
        """Сбросить все невязки (например, при изменении входных данных)."""
        n = self.GetNumberRows()
        self.update_residuals([None] * n)
        self.update_metric_residuals([None] * n)
        self.clear_geoid_heights()

    # ── Вспомогательные ───────────────────────────────────────────────────────

    def _parse_tabular(self, text: str) -> List[List[str]]:
        """
        Универсальный парсер строк из буфера обмена.
        Приоритет разделителей: Tab → ; → , (только если dec_sep != ',') → пробел.
        """
        result = []
        for line in text.splitlines():
            line = line.rstrip("\r")
            if not line.strip():
                continue
            if "\t" in line:
                result.append(line.split("\t"))
            elif ";" in line:
                result.append(line.split(";"))
            elif "," in line and self._dec_sep != ",":
                # Запятую как разделитель полей используем только если
                # она НЕ является десятичным разделителем в системе
                result.append(line.split(","))
            else:
                result.append(line.split())
        return [r for r in result if any(c.strip() for c in r)]
    
    def update_geoid_heights(
        self,
        src_info: List[Optional[Tuple[float, float]]],
        tgt_info: List[Optional[Tuple[float, float]]],
    ):
        """
        Обновить столбцы «H исх. скорр.» и «H опорн. скорр.».

        src_info[i] / tgt_info[i]:
        (h_corrected, n_geoid) — показывает «120.4530 (ζ=+28.1234)»
        None                   — ячейка пуста (серый фон)
        """
        for col, info_list in (
            (_Col.H1_CORR, src_info),
            (_Col.H2_CORR, tgt_info),
        ):
            for row, info in enumerate(info_list):
                if row >= self.GetNumberRows():
                    break
                if info is None:
                    self.SetCellValue(row, col, "")
                    self.SetCellBackgroundColour(row, col, _CLR_NA)
                else:
                    h_corr, n_geoid = info
                    self.SetCellValue(row, col, f"{h_corr:.4f} (ζ={n_geoid:+.4f})")
                    self.SetCellBackgroundColour(row, col, _CLR_GEOID)
        self.ForceRefresh()

    def clear_geoid_heights(self):
        """Сбросить столбцы геоида (вызывается при изменении входных данных)."""
        n = self.GetNumberRows()
        for col in (_Col.H1_CORR, _Col.H2_CORR):
            for row in range(n):
                self.SetCellValue(row, col, "")
                self.SetCellBackgroundColour(row, col, _CLR_NA)
        self.ForceRefresh()
    
    def _mark_computed_cell(self, row: int, col: int):
        """Помечает ячейку как автоматически вычисленную."""
        self.SetCellFont(row, col, self._bold_cell_font)
        self._computed_cells.add((row, col))

    def _clear_computed_cell(self, row: int, col: int):
        """Снимает пометку автоматически вычисленной ячейки."""
        if (row, col) in self._computed_cells:
            self.SetCellFont(row, col, self._normal_cell_font)
            self._computed_cells.discard((row, col))

    def clear_computed_marks(self):
        """Сбросить жирное выделение у всех автоматически вычисленных ячеек."""
        for row, col in list(self._computed_cells):
            self.SetCellFont(row, col, self._normal_cell_font)
        self._computed_cells.clear()
        self.ForceRefresh()

    def row_has_computed_coordinates(self, row: int) -> bool:
        """
        True, если в строке есть автоматически вычисленные координаты.
        Такие строки не должны участвовать в следующем расчёте МНК,
        пока пользователь не отредактирует их вручную.
        """
        coord_cols = {
            _Col.X1, _Col.Y1, _Col.H1,
            _Col.X2, _Col.Y2, _Col.H2,
        }
        return any((row, col) in self._computed_cells for col in coord_cols)

    def get_data_with_row_indices(self) -> List[tuple[int, dict]]:
        """
        То же, что get_data(), но возвращает ещё и физический индекс строки грида.

        Нужно для корректного разворота невязок и автозаполнения обратно
        в реальные строки таблицы, даже если между ними есть пустые строки.
        """
        result = []
        for row in range(self.GetNumberRows()):
            x1 = self.GetCellValue(row, _Col.X1).strip()
            y1 = self.GetCellValue(row, _Col.Y1).strip()
            x2 = self.GetCellValue(row, _Col.X2).strip()
            y2 = self.GetCellValue(row, _Col.Y2).strip()
            if not (x1 or y1 or x2 or y2):
                continue
            result.append((
                row,
                {
                    "enabled_plan": self.GetCellValue(row, _Col.USE_PLAN) == "1",
                    "enabled_h":    self.GetCellValue(row, _Col.USE_H)    == "1",
                    "name": self.GetCellValue(row, _Col.NAME).strip(),
                    "x1": x1,
                    "y1": y1,
                    "h1": self.GetCellValue(row, _Col.H1).strip(),
                    "x2": x2,
                    "y2": y2,
                    "h2": self.GetCellValue(row, _Col.H2).strip(),
                }
            ))
        return result

    def fill_missing_coordinates(self, predictions: dict[int, dict[str, str]]) -> int:
        """
        Заполняет пустые координатные ячейки вычисленными значениями и помечает
        их жирным шрифтом.

        predictions:
            {
                row_index: {
                    "x1": "...",
                    "y1": "...",
                    "h1": "...",
                    "x2": "...",
                    "y2": "...",
                    "h2": "...",
                }
            }

        Возвращает количество реально заполненных ячеек.
        """
        key_to_col = {
            "x1": _Col.X1, "y1": _Col.Y1, "h1": _Col.H1,
            "x2": _Col.X2, "y2": _Col.Y2, "h2": _Col.H2,
        }

        filled = 0
        self._busy = True
        try:
            for row, data in predictions.items():
                if row >= self.GetNumberRows():
                    continue
                for key, value in data.items():
                    if value is None or value == "":
                        continue
                    col = key_to_col[key]
                    if not self.GetCellValue(row, col).strip():
                        self.SetCellValue(row, col, value)
                        self._mark_computed_cell(row, col)
                        filled += 1
        finally:
            self._busy = False

        self.ForceRefresh()
        return filled

    def update_geoid_heights_partial(self, src_updates, tgt_updates):
        for row, (h, n) in src_updates.items():
            self.SetCellValue(row, _Col.H1_CORR, f"{h:.4f} (ζ {n:+.4f})")
            self.SetCellBackgroundColour(row, _Col.H1_CORR, _CLR_GEOID)
        for row, (h, n) in tgt_updates.items():
            self.SetCellValue(row, _Col.H2_CORR, f"{h:.4f} (ζ {n:+.4f})")
            self.SetCellBackgroundColour(row, _Col.H2_CORR, _CLR_GEOID)
        self.ForceRefresh()

    def clear_autofilled_coordinates(self):
        """
        Удаляет значения только из автодостроенных координатных ячеек
        (помеченных жирным), и снимает пометки.
        """
        coord_cols = {_Col.X1, _Col.Y1, _Col.H1, _Col.X2, _Col.Y2, _Col.H2}
        self._busy = True
        try:
            for row, col in list(self._computed_cells):
                if col in coord_cols and row < self.GetNumberRows():
                    self.SetCellValue(row, col, "")
                    self.SetCellFont(row, col, self._normal_cell_font)
                self._computed_cells.discard((row, col))
        finally:
            self._busy = False
        self.ForceRefresh()