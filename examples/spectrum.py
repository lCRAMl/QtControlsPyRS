"""Beispiel: das Spektrum an einer echten Tonquelle.

Quelle wählen, starten, zuhören. In der Mitte liegen 0 Hz, links der linke
Kanal, rechts der rechte.

Anders als `demo.py` braucht dieses Beispiel zwei Zusatzpakete:

    pip install -e .[audio]
    python examples/spectrum.py

Ohne Ton bleibt die Grundlinie stehen — das ist kein Fehler, sondern das
Ruhebild.
"""

from __future__ import annotations

import sys

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QSizePolicy, QStyleFactory, QVBoxLayout, QWidget
)

from demo import dark_palette
from qt_controls_pyrs import HaloDropdown, PulseHaloButton, StatusBar
from qt_controls_pyrs.audiosource import AudioSource, available_sources
from qt_controls_pyrs.halospectrum import HaloSpectrum


class SpectrumWindow(QWidget):
    """Ein Fenster mit Quellenauswahl, Start/Stopp und dem Spektrum."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qt-controls-pyrs – Spektrum")
        self.resize(760, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(12)

        # ------------------------------------------------------------------
        # Quellenauswahl — die Liste kommt aus audiosource
        #
        # Zuerst stehen die Ausgaben („Systemton"): sie werden mitgehört,
        # dann die Eingänge wie Mikrofon oder Line-In.
        # ------------------------------------------------------------------
        self.sources: list[AudioSource] = available_sources()

        self.source_dropdown = HaloDropdown()
        self.source_dropdown.setPlaceholderText("Tonquelle wählen")
        for source in self.sources:
            self.source_dropdown.addItem(source.name)
        self.source_dropdown.setCurrentIndex(0 if self.sources else -1)
        layout.addWidget(self.source_dropdown)

        # ------------------------------------------------------------------
        # Start und Stopp
        # ------------------------------------------------------------------
        buttons = QHBoxLayout()
        layout.addLayout(buttons)

        self.listen_button = PulseHaloButton("Zuhören")
        self.listen_button.setMinimumWidth(220)
        self.listen_button.clicked.connect(self.toggle_listening)
        buttons.addWidget(self.listen_button)
        buttons.addStretch(1)

        # ------------------------------------------------------------------
        # HaloSpectrum — die Anzeige selbst
        # ------------------------------------------------------------------
        self.spectrum = HaloSpectrum()
        self.spectrum.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.spectrum.failed.connect(self.listening_failed)
        layout.addWidget(self.spectrum, 1)

        # ------------------------------------------------------------------
        # Statuszeile, wie in der Demo
        # ------------------------------------------------------------------
        self.status_slot = QWidget()
        self.status_slot.setFixedHeight(20)
        self.status_slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.status_slot)

        self.status = StatusBar(self.status_slot, self)
        if self.sources:
            self.status.setText(f"{len(self.sources)} Quellen gefunden")
        else:
            self.status.setText(
                "Keine Quelle gefunden — fehlt das Paket soundcard? "
                "pip install -e .[audio]"
            )

        QTimer.singleShot(0, self.status.sync_geometry)

    # ----------------------------------------------------------------------
    # Zuhören
    # ----------------------------------------------------------------------

    def toggle_listening(self) -> None:
        if self.spectrum.is_running():
            self.stop_listening()
            return
        self.start_listening()

    def start_listening(self) -> None:
        index = self.source_dropdown.currentIndex()
        if index < 0:
            self.source_dropdown.flash()
            self.status.setText("Erst eine Quelle wählen")
            return

        source = self.sources[index]
        self.spectrum.start(source)
        if not self.spectrum.is_running():
            return          # der Grund kam schon über `failed`

        self.listen_button.setText("Stopp")
        self.status.setText(f"Zuhören: {source.name}")

    def stop_listening(self) -> None:
        self.spectrum.stop()
        self.listen_button.setText("Zuhören")
        self.status.setText("Gestoppt")

    def listening_failed(self, message: str) -> None:
        self.listen_button.setText("Zuhören")
        self.status.setText(message)

    # ----------------------------------------------------------------------
    # Fenster
    # ----------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.status.sync_geometry()

    def closeEvent(self, event) -> None:
        # Der Aufnahme-Thread muss stehen, bevor das Fenster verschwindet.
        self.spectrum.stop()
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    dark_palette(app)

    window = SpectrumWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
