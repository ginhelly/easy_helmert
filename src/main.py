import wx
from gui.controllers.main_frame import MainFrame

def main():
    app = wx.App(False)
    frame = MainFrame()
    app.MainLoop()

if __name__ == "__main__":
    main()