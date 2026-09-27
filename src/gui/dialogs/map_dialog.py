from __future__ import annotations

import json
from typing import Optional

import wx
import wx.html2 as webview

from core.geoid_correction import GeoidAction
from core.models import TransformationParams
from gui.utils.map_html import render_map_html
from gui.utils.kml_export import build_kml
from gui.utils.deviation_grid import compute_deviation_grid

_DEVIATION_MODES = [
    ("mag", "Модуль |Δ|"),
    ("dE",  "По E"),
    ("dN",  "По N"),
    ("dU",  "По U"),
]


class MapDialog(wx.Dialog):
    def __init__(self, parent, title: str = "Точки на карте", size=(980, 700)):
        super().__init__(parent, title=title, size=size,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        if webview.WebView.IsBackendAvailable(webview.WebViewBackendEdge):
            self.web = webview.WebView.New(self, backend=webview.WebViewBackendEdge)
        else:
            from gui.dialogs.webview2_help_dialog import WebView2HelpDialog
            with WebView2HelpDialog(self) as dlg:
                dlg.ShowModal()
            self.web = webview.WebView.New(self)  # fallback

        self._src_points = []
        self._tgt_points = []
        self._title = title

        # ── Контекст для карты отклонений ────────────────────────────────
        self._source_crs = None
        self._target_crs = None
        self._current_params: Optional[TransformationParams] = None
        self._src_action: GeoidAction = GeoidAction.NOTHING
        self._tgt_action: GeoidAction = GeoidAction.NOTHING
        self._delta_zeta_mean: Optional[float] = None
        self._reference_params: Optional[TransformationParams] = None
        self._reference_label: str = ""
        self._last_bounds: Optional[tuple] = None
        self._last_geojson: Optional[dict] = None

        s = wx.BoxSizer(wx.VERTICAL)
        s.Add(self.web, 1, wx.EXPAND | wx.ALL, 6)

        # ── Ряд управления картой отклонений ────────────────────────────
        dev_row = wx.BoxSizer(wx.HORIZONTAL)
        self.chk_deviation = wx.CheckBox(self, label="Карта отклонений")
        self.btn_reference_params = wx.Button(self, label="Опорные параметры...")
        self.lbl_reference = wx.StaticText(self, label="не выбраны")
        self.choice_deviation_mode = wx.Choice(self, choices=[lbl for _, lbl in _DEVIATION_MODES])
        self.choice_deviation_mode.SetSelection(0)
        self.choice_deviation_mode.Enable(False)

        dev_row.Add(self.chk_deviation, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        dev_row.Add(self.btn_reference_params, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        dev_row.Add(self.lbl_reference, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 12)
        dev_row.Add(wx.StaticText(self, label="Режим:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        dev_row.Add(self.choice_deviation_mode, 0, wx.ALIGN_CENTER_VERTICAL)
        s.Add(dev_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_export_kml = wx.Button(self, label="Экспорт KML...")
        self.btn_close = wx.Button(self, wx.ID_CLOSE, "Закрыть")

        btns.Add(self.btn_export_kml, 0, wx.RIGHT, 8)
        btns.AddStretchSpacer(1)
        btns.Add(self.btn_close, 0)

        s.Add(btns, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)

        self.SetSizer(s)
        self.CentreOnParent()

        self.btn_export_kml.Bind(wx.EVT_BUTTON, self.on_export_kml)
        self.btn_close.Bind(wx.EVT_BUTTON, lambda e: self.EndModal(wx.ID_CLOSE))

        self.chk_deviation.Bind(wx.EVT_CHECKBOX, self._on_toggle_deviation)
        self.btn_reference_params.Bind(wx.EVT_BUTTON, self._on_pick_reference)
        self.choice_deviation_mode.Bind(wx.EVT_CHOICE, self._on_mode_changed)

        self.web.AddScriptMessageHandler("pyBridge")
        self.web.Bind(webview.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self._on_js_message)

    def set_points(self, src_points: list[dict], tgt_points: list[dict], title: str = "Точки калибровки"):
        self._src_points = list(src_points or [])
        self._tgt_points = list(tgt_points or [])
        self._title = title

        html = render_map_html(title, self._src_points, self._tgt_points)
        self.web.SetPage(html, "https://easyhelmert.local/")  # base URL для referer

    def set_transform_context(
        self, source_crs, target_crs, current_params: TransformationParams,
        src_action: GeoidAction = GeoidAction.NOTHING,
        tgt_action: GeoidAction = GeoidAction.NOTHING,
        delta_zeta_mean: Optional[float] = None,
    ):
        """
        Нужен для карты отклонений: текущие параметры/СК главного окна и
        его настройки учёта геоида (те же, что реально применялись в
        последнем расчёте) — оба перехода (текущими/опорными параметрами)
        учитывают ондуляцию EGM2008 так же, как основной расчёт.
        """
        self._source_crs = source_crs
        self._target_crs = target_crs
        self._current_params = current_params
        self._src_action = src_action
        self._tgt_action = tgt_action
        self._delta_zeta_mean = delta_zeta_mean

    def on_export_kml(self, event):
        kml = build_kml(self._src_points, self._tgt_points, self._title)

        with wx.FileDialog(
            self,
            "Сохранить KML",
            wildcard="KML файл (*.kml)|*.kml",
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        ) as dlg:
            dlg.SetFilename("calibration_points.kml")
            if dlg.ShowModal() == wx.ID_CANCEL:
                return
            path = dlg.GetPath()

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(kml)
            wx.MessageBox("KML сохранён.", "Экспорт", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.MessageBox(f"Ошибка сохранения:\n{e}", "Ошибка", wx.OK | wx.ICON_ERROR)

    # ── Карта отклонений ─────────────────────────────────────────────────────

    def _on_toggle_deviation(self, event):
        if self.chk_deviation.GetValue():
            if self._reference_params is None:
                if not self._pick_reference_params():
                    self.chk_deviation.SetValue(False)
                    return
            self.choice_deviation_mode.Enable(True)
            self.web.RunScript("window.setDeviationModeEnabled(true)")
        else:
            self.choice_deviation_mode.Enable(False)
            self.web.RunScript("window.setDeviationModeEnabled(false); window.clearDeviationGrid();")

    def _on_pick_reference(self, event):
        self._pick_reference_params()

    def _pick_reference_params(self) -> bool:
        from gui.dialogs.transform_preset_picker_dialog import TransformPresetPickerDialog
        with TransformPresetPickerDialog(self) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return False
            self._reference_params = dlg.get_params()
            self._reference_label = dlg.get_preset_name()

        self.lbl_reference.SetLabel(self._reference_label)
        self.GetSizer().Layout()

        if self.chk_deviation.GetValue() and self._last_bounds is not None:
            self._recompute_deviation_grid()
        return True

    def _current_mode_key(self) -> str:
        idx = self.choice_deviation_mode.GetSelection()
        if idx == wx.NOT_FOUND:
            idx = 0
        return _DEVIATION_MODES[idx][0]

    def _on_mode_changed(self, event):
        if self._last_geojson is None:
            return
        mode = self._current_mode_key()
        payload = json.dumps(self._last_geojson)
        self.web.RunScript(f"window.setDeviationGrid({payload}, {json.dumps(mode)})")

    def _on_js_message(self, event: webview.WebViewEvent):
        try:
            data = json.loads(event.GetString())
            bounds = (float(data["west"]), float(data["south"]), float(data["east"]), float(data["north"]))
        except (ValueError, KeyError, TypeError):
            return
        self._last_bounds = bounds
        if self.chk_deviation.GetValue() and self._reference_params is not None:
            self._recompute_deviation_grid()

    def _recompute_deviation_grid(self):
        if (
            self._last_bounds is None
            or self._source_crs is None
            or self._target_crs is None
            or self._current_params is None
            or self._reference_params is None
        ):
            return
        try:
            geojson = compute_deviation_grid(
                self._last_bounds, self._source_crs, self._target_crs,
                self._current_params, self._reference_params,
                src_action=self._src_action, tgt_action=self._tgt_action,
                delta_zeta_mean=self._delta_zeta_mean,
            )
        except Exception as e:
            wx.LogWarning(f"Не удалось построить карту отклонений: {e}")
            return
        self._last_geojson = geojson
        mode = self._current_mode_key()
        payload = json.dumps(geojson)
        self.web.RunScript(f"window.setDeviationGrid({payload}, {json.dumps(mode)})")
