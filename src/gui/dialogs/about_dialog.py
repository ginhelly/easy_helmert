"""Диалог «О программе»."""

from __future__ import annotations
import wx

from utils.debug_flags import (
    enable_geoid_debug, is_geoid_debug_enabled,
    is_using_global_undulation_for_calc, set_use_global_undulation_for_calc,
)

_EASTER_EGG_CLICKS = 5


class AboutDialog(wx.Dialog):

    def __init__(self, parent: wx.Window):
        super().__init__(parent, title="О программе", style=wx.DEFAULT_DIALOG_STYLE)
        self._title_click_count = 0
        self._build_ui()
        self.Centre()

    def _build_ui(self):
        panel = wx.Panel(self)
        main  = wx.BoxSizer(wx.VERTICAL)
        self._panel = panel
        self._main_sizer = main

        # ── Название ─────────────────────────────────────────────────────────
        title_font = self.GetFont()
        title_font.SetPointSize(16)
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)

        lbl_title = wx.StaticText(panel, label="Easy Helmert v0.9.2")
        lbl_title.SetFont(title_font)
        lbl_title.Bind(wx.EVT_LEFT_DOWN, self._on_title_click)

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

        # ── Секретный debug-переключатель (виден только в debug-режиме) ────────
        self.chk_use_global_undulation = wx.CheckBox(
            panel,
            label="Использовать при расчётах ондуляции высот, "
                  "рассчитанные по захардкоженным параметрам",
        )
        self.chk_use_global_undulation.SetValue(is_using_global_undulation_for_calc())
        self.chk_use_global_undulation.Bind(wx.EVT_CHECKBOX, self._on_toggle_use_global)
        self.chk_use_global_undulation.Show(is_geoid_debug_enabled())
        main.Add(self.chk_use_global_undulation, 0, wx.ALIGN_CENTRE | wx.ALL, 8)

        # ── Кнопка ───────────────────────────────────────────────────────────
        btn_ok = wx.Button(panel, wx.ID_OK, "Закрыть")
        btn_ok.SetDefault()
        main.Add(btn_ok, 0, wx.ALIGN_CENTRE | wx.ALL, 12)

        panel.SetSizer(main)
        main.Fit(self)

    def _on_title_click(self, event):
        event.Skip()
        self._title_click_count += 1
        if self._title_click_count >= _EASTER_EGG_CLICKS:
            self._title_click_count = 0
            enable_geoid_debug()
            self.chk_use_global_undulation.Show(True)
            self._panel.Layout()
            self._main_sizer.Fit(self)
            wx.MessageBox(
                "Debug-режим геоида включён: рядом со скорректированными высотами "
                "будет показана ондуляция по жёстко заданному \"глобальному\" эталону "
                "(СК-42 → WGS-84, ГОСТ 32453-2017) для сравнения с локальным МНК.\n\n"
                "Действует до перезапуска приложения.",
                "Debug-режим", wx.OK | wx.ICON_INFORMATION, self,
            )

    def _on_toggle_use_global(self, event):
        set_use_global_undulation_for_calc(self.chk_use_global_undulation.GetValue())
        event.Skip()