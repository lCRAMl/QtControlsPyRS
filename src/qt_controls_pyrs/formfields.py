# formfields.py
#
# Die Teile, aus denen ein Eingabeformular besteht:
#
#   NumberField   Zahl mit Einheit und Platz für eine Meldung darunter
#   IntField      Stückzahl mit Einheit
#   ResultGrid    beschriftete Ergebniswerte in zwei Spalten
#   StaleBanner   Band über einer Anzeige, die nicht mehr aktuell ist
#
# Sie stammen aus einer Anwendung und sind hierher gewandert, weil jedes
# Programm mit Messwerten sie wieder braucht. Gezeichnet wird im Halo-Stil:
# die Zahlenfelder benutzen HaloSpinBox und HaloDoubleSpinBox, das
# Ergebnisraster sitzt in einer HaloGroupBox.
#
# Keiner dieser Bausteine rechnet. Das Zahlenfeld prüft nicht, ob eine Länge
# plausibel ist — es zeigt an, was ihm gemeldet wurde. Der Unterschied
# entscheidet darüber, ob eine Regel an einer Stelle steht oder in jedem
# Formular noch einmal.

from __future__ import annotations

from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget
)

from .buttons.hoverbuttons import _faded
from .halogroupbox import HaloGroupBox
from .spinboxes import HaloDoubleSpinBox, HaloSpinBox

#: Schrift für Zahlen. Feste Laufweite, damit Stellen untereinander stehen und
#: sich zwei Läufe vergleichen lassen.
MONO_FAMILY = "Consolas, 'DejaVu Sans Mono', monospace"


def mono_font(bold: bool = False, point_size: int = 0) -> QFont:
    """Eine Schrift fester Laufweite, mit Rückfall auf das, was da ist."""
    font = QFont(MONO_FAMILY.split(",")[0].strip())
    font.setStyleHint(QFont.StyleHint.Monospace)
    if point_size:
        font.setPointSize(point_size)
    font.setBold(bold)
    return font


class _UnitField(QWidget):
    """Was beide Zahlenfelder teilen: das Feld, die Einheit daneben, der Wert.

    Die Unterklasse legt an, welches Spinfeld es wird und ob darunter Platz
    für eine Meldung bleibt.
    """

    UNIT_WIDTH  = 40          # feste Breite der Einheit, damit Felder fluchten
    GAP         = 6           # Abstand zwischen Feld und Einheit
    UNIT_ALPHA  = 0.7         # Deckkraft der Einheit — sie ist Beiwerk
    ERROR       = "#ef6a5a"
    WARNING     = "#d8a92a"

    def __init__(self, unit: str, spin, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.spin = spin
        self.spin.setFont(mono_font())

        self._unit = QLabel(unit)
        self._unit.setMinimumWidth(self.UNIT_WIDTH)
        self._unit.setProperty("role", "unit")   # für Anwendungen mit eigenem Stylesheet
        palette = self._unit.palette()
        ink = palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        palette.setColor(QPalette.ColorRole.WindowText, _faded(ink, self.UNIT_ALPHA))
        self._unit.setPalette(palette)

    def _row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(self.GAP)
        row.addWidget(self.spin)
        row.addWidget(self._unit)
        row.addStretch(1)
        return row

    def unit(self) -> str:
        return self._unit.text()

    def setUnit(self, unit: str) -> None:  # noqa: N802 - Qt-Namensschema
        self._unit.setText(unit)

    def value(self):
        return self.spin.value()

    def set_value(self, value) -> None:
        """Setzt den Wert, OHNE value_changed auszulösen.

        Nötig, wenn eine Anzeige ein Feld aus dem Zustand nachführt — sonst
        entsteht eine Rückkopplung zwischen Anzeige und Zustand.
        """
        blocked = self.spin.blockSignals(True)
        self.spin.setValue(value)
        self.spin.blockSignals(blocked)

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - Qt-Namensschema
        super().setEnabled(enabled)
        self.spin.setEnabled(enabled)


class NumberField(_UnitField):
    """Zahleneingabe mit Einheit und Platz für eine Meldung darunter.

    Die Meldung steht unter dem Feld und nicht in einem Dialog: wer einen Wert
    eintippt, soll dort lesen, was daran nicht stimmt. Der Platz dafür ist
    dauerhaft reserviert — sonst springt das ganze Formular, sobald eine
    Meldung erscheint oder verschwindet.

    ``set_error()`` und ``set_warning()`` färben zusätzlich den Rahmen des
    Feldes. Das Feld selbst entscheidet nichts: es zeigt an, was ihm gemeldet
    wurde.
    """

    value_changed = pyqtSignal(float)

    #: Welches Spinfeld benutzt wird. Eine Unterklasse darf hier ein eigenes
    #: eintragen - etwa eine engere Fassung fuer ein dichtes Formular.
    SPIN = HaloDoubleSpinBox

    MIN_WIDTH    = 110        # Mindestbreite des Feldes
    NOTE_SHRINK  = 1          # Punkt kleiner als die übrige Schrift
    NOTE_MIN_PT  = 7
    NOTE_HEIGHT  = 14         # reservierter Platz für die Meldung

    #: Breite, für die die Meldung gesetzt wird — ihre WUNSCHbreite.
    #:
    #: Ausdrücklich keine Mindestbreite. Eine Meldung ist ein Ausnahmezustand;
    #: sie darf nicht bestimmen, wie breit das Feld im Normalfall sein muss.
    #: Mit einer Mindestbreite von 200 forderte jedes Zahlenfeld 200 Pixel
    #: allein für eine Zeile, die meistens leer ist — bei zwei Feldern
    #: nebeneinander also 400, und die Bedienspalte wuchs von 386 auf 842.
    #:
    #: Stattdessen bekommt die Meldung eine Größenrichtlinie, die ihren Inhalt
    #: ignoriert: sie nimmt, was die Zeile ihr gibt, und bricht darin um.
    NOTE_WIDTH   = 130

    def __init__(
        self,
        unit: str = "",
        *,
        minimum: float = 0.0,
        maximum: float = 1_000_000.0,
        decimals: int = 1,
        step: float = 1.0,
        value: float = 0.0,
        parent: QWidget | None = None,
    ) -> None:
        spin = self.SPIN()
        spin.setRange(minimum, maximum)
        spin.setDecimals(decimals)
        spin.setSingleStep(step)
        spin.setValue(value)
        spin.setKeyboardTracking(True)
        spin.setMinimumWidth(self.MIN_WIDTH)
        super().__init__(unit, spin, parent)

        self.spin.valueChanged.connect(self.value_changed.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)
        layout.addLayout(self._row())

        self._message = QLabel("")
        self._message.setWordWrap(True)
        self._message.setMinimumHeight(self.NOTE_HEIGHT)
        # Eine BESCHEIDENE Mindestbreite, nicht die volle Satzbreite: ohne sie
        # bekommt die Meldung in einem engen Raster zwei Woerter je Zeile und
        # wird achtzeilig; mit der vollen Satzbreite bestimmte sie, wie breit
        # das Feld im Normalfall sein muss. Dazwischen liegt dieser Wert.
        self._message.setMinimumWidth(self.NOTE_WIDTH)
        self._message.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        font = self._message.font()
        font.setPointSize(max(self.NOTE_MIN_PT, font.pointSize() - self.NOTE_SHRINK))
        self._message.setFont(font)
        layout.addWidget(self._message)

    def configure(
        self,
        unit: str = "",
        *,
        minimum: float | None = None,
        maximum: float | None = None,
        decimals: int | None = None,
        step: float | None = None,
        value: float | None = None,
        tooltip: str = "",
    ) -> "NumberField":
        """Setzt Einheit, Wertebereich und Schrittweite nachträglich.

        Gebraucht, wenn das Layout aus einer .ui-Datei kommt: der Qt Designer
        legt das Feld an und bestimmt, wo es sitzt — was es bedeutet, steht im
        Quelltext. Einheit und Grenzen sind Fachwissen und keine Gestaltung; in
        der XML-Datei lägen sie als namenlose Eigenschaften ohne jede Prüfung.

        Gibt sich selbst zurück, damit sich Anlegen und Einstellen in einer
        Zeile lesen lassen.
        """
        if unit:
            self.setUnit(unit)
        if decimals is not None:
            self.spin.setDecimals(decimals)
        if minimum is not None or maximum is not None:
            self.spin.setRange(
                self.spin.minimum() if minimum is None else minimum,
                self.spin.maximum() if maximum is None else maximum,
            )
        if step is not None:
            self.spin.setSingleStep(step)
        if value is not None:
            self.set_value(value)
        if tooltip:
            self.spin.setToolTip(tooltip)
        return self

    def value(self) -> float:
        return self.spin.value()

    def message(self) -> str:
        return self._message.text()

    def _note(self, message: str, color: str) -> None:
        self._message.setText(message)
        palette = self._message.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
        self._message.setPalette(palette)
        self.spin.setAlert(QColor(color))

    def set_error(self, message: str) -> None:
        self._note(message, self.ERROR)

    def set_warning(self, message: str) -> None:
        self._note(message, self.WARNING)

    def clear_message(self) -> None:
        self._message.setText("")
        self.spin.setAlert(None)


class IntField(_UnitField):
    """Ganzzahleingabe mit Einheit. Für Stückzahlen.

    Ohne Platz für eine Meldung: eine Stückzahl ist entweder im Bereich oder
    wird vom Feld gekappt, und mehr gibt es dazu nicht zu sagen.
    """

    value_changed = pyqtSignal(int)

    #: Siehe NumberField.SPIN.
    SPIN = HaloSpinBox

    MIN_WIDTH = 110

    def __init__(
        self,
        unit: str = "",
        *,
        minimum: int = 0,
        maximum: int = 1_000_000,
        value: int = 0,
        special_zero_text: str = "",
        parent: QWidget | None = None,
    ) -> None:
        spin = self.SPIN()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setMinimumWidth(self.MIN_WIDTH)
        if special_zero_text:
            # Null bedeutet hier nicht „keine", sondern „automatisch". Ohne
            # Sondertext wäre das aus der Anzeige nicht zu erkennen.
            spin.setSpecialValueText(special_zero_text)
        super().__init__(unit, spin, parent)

        self.spin.valueChanged.connect(self.value_changed.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(self.GAP)
        layout.addLayout(self._row())

    def configure(
        self,
        unit: str = "",
        *,
        minimum: int | None = None,
        maximum: int | None = None,
        value: int | None = None,
        special_zero_text: str = "",
        tooltip: str = "",
    ) -> "IntField":
        """Wie ``NumberField.configure()`` — dieselbe Aufgabenteilung."""
        if unit:
            self.setUnit(unit)
        if minimum is not None or maximum is not None:
            self.spin.setRange(
                self.spin.minimum() if minimum is None else minimum,
                self.spin.maximum() if maximum is None else maximum,
            )
        if value is not None:
            self.set_value(value)
        if special_zero_text:
            self.spin.setSpecialValueText(special_zero_text)
        if tooltip:
            self.spin.setToolTip(tooltip)
        return self

    def value(self) -> int:
        return self.spin.value()

    def set_maximum(self, maximum: int) -> None:
        """Hebt oder senkt die Obergrenze, ohne unter die Untergrenze zu rutschen."""
        self.spin.setMaximum(max(self.spin.minimum(), maximum))


class ResultGrid(HaloGroupBox):
    """Beschriftete Ergebniswerte in zwei Spalten, in einem Halo-Rahmen.

    Die Werte stehen in fester Laufweite und rechtsbündig, damit Stellen
    untereinander stehen und sich zwei Läufe vergleichen lassen. Angesprochen
    werden die Zeilen über einen Schlüssel und nicht über ihre Nummer — sonst
    verschiebt eine eingefügte Zeile alle folgenden.
    """

    CAPTION_ALPHA = 0.65      # Deckkraft der Beschriftung — der Wert zählt
    LINE_ALPHA    = 0.3       # Deckkraft einer Trennlinie
    SPACING_X     = 14
    SPACING_Y     = 4

    #: Wieviele Wertpaare nebeneinander stehen.
    #:
    #: Eins ist die schlichte Liste. Zwei halbiert die Höhe des Blocks und
    #: macht ihn dafür breiter — das lohnt, sobald die Spalte breit genug ist
    #: und der Block sonst nach unten aus dem Fenster läuft. Die Zeilen füllen
    #: sich dabei von links nach rechts, erst dann kommt die nächste.
    COLUMNS = 1

    #: Abstand zwischen zwei Wertpaaren, wenn mehrere nebeneinander stehen.
    PAIR_GAP = 26

    def __init__(self, title: str = "Ergebnis", parent: QWidget | None = None) -> None:
        super().__init__(title, parent)
        self._grid = QGridLayout(self)
        self._apply_margins()   # die Raender der HaloGroupBox gelten fuer dieses Raster
        self._grid.setHorizontalSpacing(self.SPACING_X)
        self._grid.setVerticalSpacing(self.SPACING_Y)
        for paar in range(max(self.COLUMNS, 1)):
            self._grid.setColumnStretch(2 * paar + 1, 1)
            if paar:
                self._grid.setColumnMinimumWidth(2 * paar, self.PAIR_GAP)
        self._rows: dict[str, QLabel] = {}
        self._row_index = 0          # laufende Nummer der Zeile, nicht des Rasters

    def _cell(self) -> tuple[int, int]:
        """Rasterzeile und erste Rasterspalte für den nächsten Eintrag."""
        paare = max(self.COLUMNS, 1)
        return self._row_index // paare, 2 * (self._row_index % paare)

    def _ink(self) -> QColor:
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText
        )

    def add_row(self, key: str, label: str, value: str = "-") -> None:
        caption = QLabel(label)
        palette = caption.palette()
        palette.setColor(QPalette.ColorRole.WindowText,
                         _faded(self._ink(), self.CAPTION_ALPHA))
        caption.setPalette(palette)

        display = QLabel(value)
        display.setFont(mono_font())
        display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # Zahlen zum Herauskopieren — sonst tippt sie jemand ab.
        display.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        zeile, spalte = self._cell()
        self._grid.addWidget(caption, zeile, spalte)
        self._grid.addWidget(display, zeile, spalte + 1)
        self._rows[key] = display
        self._row_index += 1

    def add_separator(self) -> None:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        palette = line.palette()
        palette.setColor(QPalette.ColorRole.WindowText,
                         _faded(self._ink(), self.LINE_ALPHA))
        line.setPalette(palette)

        # Eine Trennlinie geht IMMER ueber die volle Breite und beginnt eine
        # neue Zeile. Mitten in einer Zeile waere sie keine Trennung mehr,
        # sondern ein Strich zwischen zwei Werten.
        paare = max(self.COLUMNS, 1)
        if self._row_index % paare:
            self._row_index += paare - (self._row_index % paare)
        zeile, _ = self._cell()
        self._grid.addWidget(line, zeile, 0, 1, 2 * paare)
        self._row_index += paare

    def set_value(self, key: str, value: str, color: str = "") -> None:
        """Setzt eine Zeile. Eine unbekannte Zeile wird still übergangen."""
        label = self._rows.get(key)
        if label is None:
            return
        label.setText(value)
        font = label.font()
        font.setBold(bool(color))
        label.setFont(font)
        palette = label.palette()
        palette.setColor(
            QPalette.ColorRole.WindowText,
            QColor(color) if color else self._ink(),
        )
        label.setPalette(palette)

    def clear_values(self, placeholder: str = "-") -> None:
        for key in self._rows:
            self.set_value(key, placeholder)

    def keys(self) -> tuple[str, ...]:
        return tuple(self._rows)


class StaleBanner(QFrame):
    """Hinweisband über einer Anzeige, die nicht mehr aktuell ist.

    Gedacht für den Fall, dass sich die Eingaben geändert haben und das
    angezeigte Ergebnis noch zu den alten gehört. Es bleibt stehen — es war ja
    richtig, nur eben für etwas anderes — und bekommt dieses Band darüber.

    Versteckt sich selbst, solange es nichts zu sagen hat.
    """

    COLOR      = "#d8b44a"    # Rahmen und Schrift
    BACKGROUND = "#3a3222"    # getönte Fläche darunter
    RADIUS     = 2
    PAD_X      = 9
    PAD_Y      = 5

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(self.PAD_X, self.PAD_Y, self.PAD_X, self.PAD_Y)

        self._label = QLabel("")
        self._label.setWordWrap(True)
        font = self._label.font()
        font.setBold(True)
        self._label.setFont(font)
        palette = self._label.palette()
        palette.setColor(QPalette.ColorRole.WindowText, QColor(self.COLOR))
        self._label.setPalette(palette)
        layout.addWidget(self._label)
        layout.addStretch(1)

        self.setVisible(False)

    def message(self) -> str:
        return self._label.text()

    def show_message(self, message: str) -> None:
        self._label.setText(message)
        self.setVisible(True)

    def hide_message(self) -> None:
        self.setVisible(False)

    def paintEvent(self, event) -> None:
        # Gezeichnet statt über ein Stylesheet gesetzt, wie überall in dieser
        # Sammlung: ein Stylesheet an einem Widget schlägt sonst auf alle
        # Kinder durch, und die Beschriftung bekäme den Rahmen gleich mit.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = float(self.RADIUS)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.BACKGROUND))
        painter.drawRoundedRect(box, radius, radius)

        painter.setPen(QPen(QColor(self.COLOR), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(box, radius, radius)
        painter.end()
        super().paintEvent(event)
