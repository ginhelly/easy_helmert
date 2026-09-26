"""
TransformPresetPickerDialog — выбор ранее сохранённого набора параметров
перехода из пользовательской БД (core/user_transforms_db.py).

Дерево: категории (системные + пользовательские + «Без категории») ->
пресеты. Drag&drop пресетов между категориями (кроме системных), поиск по
названию/описанию/значениям параметров, CRUD категорий, и единое
dropdown-меню «Параметры перехода...» (новые / импорт DAM-заглушка /
редактировать).

Применение пресета НЕ трогает source_crs/target_crs главного окна — пресет
не привязан к конкретной паре СК, это просто числа + описание.
"""
from __future__ import annotations

from typing import Optional

import wx

from core.models import DisplaySettings, TransformationParams
from core.user_transforms_db import (
    Category, NO_CATEGORY_LABEL, TransformPreset,
    create_category, delete_category, delete_preset, list_categories,
    list_presets, rename_category, update_preset_category,
)

_SEARCH_DELAY_MS = 250


class TransformPresetPickerDialog(wx.Dialog):

    def __init__(self, parent: wx.Window):
        super().__init__(
            parent, title="Параметры перехода из базы",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
            size=(820, 560),
        )
        self._categories: list[Category] = []
        self._presets: list[TransformPreset] = []
        self._selected_preset: Optional[TransformPreset] = None
        self._selected_category: Optional[Category] = None   # None и есть выбрана "Без категории"
        self._category_node_selected = False                  # выбран узел категории (не пресет)
        self._drag_preset: Optional[TransformPreset] = None
        self._result_params: Optional[TransformationParams] = None
        self._search_timer = wx.Timer(self)

        self._init_ui()
        self._reload()
        self.Centre()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        self.search_ctrl = wx.SearchCtrl(self)
        self.search_ctrl.ShowCancelButton(True)
        root.Add(self.search_ctrl, 0, wx.EXPAND | wx.ALL, 6)

        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # ── Дерево слева ─────────────────────────────────────────────────
        left_panel = wx.Panel(splitter)
        left_sizer = wx.BoxSizer(wx.VERTICAL)

        self.tree = wx.TreeCtrl(
            left_panel,
            style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT | wx.TR_SINGLE,
        )
        left_sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 4)

        cat_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_cat_new = wx.Button(left_panel, label="Новая категория")
        self.btn_cat_rename = wx.Button(left_panel, label="Переименовать")
        self.btn_cat_delete = wx.Button(left_panel, label="Удалить категорию")
        cat_btn_row.Add(self.btn_cat_new, 0, wx.RIGHT, 4)
        cat_btn_row.Add(self.btn_cat_rename, 0, wx.RIGHT, 4)
        cat_btn_row.Add(self.btn_cat_delete, 0)
        left_sizer.Add(cat_btn_row, 0, wx.ALL, 4)

        preset_btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self.btn_params_menu = wx.Button(left_panel, label="Параметры перехода... ▾")
        self.btn_delete_preset = wx.Button(left_panel, label="Удалить пресет")
        preset_btn_row.Add(self.btn_params_menu, 0, wx.RIGHT, 4)
        preset_btn_row.Add(self.btn_delete_preset, 0)
        left_sizer.Add(preset_btn_row, 0, wx.ALL, 4)

        left_panel.SetSizer(left_sizer)

        # ── Превью справа ────────────────────────────────────────────────
        preview_panel = wx.Panel(splitter)
        preview_sizer = wx.BoxSizer(wx.VERTICAL)
        self.txt_preview = wx.TextCtrl(
            preview_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL,
        )
        self.txt_preview.SetFont(wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        preview_sizer.Add(self.txt_preview, 1, wx.EXPAND | wx.ALL, 4)
        preview_panel.SetSizer(preview_sizer)

        splitter.SplitVertically(left_panel, preview_panel, 420)
        splitter.SetMinimumPaneSize(150)
        root.Add(splitter, 1, wx.EXPAND | wx.ALL, 6)

        # ── Кнопки OK/Cancel ─────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        self.ok_btn = wx.Button(self, wx.ID_OK, "Применить")
        self.ok_btn.SetDefault()
        self.ok_btn.Disable()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Отмена")
        btn_sizer.AddButton(self.ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        # ── Биндинги ─────────────────────────────────────────────────────
        self.ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_tree_selection)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_tree_activate)
        self.tree.Bind(wx.EVT_TREE_BEGIN_DRAG, self._on_begin_drag)
        self.tree.Bind(wx.EVT_TREE_END_DRAG, self._on_end_drag)

        self.btn_cat_new.Bind(wx.EVT_BUTTON, self._on_new_category)
        self.btn_cat_rename.Bind(wx.EVT_BUTTON, self._on_rename_category)
        self.btn_cat_delete.Bind(wx.EVT_BUTTON, self._on_delete_category)
        self.btn_delete_preset.Bind(wx.EVT_BUTTON, self._on_delete_preset)
        self.btn_params_menu.Bind(wx.EVT_BUTTON, self._on_params_menu)

        self.search_ctrl.Bind(wx.EVT_TEXT, self._on_search_text_changed)
        self.search_ctrl.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, lambda e: self.search_ctrl.SetValue(""))
        self.Bind(wx.EVT_TIMER, lambda e: self._rebuild_tree(), self._search_timer)

        self.SetSizer(root)

    # ── Загрузка / построение дерева ─────────────────────────────────────────

    def _reload(self):
        self._categories = list_categories()
        self._presets = list_presets()
        self._rebuild_tree()

    def _on_search_text_changed(self, event):
        self._search_timer.StartOnce(_SEARCH_DELAY_MS)
        event.Skip()

    @staticmethod
    def _preset_search_blob(p: TransformPreset) -> str:
        parts = [p.name, p.description]
        parts.extend(str(v) for v in p.params.values())
        return " ".join(parts).lower()

    def _rebuild_tree(self):
        query = self.search_ctrl.GetValue().strip().lower()

        tree = self.tree
        tree.DeleteAllItems()
        root = tree.AddRoot("root")

        ordered_categories = sorted(self._categories, key=lambda c: (not c.is_system, c.sort_order, c.name))

        def _presets_for(category_id: Optional[int]) -> list[TransformPreset]:
            items = [p for p in self._presets if p.category_id == category_id]
            if query:
                items = [p for p in items if query in self._preset_search_blob(p)]
            return items

        for cat in ordered_categories:
            cat_presets = _presets_for(cat.id)
            if query and not cat_presets:
                continue
            cat_item = tree.AppendItem(root, cat.name)
            tree.SetItemData(cat_item, cat)
            if cat.is_system:
                tree.SetItemBold(cat_item, True)
            for p in cat_presets:
                self._append_preset_item(cat_item, p)
            tree.Expand(cat_item)

        no_cat_presets = _presets_for(None)
        if not query or no_cat_presets:
            no_cat_item = tree.AppendItem(root, NO_CATEGORY_LABEL)
            tree.SetItemData(no_cat_item, None)
            for p in no_cat_presets:
                self._append_preset_item(no_cat_item, p)
            tree.Expand(no_cat_item)

        self._selected_preset = None
        self._selected_category = None
        self._category_node_selected = False
        self._update_preview()
        self._update_button_states()

    def _append_preset_item(self, parent_item, preset: TransformPreset):
        item = self.tree.AppendItem(parent_item, preset.name)
        self.tree.SetItemData(item, preset)
        if preset.is_system:
            self.tree.SetItemTextColour(item, wx.Colour(120, 120, 120))

    # ── Выбор в дереве ────────────────────────────────────────────────────────

    def _on_tree_selection(self, event):
        item = event.GetItem()
        if not item.IsOk():
            self._selected_preset = None
            self._selected_category = None
            self._category_node_selected = False
        else:
            data = self.tree.GetItemData(item)
            parent = self.tree.GetItemParent(item)
            is_top_level = parent.IsOk() and parent == self.tree.GetRootItem()
            if isinstance(data, TransformPreset):
                self._selected_preset = data
                self._selected_category = None
                self._category_node_selected = False
            elif is_top_level:
                self._selected_preset = None
                self._selected_category = data   # Category или None ("Без категории")
                self._category_node_selected = True
            else:
                self._selected_preset = None
                self._selected_category = None
                self._category_node_selected = False
        self._update_preview()
        self._update_button_states()

    def _on_tree_activate(self, event):
        if self._selected_preset is not None and self._selected_preset.is_supported:
            self._on_ok(event)

    def _update_button_states(self):
        has_preset = self._selected_preset is not None
        self.btn_delete_preset.Enable(has_preset and not self._selected_preset.is_system)

        is_editable_category = (
            self._category_node_selected
            and self._selected_category is not None
            and not self._selected_category.is_system
        )
        self.btn_cat_rename.Enable(is_editable_category)
        self.btn_cat_delete.Enable(is_editable_category)

    def _update_preview(self):
        p = self._selected_preset
        if p is None:
            self.txt_preview.SetValue("")
            self.ok_btn.Disable()
            return

        if not p.is_supported:
            self.txt_preview.SetValue(
                f"Формат параметров «{p.method}» не поддерживается в этой версии "
                f"приложения — применить нельзя.\n\n{p.description}"
            )
            self.ok_btn.Disable()
            return

        params = p.to_transformation_params()
        display = params.as_display(DisplaySettings())
        text = (
            f"{p.name}\n"
            f"Сохранён: {p.created_at}"
            f"{'  (системный)' if p.is_system else ''}\n"
            f"{'-' * 60}\n"
            f"{display.to_text(include_rms=False)}\n"
        )
        if p.description:
            text += f"\n{'-' * 60}\n{p.description}\n"
        self.txt_preview.SetValue(text)
        self.ok_btn.Enable()

    # ── Drag & drop ───────────────────────────────────────────────────────────

    def _on_begin_drag(self, event):
        item = event.GetItem()
        data = self.tree.GetItemData(item)
        if isinstance(data, TransformPreset) and not data.is_system:
            self._drag_preset = data
            event.Allow()
        else:
            self._drag_preset = None

    def _on_end_drag(self, event):
        preset = self._drag_preset
        self._drag_preset = None
        if preset is None:
            return

        target_item = event.GetItem()
        if not target_item.IsOk():
            return

        target_data = self.tree.GetItemData(target_item)
        if isinstance(target_data, TransformPreset):
            target_item = self.tree.GetItemParent(target_item)
            target_data = self.tree.GetItemData(target_item)

        new_category_id = target_data.id if isinstance(target_data, Category) else None

        try:
            update_preset_category(preset.id, new_category_id)
        except ValueError as e:
            wx.MessageBox(str(e), "Ошибка", wx.OK | wx.ICON_ERROR, self)
        self._reload()

    # ── Категории: CRUD ──────────────────────────────────────────────────────

    def _on_new_category(self, event):
        with wx.TextEntryDialog(self, "Название категории:", "Новая категория") as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            name = dlg.GetValue().strip()
        if not name:
            return
        create_category(name)
        self._reload()

    def _on_rename_category(self, event):
        if self._selected_category is None:
            return
        with wx.TextEntryDialog(
            self, "Новое название категории:", "Переименовать категорию",
            value=self._selected_category.name,
        ) as dlg:
            if dlg.ShowModal() != wx.ID_OK:
                return
            new_name = dlg.GetValue().strip()
        if not new_name:
            return
        try:
            rename_category(self._selected_category.id, new_name)
        except ValueError as e:
            wx.MessageBox(str(e), "Ошибка", wx.OK | wx.ICON_ERROR, self)
            return
        self._reload()

    def _on_delete_category(self, event):
        if self._selected_category is None:
            return
        cat = self._selected_category
        if wx.MessageBox(
            f"Удалить категорию «{cat.name}»?\n"
            f"Пресеты из неё перейдут в «{NO_CATEGORY_LABEL}».",
            "Подтверждение", wx.YES_NO | wx.ICON_QUESTION, self,
        ) != wx.YES:
            return
        try:
            delete_category(cat.id)
        except ValueError as e:
            wx.MessageBox(str(e), "Ошибка", wx.OK | wx.ICON_ERROR, self)
            return
        self._reload()

    # ── Пресеты: удаление ────────────────────────────────────────────────────

    def _on_delete_preset(self, event):
        p = self._selected_preset
        if p is None:
            return
        if wx.MessageBox(
            f"Удалить пресет «{p.name}»?", "Подтверждение",
            wx.YES_NO | wx.ICON_QUESTION, self,
        ) != wx.YES:
            return
        try:
            delete_preset(p.id)
        except ValueError as e:
            wx.MessageBox(str(e), "Ошибка", wx.OK | wx.ICON_ERROR, self)
            return
        self._reload()

    # ── Пресеты: новые / импорт / редактировать ─────────────────────────────

    def _current_category_id_for_new(self) -> Optional[int]:
        if self._category_node_selected:
            return self._selected_category.id if self._selected_category else None
        if self._selected_preset is not None:
            return self._selected_preset.category_id
        return None

    def _on_params_menu(self, event):
        menu = wx.Menu()
        item_new = menu.Append(wx.ID_ANY, "Новые параметры")
        item_dam = menu.Append(wx.ID_ANY, "Импорт из DAM-файла (бета)")
        item_edit = menu.Append(wx.ID_ANY, "Редактировать параметры")
        item_edit.Enable(self._selected_preset is not None and not self._selected_preset.is_system)

        self.Bind(wx.EVT_MENU, self._on_new_params, item_new)
        self.Bind(wx.EVT_MENU, self._on_import_dam_stub, item_dam)
        self.Bind(wx.EVT_MENU, self._on_edit_params, item_edit)

        self.btn_params_menu.PopupMenu(menu)
        menu.Destroy()

    def _on_new_params(self, event):
        from gui.dialogs.import_params_dialog import ImportParamsDialog
        with ImportParamsDialog(
            self, force_save=True,
            default_category_id=self._current_category_id_for_new(),
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._reload()

    def _on_import_dam_stub(self, event):
        wx.MessageBox(
            "Импорт из DAM-файла пока не реализован — скоро будет доступно.",
            "В разработке", wx.OK | wx.ICON_INFORMATION, self,
        )

    def _on_edit_params(self, event):
        if self._selected_preset is None or self._selected_preset.is_system:
            return
        from gui.dialogs.import_params_dialog import ImportParamsDialog
        with ImportParamsDialog(self, edit_preset=self._selected_preset) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self._reload()

    # ── OK ────────────────────────────────────────────────────────────────────

    def _on_ok(self, event):
        if self._selected_preset is None or not self._selected_preset.is_supported:
            return
        self._result_params = self._selected_preset.to_transformation_params()
        self.EndModal(wx.ID_OK)

    # ── Публичный API ─────────────────────────────────────────────────────────

    def get_params(self) -> Optional[TransformationParams]:
        return self._result_params

    def get_preset_name(self) -> str:
        return self._selected_preset.name if self._selected_preset else ""
