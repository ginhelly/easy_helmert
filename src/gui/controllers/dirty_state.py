from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional
import wx


@dataclass
class DirtyStateManager:
    """
    Простой менеджер dirty-state для MainFrame.
    Не знает ничего о grid/CRS/расчётах — только про:
      - изменено / не изменено
      - спросить пользователя о сохранении
    """
    is_modified: bool = False
    history: List[str] = field(default_factory=list)
    debug: bool = True

    def mark(self, reason: str = "") -> None:
        self.is_modified = True
        if reason:
            self.history.append(f"+ {reason}")
        if self.debug:
            print(f"[DIRTY] -> True  reason={reason}")

    def clear(self, reason: str = "") -> None:
        self.is_modified = False
        if reason:
            self.history.append(f"- {reason}")
        if self.debug:
            print(f"[DIRTY] -> False reason={reason}")

    def ask_save_if_modified(
        self,
        parent: wx.Window,
        has_data: Callable[[], bool],
        save_callable: Callable[[], bool],
        title: str = "Несохранённые изменения",
        message: str = "Данные были изменены.\nСохранить перед продолжением?",
    ) -> bool:
        """
        Возвращает:
          True  -> можно продолжать действие
          False -> прервать действие
        """
        if not self.is_modified:
            return True

        if not has_data():
            return True

        dlg = wx.MessageDialog(
            parent,
            message,
            title,
            wx.YES_NO | wx.CANCEL | wx.ICON_QUESTION,
        )
        result = dlg.ShowModal()
        dlg.Destroy()

        if result == wx.ID_YES:
            ok = save_callable()   # True только при реальном сохранении
            return bool(ok)

        if result == wx.ID_NO:
            return True

        return False  # wx.ID_CANCEL