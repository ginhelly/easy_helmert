"""
CrsPickerDialog — диалог выбора системы координат.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import wx
import wx.dataview as dv

from pyproj import CRS
from pyproj.exceptions import CRSError

from core.crs_database import (
    CrsEntry,
    filter_entries,
    group_entries,
    load_all_entries,
)
from utils.crs_utils import describe_crs
from gui.forms.easy_helmert_base import BaseCRSPickerDialog


# Типы, которые не показываем в дереве
_HIDDEN_TYPES = {"Геоцентрические", "Прочие"}


class CrsPickerDialog(BaseCRSPickerDialog):

    _SEARCH_DELAY_MS = 250

    def __init__(self, parent: wx.Window, title: str = "Выбор системы координат"):
        super().__init__(parent)
        self.SetTitle(title)

        self._selected_crs:  Optional[CRS] = None
        self._selected_name: str = ""          # ← новое поле
        self._all_entries:   List[CrsEntry] = []
        self._search_timer = wx.Timer(self)

        self.m_btn_ok.Disable()
        self._load_database()
        self._bind_events()
        self._rebuild_tree(self._all_entries)

    # ── Загрузка базы ─────────────────────────────────────────────────────────

    def _load_database(self):
        wx.BeginBusyCursor()
        try:
            self._all_entries = load_all_entries()
        finally:
            wx.EndBusyCursor()

    # ── Привязка событий ──────────────────────────────────────────────────────

    def _bind_events(self):
        self.m_txt_search.Bind(wx.EVT_TEXT, self._on_search_text_changed)
        self.Bind(wx.EVT_TIMER, self._on_search_timer, self._search_timer)

        self.m_chk_projected.Bind(wx.EVT_CHECKBOX, self._on_filter_changed)
        self.m_chk_geographic.Bind(wx.EVT_CHECKBOX, self._on_filter_changed)

        self.m_tree_search.Bind(
            dv.EVT_DATAVIEW_SELECTION_CHANGED, self._on_tree_selection
        )
        self.m_tree_search.Bind(
            dv.EVT_DATAVIEW_ITEM_ACTIVATED, self._on_tree_activate
        )

        self.m_btn_parse_crs.Bind(wx.EVT_BUTTON, self._on_parse_custom)
        self.m_btn_ok.Bind(wx.EVT_BUTTON, self._on_ok)

    # ── Построение дерева ─────────────────────────────────────────────────────

    def _rebuild_tree(self, entries: List[CrsEntry]):
        tree = self.m_tree_search
        tree.DeleteAllItems()

        grouped = group_entries(entries)

        TYPE_ORDER = [
            "Проецированные", "Географические",
            "Геоцентрические", "Составные", "Вертикальные", "Прочие",
        ]
        sorted_types = sorted(
            grouped.keys(),
            key=lambda k: TYPE_ORDER.index(k) if k in TYPE_ORDER else 99,
        )

        has_query = bool(self.m_txt_search.GetValue().strip())

        for type_label in sorted_types:
            if type_label in _HIDDEN_TYPES:
                continue

            subcats = grouped[type_label]
            total = sum(len(v) for v in subcats.values())

            type_node = tree.AppendContainer(
                dv.NullDataViewItem,
                f"{type_label}  ({total})",
            )

            for subcat_label, cat_entries in subcats.items():
                subcat_node = tree.AppendContainer(
                    type_node,
                    f"{subcat_label}  ({len(cat_entries)})",
                )
                for e in cat_entries:
                    item = tree.AppendItem(subcat_node, e.label)
                    # Храним CrsEntry прямо в узле — надёжнее любого словаря
                    tree.SetItemData(item, e)

                if has_query:
                    tree.Expand(subcat_node)

            if has_query or len(entries) <= 200:
                tree.Expand(type_node)


    @staticmethod
    def _item_key(item: dv.DataViewItem) -> int:
        return item.GetID()

    # ── Фильтрация ────────────────────────────────────────────────────────────

    def _on_search_text_changed(self, event):
        self._search_timer.StartOnce(self._SEARCH_DELAY_MS)
        event.Skip()

    def _on_search_timer(self, event):
        self._apply_filter()

    def _on_filter_changed(self, event):
        self._apply_filter()
        event.Skip()

    def _apply_filter(self):
        query = self.m_txt_search.GetValue()
        entries = filter_entries(
            self._all_entries,
            query              = query,
            include_projected  = self.m_chk_projected.GetValue(),
            include_geographic = self.m_chk_geographic.GetValue(),
        )
        self._rebuild_tree(entries)

    # ── Выбор в дереве ────────────────────────────────────────────────────────

    def _on_tree_selection(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        entry = self.m_tree_search.GetItemData(item)
        if not isinstance(entry, CrsEntry):
            return   # контейнер (тип или подкатегория)
        self._load_crs_from_entry(entry)

    def _on_tree_activate(self, event):
        item = event.GetItem()
        if not item.IsOk():
            return
        entry = self.m_tree_search.GetItemData(item)
        if isinstance(entry, CrsEntry):
            if self._selected_crs:
                self.EndModal(wx.ID_OK)
            else:
                self._load_crs_from_entry(entry)
        else:
            # Контейнер — раскрываем/сворачиваем
            tree = self.m_tree_search
            if tree.IsExpanded(item):
                tree.Collapse(item)
            else:
                tree.Expand(item)

    # ── Вкладка WKT / Proj4 ───────────────────────────────────────────────────

    def _on_parse_custom(self, event):
        text = self.m_txt_wkt_input.GetValue().strip()
        if not text:
            return
        try:
            crs = CRS.from_user_input(text)
            # Для ручного ввода имя берём из самого CRS
            self._set_crs(crs, display_name=crs.name)
        except CRSError as e:
            self._set_error(str(e))


    # ── Загрузка CRS ──────────────────────────────────────────────────────────

    def _load_crs_from_entry(self, entry: CrsEntry):
        src = entry.crs_source
        if not src:
            self._set_error(f"Нет WKT и Proj4 для: {entry.name}")
            return
        try:
            crs = CRS.from_user_input(src)
            # Передаём label записи — ровно в том виде, что в дереве
            self._set_crs(crs, display_name=entry.label)
        except CRSError as e:
            self._set_error(str(e))


    def _set_crs(self, crs: CRS, display_name: Optional[str] = None):
        self._selected_crs  = crs
        self._selected_name = display_name or crs.name
        self.m_txt_crs_info.SetForegroundColour(wx.NullColour)
        self.m_txt_crs_info.SetValue(describe_crs(crs))
        self.m_btn_ok.Enable()

    def _set_error(self, msg: str):
        self._selected_crs  = None
        self._selected_name = ""
        self.m_txt_crs_info.SetForegroundColour(wx.Colour(180, 0, 0))
        self.m_txt_crs_info.SetValue(f"Ошибка: {msg}")
        self.m_btn_ok.Disable()

    # ── OK ────────────────────────────────────────────────────────────────────

    def _on_ok(self, event):
        if self._selected_crs is not None:
            event.Skip()

    # ── Публичный API ─────────────────────────────────────────────────────────

    def get_selected_crs(self) -> Optional[CRS]:
        """Вызывать после ShowModal() == wx.ID_OK."""
        return self._selected_crs
    
    def get_selected_name(self) -> str:
        """
        Имя СК в том виде, что отображается в списке:
        'Pulkovo 1942 / Gauss-Kruger zone 3  [EPSG:28403]'
        Для ручного ввода — crs.name согласно WKT/Proj4.
        """
        return self._selected_name