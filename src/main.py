import os
import sys
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)

import wx
from gui.controllers.main_frame import MainFrame

# ── DPI Awareness для чёткого отображения на Windows 10/11 ────────────────
if sys.platform == "win32":
    try:
        # Per-Monitor V2 — лучший вариант для Windows 10 1703+
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Fallback для старых Windows
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

if hasattr(sys, "_MEIPASS"):
    os.environ["GDAL_DATA"] = os.path.join(
        sys._MEIPASS, "rasterio", "gdal_data"
    )
    os.environ["PROJ_DATA"] = os.path.join(
        sys._MEIPASS, "pyproj", "proj_dir", "share", "proj"
    )
    os.environ["PROJ_LIB"]      = os.environ["PROJ_DATA"]
    os.environ["RASTERIO_DATA"] = os.environ["GDAL_DATA"]

def main():
    app = wx.App(False)
    frame = MainFrame()
    app.MainLoop()

if __name__ == "__main__":
    main()