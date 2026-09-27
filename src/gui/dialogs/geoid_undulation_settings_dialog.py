"""
GeoidUndulationSettingsDialog — диалог "Программа → Настройки": выбор
способа получения ондуляции геоида на нужном эллипсоиде
(core.geoid_correction.GeoidUndulationMethod). Настройка общая для
программы, не привязана к конкретному расчёту — хранится через
core.app_settings.
"""
from __future__ import annotations

from typing import Optional

import wx

from core.geoid_correction import GeoidUndulationMethod
from core.models import TransformationParams


class GeoidUndulationSettingsDialog(wx.Dialog):

    def __init__(
        self,
        parent: wx.Window,
        method: GeoidUndulationMethod,
        preset_id: Optional[int] = None,
        preset_name: str = "",
        preset_params: Optional[TransformationParams] = None,
    ):
        super().__init__(
            parent, title="Настройки",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )

        self._preset_id: Optional[int] = preset_id
        self._preset_name: str = preset_name
        self._preset_params: Optional[TransformationParams] = preset_params

        root = wx.BoxSizer(wx.VERTICAL)

        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Расчёт ондуляций геоида")
        panel = box.GetStaticBox()

        self.rb_naive = wx.RadioButton(
            panel, label="По приближённым (наивным) параметрам перехода — как сейчас",
            style=wx.RB_GROUP,
        )
        self.rb_trusted = wx.RadioButton(
            panel, label="По заданным параметрам перехода",
        )
        self.rb_raw = wx.RadioButton(
            panel, label="Принимать N_WGS за N_исх",
        )

        box.Add(self.rb_naive, 0, wx.ALL, 6)

        trusted_row = wx.BoxSizer(wx.HORIZONTAL)
        trusted_row.Add(self.rb_trusted, 0, wx.ALIGN_CENTER_VERTICAL)
        self.btn_pick_preset = wx.Button(panel, label="Выбрать...")
        trusted_row.Add(self.btn_pick_preset, 0, wx.LEFT, 8)
        box.Add(trusted_row, 0, wx.ALL, 6)

        self.lbl_preset = wx.StaticText(panel, label=self._preset_label())
        box.Add(self.lbl_preset, 0, wx.LEFT | wx.BOTTOM, 26)

        box.Add(self.rb_raw, 0, wx.ALL, 6)

        root.Add(box, 0, wx.EXPAND | wx.ALL, 10)

        btn_sizer = wx.StdDialogButtonSizer()
        ok_btn = wx.Button(self, wx.ID_OK, "ОК")
        ok_btn.SetDefault()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Отмена")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        initial_radio = {
            GeoidUndulationMethod.NAIVE_FIT: self.rb_naive,
            GeoidUndulationMethod.TRUSTED_PARAMS: self.rb_trusted,
            GeoidUndulationMethod.RAW_AS_IS: self.rb_raw,
        }.get(method, self.rb_naive)
        initial_radio.SetValue(True)

        self.btn_pick_preset.Bind(wx.EVT_BUTTON, self._on_pick_preset)
        self.rb_naive.Bind(wx.EVT_RADIOBUTTON, self._update_enabled)
        self.rb_trusted.Bind(wx.EVT_RADIOBUTTON, self._update_enabled)
        self.rb_raw.Bind(wx.EVT_RADIOBUTTON, self._update_enabled)
        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        self.SetSizer(root)
        self.Fit()
        self.SetMinSize((480, 260))
        self.Centre()
        self._update_enabled()

    def _preset_label(self) -> str:
        return f"Выбрано: {self._preset_name}" if self._preset_name else "Набор параметров не выбран"

    def _update_enabled(self, event=None):
        self.btn_pick_preset.Enable(self.rb_trusted.GetValue())
        if event is not None:
            event.Skip()

    def _on_pick_preset(self, event):
        from gui.dialogs.transform_preset_picker_dialog import TransformPresetPickerDialog
        with TransformPresetPickerDialog(self) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._preset_params = dlg.get_params()
                self._preset_id = dlg.get_preset_id()
                self._preset_name = dlg.get_preset_name()
                self.lbl_preset.SetLabel(self._preset_label())
                self.Layout()

    def _on_ok(self, event):
        if self.rb_trusted.GetValue() and self._preset_params is None:
            wx.MessageBox(
                "Выберите набор параметров.", "Настройки",
                wx.OK | wx.ICON_ERROR, self,
            )
            return
        event.Skip()

    # ── Публичный API ─────────────────────────────────────────────────────────

    def get_method(self) -> GeoidUndulationMethod:
        if self.rb_trusted.GetValue():
            return GeoidUndulationMethod.TRUSTED_PARAMS
        if self.rb_raw.GetValue():
            return GeoidUndulationMethod.RAW_AS_IS
        return GeoidUndulationMethod.NAIVE_FIT

    def get_preset_id(self) -> Optional[int]:
        return self._preset_id

    def get_preset_name(self) -> str:
        return self._preset_name

    def get_preset_params(self) -> Optional[TransformationParams]:
        return self._preset_params
