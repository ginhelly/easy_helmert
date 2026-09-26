"""
SavePresetDialog — маленький диалог "Название + Описание" для сохранения
текущего результата (посчитанного МНК или заданного вручную) в
пользовательскую БД параметров (core/user_transforms_db.py).

Сам сохранением не занимается — только собирает name/description,
сохранение делает вызывающий код (у него уже есть params/method).
"""
from __future__ import annotations

from typing import Optional

import wx


class SavePresetDialog(wx.Dialog):

    def __init__(self, parent: wx.Window, initial_description: str = ""):
        super().__init__(
            parent, title="Сохранить параметры в базу",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        root = wx.BoxSizer(wx.VERTICAL)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(wx.StaticText(self, label="Название:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.txt_name = wx.TextCtrl(self, size=(320, -1))
        name_row.Add(self.txt_name, 1)
        root.Add(name_row, 0, wx.EXPAND | wx.ALL, 8)

        root.Add(wx.StaticText(self, label="Описание:"), 0, wx.LEFT | wx.RIGHT, 8)
        self.txt_description = wx.TextCtrl(
            self, value=initial_description,
            style=wx.TE_MULTILINE, size=(320, 100),
        )
        root.Add(self.txt_description, 1, wx.EXPAND | wx.ALL, 8)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self, wx.ID_OK, "Сохранить")
        ok_btn.SetDefault()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Отмена")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        self.SetSizer(root)
        self.Fit()
        self.SetMinSize((420, 260))
        self.Centre()

    def _on_ok(self, event):
        if not self.txt_name.GetValue().strip():
            wx.MessageBox("Укажите название.", "Ошибка ввода", wx.OK | wx.ICON_ERROR, self)
            return
        event.Skip()

    def get_name(self) -> str:
        return self.txt_name.GetValue().strip()

    def get_description(self) -> str:
        return self.txt_description.GetValue().strip()
