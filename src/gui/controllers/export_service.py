from __future__ import annotations

from typing import Optional

import wx


class ExportService:
    """
    Сервис экспорта:
      - WKT1 / WKT2 / Proj4 в файл
      - копирование WKT1 / WKT2 / Proj4 в буфер
      - сохранение таблицы точек в CSV/TXT
    """

    def __init__(
        self,
        parent: wx.Window,
        coord_grid,
        get_source_crs,
        get_target_crs,
        get_calc_result,
        get_source_label,
        get_src_name,
        get_tgt_name,
        clear_modified,
    ):
        self.parent = parent
        self.coord_grid = coord_grid
        self.get_source_crs = get_source_crs
        self.get_target_crs = get_target_crs
        self.get_calc_result = get_calc_result
        self.get_source_label = get_source_label
        self.get_src_name = get_src_name
        self.get_tgt_name = get_tgt_name
        self.clear_modified = clear_modified

    # ── CRS export ──────────────────────────────────────────────────────────

    def format_crs(self, fmt: str) -> Optional[str]:
        calc_result = self.get_calc_result()
        source_crs = self.get_source_crs()
        target_crs = self.get_target_crs()

        if calc_result is None or source_crs is None:
            wx.MessageBox(
                "Сначала выполните расчёт.",
                "Нет результата",
                wx.OK | wx.ICON_INFORMATION,
                self.parent,
            )
            return None

        display_name = self.get_source_label() or ""

        from utils.crs_export import to_wkt1, to_wkt2, to_proj4
        try:
            if fmt == "wkt1":
                return to_wkt1(source_crs, calc_result.params, display_name)
            if fmt == "wkt2":
                return to_wkt2(source_crs, calc_result.params, display_name, target_crs)
            if fmt == "proj4":
                return to_proj4(source_crs, calc_result.params)
            wx.MessageBox(
                f"Неизвестный формат экспорта: {fmt}",
                "Ошибка",
                wx.OK | wx.ICON_ERROR,
                self.parent,
            )
            return None
        except Exception as e:
            wx.MessageBox(
                f"Не удалось сформировать {fmt.upper()}:\n{e}",
                "Ошибка",
                wx.OK | wx.ICON_ERROR,
                self.parent,
            )
            return None

    def save_crs_to_file(self, fmt: str) -> bool:
        text = self.format_crs(fmt)
        if text is None:
            return False

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
            self.parent,
            f"Сохранить {fmt.upper()}",
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            dlg.SetFilename("result.prj")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return False
            path = dlg.GetPath()

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)
            return True
        except IOError as e:
            wx.MessageBox(str(e), "Ошибка записи", wx.OK | wx.ICON_ERROR, self.parent)
            return False

    def copy_crs_to_clipboard(self, fmt: str) -> bool:
        text = self.format_crs(fmt)
        if text is None:
            return False

        if not wx.TheClipboard.Open():
            wx.MessageBox(
                "Не удалось открыть буфер обмена.",
                "Ошибка",
                wx.OK | wx.ICON_ERROR,
                self.parent,
            )
            return False

        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()

        wx.MessageBox(
            f"Описание проекции в формате {fmt} скопировано в буфер обмена",
            "Копирование успешно",
            wx.OK | wx.ICON_ASTERISK,
            self.parent,
        )
        return True

    # ── Table export ────────────────────────────────────────────────────────

    def save_table_to_file(self) -> bool:
        data = self.coord_grid.get_data()
        if not data:
            wx.MessageBox(
                "Таблица пуста — нечего сохранять.",
                "Нет данных",
                wx.OK | wx.ICON_INFORMATION,
                self.parent,
            )
            return False

        with wx.FileDialog(
            self.parent,
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
                return False
            path = dlg.GetPath()

        ext = path.rsplit(".", 1)[-1].lower()
        sep = ";" if ext == "csv" else "\t"

        src_name = self.get_src_name()
        tgt_name = self.get_tgt_name()

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
            rows.append(sep.join([
                "1" if d.get("enabled_plan") else "0",
                "1" if d.get("enabled_h") else "0",
                str(d.get("name", "")),
                str(d.get("x1", "")),
                str(d.get("y1", "")),
                str(d.get("h1", "")),
                str(d.get("x2", "")),
                str(d.get("y2", "")),
                str(d.get("h2", "")),
            ]))

        try:
            with open(path, "w", encoding="utf-8-sig", newline="\n") as f:
                f.write("\n".join(rows))
            self.clear_modified("save_table")
            return True
        except IOError as e:
            wx.MessageBox(str(e), "Ошибка записи", wx.OK | wx.ICON_ERROR, self.parent)
            return False
            
    def export_calibration_dialog(self) -> bool:
        """Экспорт текущей таблицы в файл калибровки."""
        from core.calibration_importers import (
            save_calibration_file,
            export_wildcard,
            UnsupportedFormatError,
            CalibrationPoint,
        )

        data = self.coord_grid.get_data()
        if not data:
            wx.MessageBox(
                "Таблица пуста.",
                "Нет данных",
                wx.OK | wx.ICON_INFORMATION,
                self.parent,
            )
            return False

        with wx.FileDialog(
            self.parent,
            "Экспорт файла калибровки",
            wildcard=export_wildcard(),
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT,
        ) as dlg:
            dlg.SetFilename("calibration.loc")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return False
            filepath = dlg.GetPath()

        points = [
            CalibrationPoint(
                name=d.get("name", ""),
                x1=d.get("x1", ""),
                y1=d.get("y1", ""),
                h1=d.get("h1", ""),
                x2=d.get("x2", ""),
                y2=d.get("y2", ""),
                h2=d.get("h2", ""),
                enabled_plan=d.get("enabled_plan", True),
                enabled_h=d.get("enabled_h", True),
            )
            for d in data
        ]

        try:
            save_calibration_file(filepath, points)
            wx.MessageBox(
                "Файл калибровки успешно сохранён.",
                "Экспорт завершён",
                wx.OK | wx.ICON_INFORMATION,
                self.parent,
            )
            return True
        except (UnsupportedFormatError, IOError, ValueError) as e:
            wx.MessageBox(
                str(e),
                "Ошибка экспорта",
                wx.OK | wx.ICON_ERROR,
                self.parent,
            )
            return False