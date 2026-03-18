from __future__ import annotations

import wx
import wx.html2 as webview

from gui.utils.map_html import render_map_html
from gui.utils.kml_export import build_kml


class MapDialog(wx.Dialog):
    def __init__(self, parent, title: str = "Точки на карте", size=(980, 700)):
        super().__init__(parent, title=title, size=size,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

        self._src_points = []
        self._tgt_points = []
        self._title = title
        
        s = wx.BoxSizer(wx.VERTICAL)
        self.web = webview.WebView.New(self)
        s.Add(self.web, 1, wx.EXPAND | wx.ALL, 6)

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

    def set_points(self, src_points: list[dict], tgt_points: list[dict], title: str = "Точки калибровки"):
        self._src_points = list(src_points or [])
        self._tgt_points = list(tgt_points or [])
        self._title = title

        html = render_map_html(title, self._src_points, self._tgt_points)
        self.web.SetPage(html, "https://easyhelmert.local/")  # base URL для referer

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