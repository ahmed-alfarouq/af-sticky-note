"""Application entry point / bootstrap.

Phase 1 responsibility only: create the QApplication and show a
minimal window, to verify PySide6, Arabic text rendering, and RTL
layout direction work end-to-end. No domain/database logic yet.
"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from app.config.settings import APP_NAME, ORG_NAME


def _build_window() -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle(APP_NAME)
    window.resize(320, 200)

    label = QLabel("دايلي ستيكي — تشغيل تجريبي للمرحلة الأولى")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    window.setCentralWidget(label)
    return window


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(ORG_NAME)
    app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

    window = _build_window()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())