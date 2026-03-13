# src/utils/xrc_loader.py
import wx
import wx.xrc
import sys
from pathlib import Path
from typing import Optional

from utils.resources import get_resource

class XRCLoader:
    """Загрузчик XRC ресурсов с поддержкой разработки и собранного exe."""
    
    def __init__(self):
        self.res = wx.xrc.XmlResource()
        self._loaded = False
    
    def load(self, xrc_filename: str = "icons.xrc", subdir: str = "icons") -> bool:
        """Загрузить XRC файл."""
        if self._loaded:
            return True
        
        # Находим файл
        xrc_path = self._find_xrc_file(xrc_filename, subdir)
        if not xrc_path:
            return False
        
        # Загружаем
        self._loaded = self.res.Load(str(xrc_path))
        return self._loaded
    
    def _find_xrc_file(self, filename: str, subdir: str) -> Optional[Path]:
        p = get_resource(f"{subdir}/{filename}")
        return p
    
    def get_bitmap(self, name: str, size: tuple = None) -> wx.Bitmap:
        """Получить битмап по имени."""
        if not self._loaded:
            return wx.NullBitmap
        
        bmp = self.res.LoadBitmap(name)
        if bmp.IsOk() and size:
            # Ресайзим если нужно
            img = bmp.ConvertToImage()
            img = img.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)
            return wx.Bitmap(img)
        return bmp
    
    def get_icon(self, name: str) -> wx.Icon:
        """Получить иконку по имени."""
        if not self._loaded:
            return wx.NullIcon
        
        return self.res.LoadIcon(name)

# Создаем глобальный экземпляр
xrc = XRCLoader()