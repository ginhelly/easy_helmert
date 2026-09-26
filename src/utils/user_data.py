"""
utils/user_data.py — каталог для пользовательских данных приложения
(в отличие от resources/, который бандлится с приложением и может быть
read-only при установке в Program Files).
"""
from __future__ import annotations

import os
from pathlib import Path


def get_user_data_dir() -> Path:
    """<APPDATA>/EasyHelmert (или домашняя папка, если APPDATA не задан)."""
    base = Path(os.environ.get("APPDATA") or Path.home())
    d = base / "EasyHelmert"
    d.mkdir(parents=True, exist_ok=True)
    return d
