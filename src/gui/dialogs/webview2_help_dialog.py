# src/gui/dialogs/webview2_help_dialog.py
import wx
import wx.adv


class WebView2HelpDialog(wx.Dialog):
    def __init__(self, parent):
        super().__init__(
            parent,
            title="Требуется Microsoft Edge WebView2 Runtime",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(620, 320),
        )

        root = wx.BoxSizer(wx.VERTICAL)

        title = wx.StaticText(self, label="Для отображения карты нужен современный веб-движок")
        title.SetFont(wx.Font(wx.NORMAL_FONT.GetPointSize() + 1, wx.FONTFAMILY_DEFAULT,
                              wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        root.Add(title, 0, wx.ALL, 10)

        text = wx.StaticText(
            self,
            label=(
                "На этом компьютере недоступен Edge WebView2 backend.\n"
                "Поэтому карта может не открыться или работать некорректно.\n\n"
                "Что сделать:\n"
                "1) Установить Microsoft Edge WebView2 Runtime (Evergreen)\n"
                "2) При необходимости посмотреть официальную инструкцию по установке"
            ),
        )
        root.Add(text, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        link1 = wx.adv.HyperlinkCtrl(
            self,
            id=wx.ID_ANY,
            label="Скачать WebView2 Runtime (официальная страница Microsoft)",
            url="https://developer.microsoft.com/en-us/microsoft-edge/webview2/",
        )
        root.Add(link1, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        link2 = wx.adv.HyperlinkCtrl(
            self,
            id=wx.ID_ANY,
            label="Инструкция по распространению/установке WebView2 Runtime",
            url="https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution",
        )
        root.Add(link2, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)

        btn_ok = wx.Button(self, wx.ID_OK, "OK")
        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        btn_row.AddStretchSpacer(1)
        btn_row.Add(btn_ok, 0, wx.ALL, 10)

        root.Add(btn_row, 0, wx.EXPAND)
        self.SetSizer(root)
        self.CentreOnParent()