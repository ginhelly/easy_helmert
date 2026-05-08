# -*- coding: utf-8 -*-
"""
main.py — точка входа Easy Helmert (PySide6).
Загружает QSS-тему и запускает главное окно.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from gui.forms.easy_helmert_base import BaseMainFrame


def load_theme(app: QApplication, qss_path: Path) -> None:
    if qss_path.exists():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
    else:
        print(f"[WARN] theme not found: {qss_path}")


def main() -> None:
    # Включить HiDPI до создания QApplication
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Easy Helmert")
    app.setOrganizationName("EasyHelmert")

    # Базовый шрифт — Segoe UI Variable 13px (Windows 11)
    font = QFont("Segoe UI Variable", 9)
    font.setWeight(QFont.Weight.Normal)
    font.setHintingPreference(QFont.HintingPreference.PreferDefaultHinting)
    app.setFont(font)

    # QSS-тема — ищем рядом со скриптом, потом resources/
    here = Path(__file__).parent
    theme_candidates = [
        here / "theme.qss",
        here / "resources" / "theme.qss",
        here.parent / "resources" / "theme.qss",
    ]
    for candidate in theme_candidates:
        if candidate.exists():
            load_theme(app, candidate)
            break

    window = BaseMainFrame()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()