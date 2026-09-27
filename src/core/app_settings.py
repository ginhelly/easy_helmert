"""
core/app_settings.py — общие настройки программы (не привязаны к конкретному
расчёту), хранятся в %APPDATA%/EasyHelmert/settings.json.

Пока единственная настройка — способ расчёта ондуляций геоида
(GeoidUndulationMethod, диалог "Программа → Настройки").
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from core.geoid_correction import GeoidUndulationMethod
from utils.user_data import get_user_data_dir

_SETTINGS_FILENAME = "settings.json"


@dataclass
class AppSettings:
    geoid_undulation_method: GeoidUndulationMethod = GeoidUndulationMethod.NAIVE_FIT
    geoid_trusted_preset_id: Optional[int] = None


def _settings_path():
    return get_user_data_dir() / _SETTINGS_FILENAME


def load_app_settings() -> AppSettings:
    path = _settings_path()
    if not path.exists():
        return AppSettings()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AppSettings(
            geoid_undulation_method=GeoidUndulationMethod(
                int(data.get("geoid_undulation_method", 0))
            ),
            geoid_trusted_preset_id=data.get("geoid_trusted_preset_id"),
        )
    except Exception:
        return AppSettings()


def save_app_settings(settings: AppSettings) -> None:
    data = {
        "geoid_undulation_method": int(settings.geoid_undulation_method),
        "geoid_trusted_preset_id": settings.geoid_trusted_preset_id,
    }
    _settings_path().write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
