"""
utils/resources.py — единая точка поиска папки resources и её содержимого.

Порядок поиска:
  1. PyInstaller bundle (_MEIPASS)
  2. Относительно текущего файла (разработка)
  3. Относительно cwd (запуск из корня проекта)
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional


# ── Поиск корня resources ─────────────────────────────────────────────────────

def _resources_candidates() -> list[Path]:
    candidates = []

    # 1. PyInstaller
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "resources")

    # 2. Относительно utils/resources.py → ../../resources
    here = Path(__file__).resolve().parent
    candidates.append(here.parent / "resources")          # src/resources
    candidates.append(here.parent.parent / "resources")   # project_root/resources

    # 3. От cwd
    candidates.append(Path.cwd() / "resources")

    return candidates


def find_resources_dir() -> Optional[Path]:
    """Возвращает Path к папке resources или None если не найдена."""
    for c in _resources_candidates():
        if c.is_dir():
            return c
    return None


def get_resource(relative_path: str) -> Optional[Path]:
    """
    Возвращает Path к файлу внутри resources.
    relative_path — путь относительно resources/, например 'combined_crs.db'
    или 'icons/import.png'.
    Возвращает None если файл не найден.
    """
    for c in _resources_candidates():
        p = c / relative_path
        if p.exists():
            return p
    return None


def require_resource(relative_path: str) -> Path:
    """
    То же что get_resource, но бросает FileNotFoundError если не найдено.
    Используется там, где файл обязателен для работы.
    """
    p = get_resource(relative_path)
    if p is None:
        searched = "\n  ".join(
            str(c / relative_path) for c in _resources_candidates()
        )
        raise FileNotFoundError(
            f"Файл ресурса не найден: {relative_path}\n"
            f"Искали в:\n  {searched}"
        )
    return p