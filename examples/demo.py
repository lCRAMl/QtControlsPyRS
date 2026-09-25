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
    AnimatedToggle, DashBorderButton, FiberHaloButton, FrameButton, FrameToggle,
    GlowButton, HaloButton, HaloCheckBox, HaloDropdown, HaloPromptBox,
    HaloTabWidget, HeartCheckBox, LineToggle, PromptEditor, PulseHaloButton,
    RaisedButton, ReferenceThumb, ShineButton, SpreadButton, StatusBar
)

class FolderDropdown(HaloDropdown):
    """Eigene Einstellungen gehören in eine Unterklasse — hier: sortiert."""

    SORTED = True       # deutsch sortiert: Ä bei A, "Ordner 2" vor "Ordner 10"


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
        self.resize(720, 1020)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 12)
        # Eng gesetzt, damit alle Abschnitte ins Fenster passen.
        layout.setSpacing(12)

        # Die Statuszeile wird als Letztes aufgebaut, weil sie im Layout ganz
        # unten sitzt. Die Handler hier oben benutzen sie erst beim Klicken,
        # die Reihenfolge stört also nicht.

        # ------------------------------------------------------------------
        # HaloPromptBox — Eingabefeld, das sich über den Inhalt darunter
        # ausfahren lässt
        #
        # Im Layout steht nur ein Platzhalter, das Feld selbst schwebt darüber.
        # Ein Klick auf den Doppelpfeil oben rechts fährt es bis zur
        # Statuszeile aus, ein zweiter Klick oder Escape fährt es wieder ein.
        # Wie weit es ausfahren darf, wird unten gesetzt (set_expand_stop),
        # sobald die Statuszeile steht.
        # ------------------------------------------------------------------
        self.prompt_slot = QWidget()
        self.prompt_slot.setFixedHeight(62)     # gut zwei Zeilen; ausgefahren viel mehr
        self.prompt_slot.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        layout.addWidget(self.prompt_slot)

        self.prompt_box = HaloPromptBox(self.prompt_slot, self)
        self.prompt_box.setPlaceholderText("Prompt eingeben ...")
        self.prompt_box.expanded_changed.connect(self.prompt_box_expanded)

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
        # HaloTabWidget — Reiter statt QTabWidget; beim Wechsel gleitet ein
        # Strich zum neuen Reiter, und der Inhalt schiebt sich seitlich
        # hinaus, während der nächste hereinkommt
        #
        # Aufgeteilt wie später im APIImageGenerator: auf dem ersten Reiter
        # die Einstellungen — die Halo-Schalter und das Dropdown aus den
        # nächsten beiden Abschnitten —, auf dem zweiten das Prompt-Feld.
        # ------------------------------------------------------------------
        self.tabs = HaloTabWidget()
        layout.addWidget(self.tabs)

        # Erster Reiter: eine leere Seite mit eigenem Layout. Die nächsten
        # beiden Abschnitte hängen ihre Widgets hier hinein statt ins Fenster.
        settings_page = QWidget()
        self.settings = QVBoxLayout(settings_page)
        self.settings.setContentsMargins(0, 16, 0, 0)
        self.settings.setSpacing(18)
        self.tabs.addTab(settings_page, "Einstellungen")

        # Zweiter Reiter: das Prompt-Feld füllt die ganze Seite.
        prompt_page = QWidget()
        prompt_layout = QVBoxLayout(prompt_page)
        prompt_layout.setContentsMargins(0, 16, 0, 0)
        self.prompt_editor = PromptEditor(["Motiv", "Stil", "Kamera"])
        prompt_layout.addWidget(self.prompt_editor)
        self.tabs.addTab(prompt_page, "Prompt")

        # Erst jetzt verbinden: addTab() meldet den ersten Reiter schon als
        # Wechsel, und die Statuszeile gibt es zu dem Zeitpunkt noch nicht.
        self.tabs.currentChanged.connect(self.tab_changed)

        # ------------------------------------------------------------------
        # Schalter im Halo-Stil — drei Formen, die zu den Halo-Knöpfen und
        # zum Dropdown passen: feine Linien, weiß unter der Maus, an in der
        # Signalfarbe
        # ------------------------------------------------------------------
        halo_toggles = QHBoxLayout()
        halo_toggles.setSpacing(24)
        self.settings.addLayout(halo_toggles)       # auf dem ersten Reiter

        # FrameToggle: eine Kugel gleitet in einem feinen Rahmen
        self.frame_toggle = FrameToggle("Rahmen")
        self.frame_toggle.toggled.connect(
            lambda on: self.status.setText(f"FrameToggle: {'an' if on else 'aus'}")
        )
        halo_toggles.addWidget(self.frame_toggle)

        # LineToggle: eine Kugel läuft auf einem Strich, der hinter ihr leuchtet
        self.line_toggle = LineToggle("Linie")
        self.line_toggle.toggled.connect(
            lambda on: self.status.setText(f"LineToggle: {'an' if on else 'aus'}")
        )
        halo_toggles.addWidget(self.line_toggle)

        # HaloCheckBox: füllt sich, und einmal läuft ein Strich nach außen
        self.halo_checkbox = HaloCheckBox("Kästchen")
        self.halo_checkbox.toggled.connect(
            lambda on: self.status.setText(f"HaloCheckBox: {'an' if on else 'aus'}")
        )
        halo_toggles.addWidget(self.halo_checkbox)

        halo_toggles.addStretch(1)

        # ------------------------------------------------------------------
        # HaloDropdown — Auswahlfeld statt QComboBox; beim Aufklappen rollt
        # die Liste auf, die Einträge gleiten nach
        # ------------------------------------------------------------------
        # Ein Buchstabe springt zum passenden Eintrag, auch bei geschlossener
        # Liste. Der Platzhalter steht da, solange nichts gewählt ist.
        self.folder_dropdown = FolderDropdown()
        self.folder_dropdown.setPlaceholderText("Ordner wählen")
        self.folder_dropdown.addItems(
            ["Tiere", "Portraits", "Architektur", "Landschaft", "Produkte"]
        )
        self.folder_dropdown.setCurrentIndex(-1)
        self.folder_dropdown.currentTextChanged.connect(self.folder_changed)
        self.settings.addWidget(self.folder_dropdown)   # auf dem ersten Reiter
        self.settings.addStretch(1)

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

        # Jetzt steht fest, wie weit das Prompt-Feld ausfahren darf: bis an
        # die Statuszeile, die dadurch sichtbar bleibt.
        self.prompt_box.set_expand_stop(self.status_slot)

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
    # Handler: HaloPromptBox
    # ----------------------------------------------------------------------

    def prompt_box_expanded(self, expanded: bool) -> None:
        if expanded:
            self.status.setText("Prompt-Feld ausgefahren — Escape fährt es ein")
            return
        self.status.setText("Prompt-Feld eingefahren")

    # ----------------------------------------------------------------------
    # Handler: HaloTabWidget
    # ----------------------------------------------------------------------

    def tab_changed(self, index: int) -> None:
        self.status.setText(f"Reiter: {self.tabs.tabText(index)}")

    # ----------------------------------------------------------------------
    # Handler: HaloDropdown
    # ----------------------------------------------------------------------

    def folder_changed(self, text: str) -> None:
        self.status.setText(f"Ordner: {text}")

    # ----------------------------------------------------------------------
    # Handler: GlowButton — Aufgabe starten und nach 6 Sekunden beenden
    # ----------------------------------------------------------------------

    def start_glow_task(self) -> None:
        # Ohne Ordner geht es nicht los — der Rahmen des Dropdowns blinkt rot.
        if self.folder_dropdown.currentIndex() < 0:
            self.folder_dropdown.flash()
            self.status.setText("Erst einen Ordner wählen")
            return

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
        # Prompt-Feld und Statuszeile schweben, deshalb müssen sie der Größe
        # folgen.
        self.prompt_box.sync_geometry()
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
