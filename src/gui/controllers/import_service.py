from __future__ import annotations

from typing import Dict, List, Tuple

import wx


class ImportService:
    """
    Сервис импорта/слияния табличных данных.
    Не трогает wx-форму напрямую, работает через переданные callback'и.
    """

    _COORD_KEYS = ("x1", "y1", "h1", "x2", "y2", "h2")
    _FLAG_KEYS = ("enabled_plan", "enabled_h")

    def __init__(
        self,
        parent: wx.Window,
        coord_grid,
        mark_modified,
        clear_residuals,
        clear_result_text,
    ):
        self.parent = parent
        self.coord_grid = coord_grid
        self.mark_modified = mark_modified
        self.clear_residuals = clear_residuals
        self.clear_result_text = clear_result_text

    # ── Public API ─────────────────────────────────────────────────────────

    def import_from_text_dialog(self) -> bool:
        with wx.FileDialog(
            self.parent,
            "Открыть файл с координатами",
            wildcard=(
                "Текстовые файлы (*.txt;*.csv;*.tsv)|*.txt;*.csv;*.tsv"
                "|Все файлы (*.*)|*.*"
            ),
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as file_dlg:
            if file_dlg.ShowModal() == wx.ID_CANCEL:
                return False
            filepath = file_dlg.GetPath()

        from gui.dialogs.import_dialog import ImportDialog

        with ImportDialog(self.parent, filepath) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            imported = dlg.get_import_data()

        if not imported:
            wx.MessageBox(
                "Нет данных для импорта — возможно, не назначен ни один столбец\n"
                "или файл пустой.",
                "Импорт",
                wx.OK | wx.ICON_INFORMATION,
            )
            return False

        n_added, n_updated = self.merge_into_grid(imported)

        self.mark_modified("import_txt")
        self.clear_residuals()
        self.clear_result_text()

        wx.MessageBox(
            f"Импорт завершён:\n"
            f"  • обновлено точек: {n_updated}\n"
            f"  • добавлено точек: {n_added}",
            "Импорт завершён",
            wx.OK | wx.ICON_INFORMATION,
        )
        return True

    def import_calibration_dialog(self) -> bool:
        from core.calibration_importers import (
            load_calibration_file,
            UnsupportedFormatError,
            WILDCARD,
        )

        with wx.FileDialog(
            self.parent,
            "Открыть файл калибровки",
            wildcard=WILDCARD,
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dlg:
            if dlg.ShowModal() == wx.ID_CANCEL:
                return False
            filepath = dlg.GetPath()

        try:
            points = load_calibration_file(filepath)
        except UnsupportedFormatError as e:
            wx.MessageBox(str(e), "Неподдерживаемый формат", wx.OK | wx.ICON_WARNING, self.parent)
            return False
        except (ValueError, IOError) as e:
            wx.MessageBox(str(e), "Ошибка импорта", wx.OK | wx.ICON_ERROR, self.parent)
            return False

        imported = [pt.to_dict() for pt in points]
        n_added, n_updated = self.merge_into_grid(imported)

        self.mark_modified("import_calibration")
        self.clear_residuals()
        self.clear_result_text()

        wx.MessageBox(
            f"Импорт завершён:\n"
            f"  • обновлено точек: {n_updated}\n"
            f"  • добавлено точек: {n_added}",
            "Импорт калибровки",
            wx.OK | wx.ICON_INFORMATION,
        )
        return True

    def merge_into_grid(self, imported: List[dict]) -> Tuple[int, int]:
        current: List[dict] = self.coord_grid.get_data()

        existing_idx: Dict[str, List[int]] = {}
        for i, row in enumerate(current):
            name = row.get("name", "").strip()
            if name:
                existing_idx.setdefault(name, []).append(i)

        new_rows: List[dict] = []
        new_by_name: Dict[str, int] = {}

        n_added, n_updated = 0, 0

        for imp in imported:
            imp_name = imp.get("name", "").strip()
            if not imp_name:
                continue

            if imp_name in existing_idx:
                for idx in existing_idx[imp_name]:
                    self._merge_row(current[idx], imp)
                n_updated += 1
                continue

            if imp_name in new_by_name:
                nr = new_rows[new_by_name[imp_name]]
                self._merge_row(nr, imp)
                n_updated += 1
                continue

            blank = {
                "enabled_plan": imp.get("enabled_plan", True),
                "enabled_h": imp.get("enabled_h", True),
                "name": imp_name,
                "x1": "",
                "y1": "",
                "h1": "",
                "x2": "",
                "y2": "",
                "h2": "",
            }
            self._merge_row(blank, imp)

            new_by_name[imp_name] = len(new_rows)
            new_rows.append(blank)
            n_added += 1

        self.coord_grid.set_data(current + new_rows)
        return n_added, n_updated

    # ── Internal ────────────────────────────────────────────────────────────

    def _merge_row(self, dst: dict, src: dict) -> None:
        for key in self._COORD_KEYS:
            val = src.get(key, "")
            if val:
                dst[key] = val
        for flag in self._FLAG_KEYS:
            if flag in src:
                dst[flag] = src[flag]