"""
ImportParamsDialog — ручной ввод 7 параметров Гельмерта из стороннего
источника (публикация, соседний расчёт и т.п.), с опцией сохранить их в
пользовательскую БД пресетов (core/user_transforms_db.py).

Три режима использования:
  - обычный (из главного окна, "Указать параметры вручную"): чекбокс
    "Сохранить" необязателен;
  - force_save=True ("Новые параметры" из диалога БД): чекбокс включён
    и задизейблен — параметры создаются именно для сохранения;
  - edit_preset=<TransformPreset> ("Редактировать параметры"): поля
    предзаполнены, OK обновляет существующую запись, а не создаёт новую.

Возвращает канонические TransformationParams (Position Vector,
источник -> опора) независимо от того, в каком методе/направлении они были
введены — конвертация применяется на OK.
"""
from __future__ import annotations

from typing import Optional

import wx

from core.constants import ARCSEC_TO_RAD, FACTOR_TO_PPM, FACTOR_TO_PPB
from core.models import (
    HelmertDirection, HelmertMethod, RotationUnit, ScaleUnit, TransformationParams,
)
from core.user_transforms_db import (
    HELMERT7, NO_CATEGORY_LABEL, TransformPreset, helmert7_to_json,
    list_categories, save_preset, update_preset,
)
from gui.widgets.coordinate_grid import _sys_dec_sep

NO_CATEGORY_INDEX = 0   # позиция «Без категории» в choice_category


def _parse_float(ctrl: wx.TextCtrl, dec_sep: str, label: str) -> float:
    raw = ctrl.GetValue().strip()
    if not raw:
        raise ValueError(f"Поле «{label}» не заполнено.")
    alt = "," if dec_sep == "." else "."
    raw = raw.replace(alt, dec_sep)
    try:
        return float(raw)
    except ValueError:
        raise ValueError(f"Некорректное число в поле «{label}»: {raw!r}")


class ImportParamsDialog(wx.Dialog):

    def __init__(
        self,
        parent: wx.Window,
        *,
        force_save: bool = False,
        edit_preset: Optional[TransformPreset] = None,
        default_category_id: Optional[int] = None,
    ):
        self._edit_preset = edit_preset
        force_save = force_save or edit_preset is not None

        title = (
            "Редактировать параметры перехода" if edit_preset is not None else
            "Новые параметры перехода" if force_save else
            "Указать параметры перехода вручную"
        )
        super().__init__(
            parent, title=title,
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self._dec_sep = _sys_dec_sep()
        self._force_save = force_save
        self._default_category_id = default_category_id
        self._result_params: Optional[TransformationParams] = None

        self._categories = list_categories()

        self._init_ui()
        if edit_preset is not None:
            self._prefill_from_preset(edit_preset)

        self.Layout()
        self.Fit()
        self.SetMinSize(self.GetSize())
        self.Centre()

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        root = wx.BoxSizer(wx.VERTICAL)

        # ── Сдвиги ────────────────────────────────────────────────────────
        shift_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Сдвиги (м)"), wx.HORIZONTAL)
        self.txt_dx = wx.TextCtrl(self, size=(90, -1))
        self.txt_dy = wx.TextCtrl(self, size=(90, -1))
        self.txt_dz = wx.TextCtrl(self, size=(90, -1))
        for label, ctrl in (("dX", self.txt_dx), ("dY", self.txt_dy), ("dZ", self.txt_dz)):
            shift_box.Add(wx.StaticText(self, label=f"{label} ="), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            shift_box.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        root.Add(shift_box, 0, wx.EXPAND | wx.ALL, 6)

        # ── Повороты ──────────────────────────────────────────────────────
        rot_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Повороты"), wx.HORIZONTAL)
        self.txt_rx = wx.TextCtrl(self, size=(90, -1))
        self.txt_ry = wx.TextCtrl(self, size=(90, -1))
        self.txt_rz = wx.TextCtrl(self, size=(90, -1))
        for label, ctrl in (("rX", self.txt_rx), ("rY", self.txt_ry), ("rZ", self.txt_rz)):
            rot_box.Add(wx.StaticText(self, label=f"{label} ="), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
            rot_box.Add(ctrl, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        self.choice_rotation_units = wx.Choice(self, choices=["Секунды (″)", "Радианы"])
        self.choice_rotation_units.SetSelection(0)
        rot_box.Add(self.choice_rotation_units, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        root.Add(rot_box, 0, wx.EXPAND | wx.ALL, 6)

        # ── Масштаб ───────────────────────────────────────────────────────
        scale_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Масштаб"), wx.HORIZONTAL)
        self.txt_scale = wx.TextCtrl(self, size=(90, -1))
        scale_box.Add(wx.StaticText(self, label="dS ="), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 8)
        scale_box.Add(self.txt_scale, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 4)
        self.choice_scale_units = wx.Choice(self, choices=[
            "Безразмерный коэффициент", "Миллионные части (ppm)", "Миллиардные части (ppb)",
        ])
        self.choice_scale_units.SetSelection(1)
        scale_box.Add(self.choice_scale_units, 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT, 10)
        root.Add(scale_box, 0, wx.EXPAND | wx.ALL, 6)

        # ── Метод и направление, как введены исходные параметры ────────────
        conv_box = wx.StaticBoxSizer(wx.StaticBox(self, label="В какой конвенции даны параметры"), wx.VERTICAL)
        self.rb_method = wx.RadioBox(
            self, label="Метод преобразования",
            choices=["EPSG:1033 (9606) Position Vector Transformation",
                     "EPSG:1032 (9607) Coordinate Frame Rotation"],
            style=wx.RA_SPECIFY_COLS,
        )
        self.rb_direction = wx.RadioBox(
            self, label="Направление параметров",
            choices=["Из исходной -> в опорную", "Из опорной -> в исходную"],
            style=wx.RA_SPECIFY_COLS,
        )
        conv_box.Add(self.rb_method, 0, wx.EXPAND | wx.ALL, 4)
        conv_box.Add(self.rb_direction, 0, wx.EXPAND | wx.ALL, 4)
        root.Add(conv_box, 0, wx.EXPAND | wx.ALL, 6)

        # ── Сохранение в БД ──────────────────────────────────────────────
        save_box = wx.StaticBoxSizer(wx.StaticBox(self, label="Сохранение"), wx.VERTICAL)
        self.chk_save = wx.CheckBox(self, label="Сохранить эти параметры в базу")
        save_box.Add(self.chk_save, 0, wx.ALL, 4)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(wx.StaticText(self, label="Название:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        self.txt_name = wx.TextCtrl(self)
        name_row.Add(self.txt_name, 1)
        save_box.Add(name_row, 0, wx.EXPAND | wx.ALL, 4)

        cat_row = wx.BoxSizer(wx.HORIZONTAL)
        cat_row.Add(wx.StaticText(self, label="Категория:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        cat_choices = [NO_CATEGORY_LABEL] + [c.name for c in self._categories]
        self.choice_category = wx.Choice(self, choices=cat_choices)
        self.choice_category.SetSelection(NO_CATEGORY_INDEX)
        if self._default_category_id is not None:
            for i, c in enumerate(self._categories):
                if c.id == self._default_category_id:
                    self.choice_category.SetSelection(i + 1)
                    break
        cat_row.Add(self.choice_category, 1)
        save_box.Add(cat_row, 0, wx.EXPAND | wx.ALL, 4)

        save_box.Add(wx.StaticText(self, label="Описание:"), 0, wx.LEFT | wx.TOP, 4)
        self.txt_description = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 60))
        save_box.Add(self.txt_description, 0, wx.EXPAND | wx.ALL, 4)

        root.Add(save_box, 0, wx.EXPAND | wx.ALL, 6)

        if self._force_save:
            self.chk_save.SetValue(True)
            self.chk_save.Enable(False)
        else:
            self.chk_save.Bind(wx.EVT_CHECKBOX, self._on_toggle_save)
        self._set_save_fields_enabled(self._force_save)

        # ── Кнопки ───────────────────────────────────────────────────────
        btn_sizer = wx.StdDialogButtonSizer()
        ok_label = "Сохранить" if self._edit_preset is not None else "Применить"
        ok_btn = wx.Button(self, wx.ID_OK, ok_label)
        ok_btn.SetDefault()
        cancel_btn = wx.Button(self, wx.ID_CANCEL, "Отмена")
        btn_sizer.AddButton(ok_btn)
        btn_sizer.AddButton(cancel_btn)
        btn_sizer.Realize()
        root.Add(btn_sizer, 0, wx.ALIGN_RIGHT | wx.ALL, 8)

        ok_btn.Bind(wx.EVT_BUTTON, self._on_ok)

        self.SetSizer(root)

    def _set_save_fields_enabled(self, enabled: bool):
        self.txt_name.Enable(enabled)
        self.choice_category.Enable(enabled)
        self.txt_description.Enable(enabled)

    def _on_toggle_save(self, event):
        self._set_save_fields_enabled(self.chk_save.GetValue())
        event.Skip()

    # ── Предзаполнение (режим редактирования) ───────────────────────────────

    def _prefill_from_preset(self, preset: TransformPreset):
        params = preset.to_transformation_params()
        self.txt_dx.SetValue(f"{params.dx:g}")
        self.txt_dy.SetValue(f"{params.dy:g}")
        self.txt_dz.SetValue(f"{params.dz:g}")
        self.txt_rx.SetValue(f"{params.rx_sec:g}")
        self.txt_ry.SetValue(f"{params.ry_sec:g}")
        self.txt_rz.SetValue(f"{params.rz_sec:g}")
        self.txt_scale.SetValue(f"{params.scale_ppm:g}")
        self.choice_rotation_units.SetSelection(RotationUnit.ARCSEC)
        self.choice_scale_units.SetSelection(ScaleUnit.PPM)
        self.rb_method.SetSelection(HelmertMethod.POSITION_VECTOR)
        self.rb_direction.SetSelection(HelmertDirection.FORWARD)

        self.txt_name.SetValue(preset.name)
        self.txt_description.SetValue(preset.description)
        if preset.category_id is None:
            self.choice_category.SetSelection(NO_CATEGORY_INDEX)
        else:
            for i, c in enumerate(self._categories):
                if c.id == preset.category_id:
                    self.choice_category.SetSelection(i + 1)
                    break

    # ── OK ────────────────────────────────────────────────────────────────────

    def _selected_category_id(self) -> Optional[int]:
        idx = self.choice_category.GetSelection()
        if idx <= 0:
            return None
        return self._categories[idx - 1].id

    def _on_ok(self, event):
        try:
            dx = _parse_float(self.txt_dx, self._dec_sep, "dX")
            dy = _parse_float(self.txt_dy, self._dec_sep, "dY")
            dz = _parse_float(self.txt_dz, self._dec_sep, "dZ")
            rx_raw = _parse_float(self.txt_rx, self._dec_sep, "rX")
            ry_raw = _parse_float(self.txt_ry, self._dec_sep, "rY")
            rz_raw = _parse_float(self.txt_rz, self._dec_sep, "rZ")
            scale_raw = _parse_float(self.txt_scale, self._dec_sep, "dS")
        except ValueError as e:
            wx.MessageBox(str(e), "Ошибка ввода", wx.OK | wx.ICON_ERROR, self)
            return

        if self.chk_save.GetValue() and not self.txt_name.GetValue().strip():
            wx.MessageBox("Укажите название для сохранения в базу.", "Ошибка ввода", wx.OK | wx.ICON_ERROR, self)
            return

        # Единицы поворота -> радианы
        if self.choice_rotation_units.GetSelection() == RotationUnit.ARCSEC:
            rx, ry, rz = rx_raw * ARCSEC_TO_RAD, ry_raw * ARCSEC_TO_RAD, rz_raw * ARCSEC_TO_RAD
        else:
            rx, ry, rz = rx_raw, ry_raw, rz_raw

        # Единицы масштаба -> множитель (1 + dS)
        scale_unit = self.choice_scale_units.GetSelection()
        if scale_unit == ScaleUnit.DIMENSIONLESS:
            scale = scale_raw
        elif scale_unit == ScaleUnit.PPM:
            scale = 1.0 + scale_raw / FACTOR_TO_PPM
        else:
            scale = 1.0 + scale_raw / FACTOR_TO_PPB

        params = TransformationParams(dx=dx, dy=dy, dz=dz, rx=rx, ry=ry, rz=rz, scale=scale)

        # Метод: Coordinate Frame -> Position Vector (инверсия знаков поворота)
        if self.rb_method.GetSelection() == HelmertMethod.COORDINATE_FRAME:
            params = params.model_copy(update={"rx": -params.rx, "ry": -params.ry, "rz": -params.rz})

        # Направление: если параметры даны как опора -> исходная, инвертируем
        if self.rb_direction.GetSelection() == HelmertDirection.INVERSE:
            params = params.inverted()

        if self.chk_save.GetValue():
            name = self.txt_name.GetValue().strip()
            description = self.txt_description.GetValue().strip()
            category_id = self._selected_category_id()
            if self._edit_preset is not None:
                try:
                    update_preset(
                        self._edit_preset.id, name, description, category_id,
                        HELMERT7, helmert7_to_json(params),
                    )
                except ValueError as e:
                    wx.MessageBox(str(e), "Ошибка", wx.OK | wx.ICON_ERROR, self)
                    return
            else:
                save_preset(
                    name=name, description=description, method=HELMERT7,
                    params=helmert7_to_json(params), category_id=category_id,
                )

        self._result_params = params
        self.EndModal(wx.ID_OK)

    # ── Публичный API ─────────────────────────────────────────────────────────

    def get_params(self) -> Optional[TransformationParams]:
        return self._result_params
