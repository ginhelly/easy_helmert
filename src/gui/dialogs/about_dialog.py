"""Диалог «О программе»."""

from __future__ import annotations
import wx


class AboutDialog(wx.Dialog):

    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="О программе", style=wx.DEFAULT_DIALOG_STYLE)
        self._build_ui()
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        main  = wx.BoxSizer(wx.VERTICAL)

        # ── Название ─────────────────────────────────────────────────────────
        title_font = self.GetFont()
        title_font.SetPointSize(16)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)

        lbl_title = wx.StaticText(panel, label="Easy Helmert v0.9.2")
        lbl_title.SetFont(title_font)

        sub_font = self.GetFont()
        sub_font.SetPointSize(9)
        lbl_sub = wx.StaticText(
            panel,
            label="Вычисление 7 параметров преобразования координат"
        )
        lbl_sub.SetFont(sub_font)

        main.Add(lbl_title, 0, wx.ALIGN_CENTRE | wx.TOP | wx.LEFT | wx.RIGHT, 20)
        main.Add(lbl_sub,   0, wx.ALIGN_CENTRE | wx.TOP | wx.LEFT | wx.RIGHT, 4)
        main.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.ALL, 12)

        # ── Текст ─────────────────────────────────────────────────────────────
        about_text = (
            "Программа для расчёта семи параметров перехода Гельмерта\n"
            "между двумя различными системами координат.\n"
            "Для работы нужен набор точек с координатами,\n"
            "определёнными с геодезической точностью в исходной\n"
            "и опорной системах - абсолютный минимум 3 точки\n"
            "с плановыми и высотными координатами.\n"
            "\nПрограмма приводит все исходные координаты\n"
            "к геоцентрическим (XYZ) и использует scipy.optimize.least_squares\n"
            "для подгонки исходной СК к опорной по трём параметрам\n"
            "сдвига, трём параметрам разворота и коэффициенту масштабирования.\n"
            "\nСКО (ECEF) считается только по точкам, участвующим в уравнивании.\n"
            "СКО (ENU) считается по всем добавленным точкам\n"
            "и в подходящей для этого топоцентрической СК.\n"
            "\n"
            "Стек: Python · wxPython · pyproj · scipy · pandas\n"
            "Создана с помощью Claude Sonnet 4.6 и Deepseek\n"
            "Иконки by Pixel perfect - Flaticon (https://www.flaticon.com/free-icons/copy)\n"
            "Основная иконка от BomSymbols (https://icon-icons.com/ru/pack/office/1572)"
        )

        lbl_about = wx.StaticText(panel, label=about_text)
        lbl_about.Wrap(420)
        main.Add(lbl_about, 0, wx.ALL, 16)

        main.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 12)

        # ── Кнопка ───────────────────────────────────────────────────────────
        btn_ok = wx.Button(panel, wx.ID_OK, "Закрыть")
        btn_ok.SetDefault()
        main.Add(btn_ok, 0, wx.ALIGN_CENTRE | wx.ALL, 12)

        panel.SetSizer(main)
        main.Fit(self)