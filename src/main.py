import wx
from gui.controllers.main_frame import MainFrame

import os
import sys

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