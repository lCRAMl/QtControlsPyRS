"""Vorlage: so bindet man die Widgets dieser Sammlung in ein Fenster ein.

Jeder Abschnitt steht für sich und ist in derselben Reihenfolge aufgebaut:
Widget erzeugen, einstellen, Signale verbinden, ins Layout hängen. Zum
Übernehmen kopiert man den passenden Abschnitt heraus.

    python examples/demo.py
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QSizePolicy, QStyleFactory, QVBoxLayout,
    QWidget
)

from qt_controls_pyrs import (
    AnimatedToggle, DashBorderButton, FiberHaloButton, FrameButton, GlowButton,
    HaloButton, HeartCheckBox, PulseHaloButton, RaisedButton, ReferenceThumb,
    ShineButton, SpreadButton, StatusBar
)

LONG_MESSAGE = (
    "Fehler: Unbekanntes Status-Antwortformat. Beispiel-Antwort: "
    "{'code': 200, 'msg': 'success', 'data': {'taskId': 'abc123', 'state': 'waiting', "
    "'failMsg': 'Eine absichtlich sehr lange Meldung, die in eine einzige Zeile "
    "niemals hineinpasst und deshalb kurz aufklappt.'}}"
)


def dark_palette(app: QApplication) -> None:
    """Dunkle Palette. Die Widgets holen ihre Farben daraus, sonst nirgendwoher."""
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
    """Ein Fenster, das jedes Widget der Sammlung einmal zeigt."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("qt-controls-pyrs – Demo")
        self.resize(720, 900)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 12)
        layout.setSpacing(18)

        # Die Statuszeile wird als Letztes aufgebaut, weil sie im Layout ganz
        # unten sitzt. Die Handler hier oben benutzen sie erst beim Klicken,
        # die Reihenfolge stört also nicht.

        # ------------------------------------------------------------------
        # AnimatedToggle — Schiebeschalter statt QCheckBox
        # ------------------------------------------------------------------
        toggles = QHBoxLayout()
        toggles.setSpacing(24)
        layout.addLayout(toggles)

        self.cleanup_toggle = AnimatedToggle("Daten nach dem Laden aufräumen")
        self.cleanup_toggle.setChecked(True)
        self.cleanup_toggle.toggled.connect(self.cleanup_toggled)
        toggles.addWidget(self.cleanup_toggle)

        self.retry_toggle = AnimatedToggle("Autoretry")
        self.retry_toggle.toggled.connect(self.retry_toggled)
        toggles.addWidget(self.retry_toggle)

        toggles.addStretch(1)

        # ------------------------------------------------------------------
        # GlowButton — zeigt mit Regenbogenrahmen, dass eine Aufgabe läuft
        # ------------------------------------------------------------------
        self.glow_button = GlowButton("✨ Generate AI", busy_text="✨ Generating")
        self.glow_button.setFixedHeight(50)
        self.glow_button.setFont(QFont("", 14, QFont.Weight.Bold))
        self.glow_button.clicked.connect(self.start_glow_task)
        layout.addWidget(self.glow_button)

        # ------------------------------------------------------------------
        # FrameButton — gibt unter der Maus seinen Schleier ab und fängt
        # dafür einen Rahmen ein, der von außen hereinfährt
        # ------------------------------------------------------------------
        frames = QHBoxLayout()
        frames.setSpacing(12)
        layout.addLayout(frames)

        self.frame_button = FrameButton("Mit Rahmen")
        self.frame_button.setFixedHeight(44)
        self.frame_button.setMinimumWidth(160)
        self.frame_button.clicked.connect(
            lambda: self.status.setText("FrameButton gedrückt")
        )
        frames.addWidget(self.frame_button)
        frames.addStretch(1)

        # ------------------------------------------------------------------
        # Die fünf Knöpfe aus der CSS-Sammlung .btn-1 … .btn-5
        # ------------------------------------------------------------------
        effects = QGridLayout()
        effects.setHorizontalSpacing(16)
        effects.setVerticalSpacing(10)
        effects.setColumnStretch(3, 1)
        layout.addLayout(effects)

        # .btn-1: der geschlossene Rahmen schnurrt zu einem kurzen Strich zusammen
        self.dash_button = DashBorderButton("Dash")
        self.dash_button.clicked.connect(
            lambda: self.status.setText("DashBorderButton gedrückt")
        )
        effects.addWidget(self.dash_button, 0, 0)

        # .btn-2: die Schrift sperrt sich, zwei Striche wachsen aus der Mitte
        self.spread_button = SpreadButton("Spread")
        self.spread_button.clicked.connect(
            lambda: self.status.setText("SpreadButton gedrückt")
        )
        effects.addWidget(self.spread_button, 0, 1)

        # .btn-3: steht erhaben da und legt sich unter der Maus flach
        self.raised_button = RaisedButton("Raised")
        self.raised_button.clicked.connect(
            lambda: self.status.setText("RaisedButton gedrückt")
        )
        effects.addWidget(self.raised_button, 0, 2)

        # .btn-4: ein schräger Lichtstreifen wischt einmal über die Fläche
        self.shine_button = ShineButton("Shine")
        self.shine_button.clicked.connect(
            lambda: self.status.setText("ShineButton gedrückt")
        )
        effects.addWidget(self.shine_button, 1, 0)

        # .btn-5: der Strich wandert nach außen, innen glimmt es auf
        self.halo_button = HaloButton("Halo")
        self.halo_button.clicked.connect(
            lambda: self.status.setText("HaloButton gedrückt")
        )
        effects.addWidget(self.halo_button, 1, 1)

        # ------------------------------------------------------------------
        # PulseHaloButton — zeigt ruhig am Rahmen, dass eine Aufgabe läuft:
        # Striche wandern nach außen, die Beschriftung blendet über
        # ------------------------------------------------------------------
        pulses = QHBoxLayout()
        layout.addLayout(pulses)

        self.pulse_button = PulseHaloButton("Generate", busy_text="Generating")
        self.pulse_button.setMinimumWidth(240)
        self.pulse_button.clicked.connect(self.start_pulse_task)
        pulses.addWidget(self.pulse_button)
        pulses.addStretch(1)

        # ------------------------------------------------------------------
        # FiberHaloButton — dasselbe auffälliger: während der Arbeit füllen
        # ziehende Farbflächen und Glasfasern die ganze Fläche
        # ------------------------------------------------------------------
        fibers = QHBoxLayout()
        layout.addLayout(fibers)

        self.fiber_button = FiberHaloButton("Generate", busy_text="Generating")
        self.fiber_button.setMinimumWidth(240)
        self.fiber_button.clicked.connect(self.start_fiber_task)
        fibers.addWidget(self.fiber_button)
        fibers.addStretch(1)

        # ------------------------------------------------------------------
        # ReferenceThumb — sechs Bild-Miniaturen nebeneinander
        #
        # Alle sechs sind gleich aufgebaut und hängen an denselben drei
        # Handlern; den `index` liefert jedes Signal mit. Nebeneinander sieht
        # man, was eine einzelne nicht zeigt: fährt der Zeiger über eine von
        # ihnen, leuchten alle mit — jede zu ihm hin.
        # ------------------------------------------------------------------
        thumbs = QHBoxLayout()
        thumbs.setSpacing(8)
        layout.addLayout(thumbs)

        # Ohne Schlüssel bleibt es bei der Vorschau, hochgeladen wird nichts.
        imgbb_api_key = os.environ.get("IMGBB_API_KEY", "")

        self.thumb_1 = ReferenceThumb(index=0, imgbb_api_key=imgbb_api_key)
        self.thumb_1.uploaded.connect(self.thumb_uploaded)
        self.thumb_1.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_1.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_1)

        self.thumb_2 = ReferenceThumb(index=1, imgbb_api_key=imgbb_api_key)
        self.thumb_2.uploaded.connect(self.thumb_uploaded)
        self.thumb_2.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_2.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_2)

        self.thumb_3 = ReferenceThumb(index=2, imgbb_api_key=imgbb_api_key)
        self.thumb_3.uploaded.connect(self.thumb_uploaded)
        self.thumb_3.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_3.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_3)

        self.thumb_4 = ReferenceThumb(index=3, imgbb_api_key=imgbb_api_key)
        self.thumb_4.uploaded.connect(self.thumb_uploaded)
        self.thumb_4.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_4.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_4)

        self.thumb_5 = ReferenceThumb(index=4, imgbb_api_key=imgbb_api_key)
        self.thumb_5.uploaded.connect(self.thumb_uploaded)
        self.thumb_5.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_5.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_5)

        self.thumb_6 = ReferenceThumb(index=5, imgbb_api_key=imgbb_api_key)
        self.thumb_6.uploaded.connect(self.thumb_uploaded)
        self.thumb_6.upload_failed.connect(self.thumb_upload_failed)
        self.thumb_6.cleared.connect(self.thumb_cleared)
        thumbs.addWidget(self.thumb_6)

        thumbs.addStretch(1)

        # ------------------------------------------------------------------
        # HeartCheckBox — Herz zum Anhaken statt QCheckBox
        # ------------------------------------------------------------------
        hearts = QHBoxLayout()
        layout.addLayout(hearts)

        self.heart = HeartCheckBox()
        self.heart.setToolTip("Like")
        self.heart.toggled.connect(self.heart_toggled)
        hearts.addWidget(self.heart)
        hearts.addStretch(1)

        layout.addStretch(1)

        # ------------------------------------------------------------------
        # StatusBar — hängt nicht im Layout, sondern schwebt über einem
        # Platzhalter; sonst würde eine lange Meldung das Fenster breitziehen
        # ------------------------------------------------------------------
        self.status_slot = QWidget()
        self.status_slot.setFixedHeight(20)
        self.status_slot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.status_slot)

        self.status = StatusBar(self.status_slot, self)
        self.status.setText("Bereit")

        # Einmal ausrichten, sobald das Fenster seine endgültige Größe hat.
        QTimer.singleShot(0, self.status.sync_geometry)

    # ----------------------------------------------------------------------
    # Handler: AnimatedToggle
    # ----------------------------------------------------------------------

    def cleanup_toggled(self, checked: bool) -> None:
        self.status.setText(f"Aufräumen: {'an' if checked else 'aus'}")

    def retry_toggled(self, checked: bool) -> None:
        self.status.setText(f"Autoretry: {'an' if checked else 'aus'}")

    # ----------------------------------------------------------------------
    # Handler: GlowButton — Aufgabe starten und nach 6 Sekunden beenden
    # ----------------------------------------------------------------------

    def start_glow_task(self) -> None:
        self.glow_button.setEnabled(False)
        self.glow_button.start_busy()
        self.status.setText("Aufgabe läuft ...")
        QTimer.singleShot(6000, self.finish_glow_task)

    def finish_glow_task(self) -> None:
        self.glow_button.stop_busy()
        self.glow_button.setEnabled(True)
        self.status.setText(LONG_MESSAGE)

    # ----------------------------------------------------------------------
    # Handler: PulseHaloButton — läuft 6 Sekunden
    # ----------------------------------------------------------------------

    def start_pulse_task(self) -> None:
        # Die Anzeige hat der Klick schon gestartet (AUTO_BUSY).
        self.status.setText("Aufgabe läuft, der Rahmen zeigt es ...")
        QTimer.singleShot(6000, self.finish_pulse_task)

    def finish_pulse_task(self) -> None:
        self.pulse_button.stop_busy()
        self.status.setText("Aufgabe fertig")

    # ----------------------------------------------------------------------
    # Handler: FiberHaloButton — läuft 8 Sekunden
    # ----------------------------------------------------------------------

    def start_fiber_task(self) -> None:
        # Die Animation hat der Klick schon aufgeblendet (AUTO_BUSY).
        self.status.setText("Aufgabe läuft, der Knopf zeigt es ...")
        QTimer.singleShot(8000, self.finish_fiber_task)

    def finish_fiber_task(self) -> None:
        self.fiber_button.stop_busy()
        self.status.setText("Aufgabe fertig")

    # ----------------------------------------------------------------------
    # Handler: ReferenceThumb und HeartCheckBox
    # ----------------------------------------------------------------------

    def thumb_uploaded(self, index: int, url: str) -> None:
        self.status.setText(f"Bild {index + 1} hochgeladen: {url}")

    def thumb_upload_failed(self, index: int, error: str) -> None:
        self.status.setText(f"Upload von Bild {index + 1} fehlgeschlagen: {error}")

    def thumb_cleared(self, index: int) -> None:
        self.status.setText(f"Bild {index + 1} entfernt")

    def heart_toggled(self, checked: bool) -> None:
        self.status.setText("Gemerkt" if checked else "Nicht mehr gemerkt")

    # ----------------------------------------------------------------------
    # Fenster
    # ----------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Die Statuszeile schwebt, deshalb muss sie der Größe folgen.
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
