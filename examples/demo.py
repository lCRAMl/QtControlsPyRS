"""Zeigt alle Widgets der Sammlung in einem Fenster.

    python examples/demo.py
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QSizePolicy, QStyleFactory, QVBoxLayout, QWidget
)

from qt_controls_pyrs import AnimatedToggle, GlowButton, StatusBar

LONG_MESSAGE = (
    "Fehler: Unbekanntes Status-Antwortformat. Beispiel-Antwort: "
    "{'code': 200, 'msg': 'success', 'data': {'taskId': 'abc123', 'state': 'waiting', "
    "'failMsg': 'Eine absichtlich sehr lange Meldung, die in eine einzige Zeile "
    "niemals hineinpasst und deshalb kurz aufklappt.'}}"
)


def dark_palette(app: QApplication) -> None:
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window,          QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText,      Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base,            QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.Text,            Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button,          QColor(45, 45, 45))
    palette.setColor(QPalette.ColorRole.ButtonText,      Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Highlight,       QColor(90, 140, 255))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
    app.setPalette(palette)


class Demo(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qt-controls-pyrs – Demo")
        self.resize(560, 320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(18)

        # --- Schiebeschalter ---
        toggles = QHBoxLayout()
        toggles.setSpacing(24)
        self.toggle_a = AnimatedToggle("Daten nach dem Laden aufräumen")
        self.toggle_a.setChecked(True)
        self.toggle_b = AnimatedToggle("Autoretry")
        toggles.addWidget(self.toggle_a)
        toggles.addWidget(self.toggle_b)
        toggles.addStretch(1)
        layout.addLayout(toggles)

        self.toggle_a.toggled.connect(
            lambda on: self.status.setText(f"Aufräumen: {'an' if on else 'aus'}")
        )
        self.toggle_b.toggled.connect(
            lambda on: self.status.setText(f"Autoretry: {'an' if on else 'aus'}")
        )

        # --- Knopf mit Arbeitsanzeige ---
        self.button = GlowButton("✨ Generate AI", busy_text="Generating")
        self.button.setFixedHeight(50)
        self.button.setFont(QFont("", 14, QFont.Weight.Bold))
        self.button.clicked.connect(self.run_task)
        layout.addWidget(self.button)

        hint = QLabel(
            "Knopf drücken: Beschriftung blendet über, der Rahmen leuchtet.\n"
            "Nach 6 Sekunden kommt eine lange Meldung in die Statuszeile."
        )
        hint.setStyleSheet("color:#909090;")
        layout.addWidget(hint)
        layout.addStretch(1)

        # --- Statuszeile: Platzhalter im Layout, Anzeige schwebt darüber ---
        self.slot = QWidget()
        self.slot.setFixedHeight(20)
        self.slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.slot)

        self.status = StatusBar(self.slot, self)
        self.status.setText("Bereit")

        QTimer.singleShot(0, self.status.sync_geometry)

    def run_task(self) -> None:
        self.button.setEnabled(False)
        self.button.start_busy()
        self.status.setText("Aufgabe läuft ...")
        QTimer.singleShot(6000, self.finish_task)

    def finish_task(self) -> None:
        self.button.stop_busy()
        self.button.setEnabled(True)
        self.status.setText(LONG_MESSAGE)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.status.sync_geometry()


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    dark_palette(app)

    demo = Demo()
    demo.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
