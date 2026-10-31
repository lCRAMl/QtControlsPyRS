# compact.py
#
# Dichter gesetzte Fassungen der Halo-Bedienelemente.
#
# Die Vorgaben der Bibliothek sind auf EINZELNE, großzügig gesetzte Elemente
# ausgelegt: 45 Pixel hohe Leisten mit 16 Pixel Luft ringsum. Das ist richtig
# für einen Knopf, der für sich steht. Ein Eingabeformular hat aber dreißig
# Zeilen untereinander, und dann ist aus Großzügigkeit Verschwendung geworden:
# die Spalte läuft nach unten aus dem Fenster, und zwischen zwei Zeilen steht
# mehr Luft als Inhalt.
#
# Geändert werden deshalb nur ZAHLEN, nie das Verhalten. Jede Klasse hier ist
# ihr Vorbild mit engeren Konstanten - der Halo-Schein bleibt, er braucht nur
# weniger Platz.
#
#     Höhe einer Leiste    45 -> 26 Pixel
#     Luftrand je Element  16 ->  2
#     Textabstand innen    16 ->  8
#     Abstand im Layout    18 ->  4
#
# Die Vorbilder selbst bleiben unangetastet. Wer HaloButton benutzt, bekommt
# weiterhin HaloButton - das ist der Grund, warum diese Fassungen neue Klassen
# sind und keine geänderten Vorgaben: mehrere Anwendungen hängen an dieser
# Bibliothek und sollen alle gleich aussehen, aber keine soll sich durch ein
# Update von selbst verändern.

from __future__ import annotations

from PyQt6.QtWidgets import QComboBox, QSizePolicy

from .buttons import HaloButton
from .checkboxes import HaloCheckBox, HaloRadioButton
from .dropdowns import HaloDropdown
from .formfields import IntField, NumberField, ResultGrid
from .halogroupbox import HaloGroupBox
from .halolineedit import HaloLineEdit
from .spinboxes import HaloDoubleSpinBox, HaloSpinBox


#: Höhe einer Eingabeleiste. Die Schrift braucht rund 15 Pixel, der Rest ist
#: Luft über und unter ihr - weniger als 26 wirkt gedrückt.
COMPACT_HEIGHT = 26

#: Luft je Seite, in die der Schein hinausläuft.
COMPACT_ROOM = 2

#: Abstand der Schrift zum Rahmen.
COMPACT_PAD = 8

# Die drei folgenden Zahlen liest die Bibliothek selbst NICHT.
#
# Sie sagen, wieviel Luft ZWISCHEN den Elementen steht, und das entscheidet
# das Layout der Anwendung. Sie stehen trotzdem hier, weil sie zu den Maßen
# darüber gehören: wer COMPACT_HEIGHT ändert, will fast immer auch diese
# Zahlen anpassen, und zwei Anwendungen sollen gleich dicht gesetzt sein.
# Farben, Schriften und Abstände sind in jeder Sammlung die Stelle, an der ein
# gemeinsames Aussehen anfängt.
#
# Wer sie benutzt, prüfe das mit einem eigenen Test. Eine Zahl, die niemand
# liest, verstellt sich unbemerkt — genau das war hier schon einmal der Fall.

#: Abstand zwischen zwei Zeilen eines Formulars, senkrecht.
#:
#: Das ist die Zahl, die ein Formular enger oder luftiger macht, ohne an den
#: Bedienelementen selbst etwas zu ändern.
COMPACT_SPACING = 4

#: Abstand zwischen Beschriftung und Feld, waagerecht — und zwischen zwei
#: Feldern, die nebeneinander in einer Zeile stehen.
COMPACT_SPACING_X = 8

#: Abstand zwischen zwei Gruppenrahmen und zwischen zwei Elementen einer
#: freistehenden Zeile.
#:
#: Größer als COMPACT_SPACING, und das mit Absicht: zwischen zwei Gruppen
#: gehört mehr Luft als zwischen zwei Zeilen derselben Gruppe, sonst sieht
#: das Formular aus wie eine einzige lange Liste.
COMPACT_GROUP_SPACING = 6

#: Breite, bei der eine umbrechende Beschriftung umbricht.
#:
#: Eine ausformulierte Beschriftung von acht Wörtern misst einzeilig über 600
#: Bildpunkte und zwänge eine ganze Bedienspalte auf diese Breite - eine
#: Rollfläche gibt die Mindestbreite ihres Inhalts nach außen weiter.
COMPACT_WRAP_WIDTH = 240


class CompactDropdown(HaloDropdown):
    """Auswahlfeld, eng gesetzt."""

    HEIGHT = COMPACT_HEIGHT
    ROOM = COMPACT_ROOM
    ROOM_Y = 1
    PAD = COMPACT_PAD


class CompactLineEdit(HaloLineEdit):
    """Eingabefeld, eng gesetzt."""

    HEIGHT = COMPACT_HEIGHT
    ROOM = COMPACT_ROOM
    ROOM_Y = 1
    PAD = COMPACT_PAD


class _CompactSpin:
    """Die engeren Maße beider Zahlenfelder, einmal aufgeschrieben.

    Auch die Pfeilspalte schrumpft mit: 26 Pixel waren auf eine 45 Pixel hohe
    Leiste gerechnet und sähen auf einer 26 Pixel hohen aus wie zwei Klötze.
    """

    HEIGHT = COMPACT_HEIGHT
    ROOM = COMPACT_ROOM
    ROOM_Y = 1
    PAD = COMPACT_PAD
    ARROW_ZONE = 16
    ARROW_W = 4
    ARROW_H = 3.0
    MIN_CHARS = 5


class CompactSpinBox(_CompactSpin, HaloSpinBox):
    """Ganzzahlfeld, eng gesetzt."""


class CompactDoubleSpinBox(_CompactSpin, HaloDoubleSpinBox):
    """Zahlenfeld mit Nachkommastellen, eng gesetzt."""


class CompactGroupBox(HaloGroupBox):
    """Gruppenrahmen, eng gesetzt."""

    PAD_X = COMPACT_PAD
    PAD_TOP = 4
    PAD_BOTTOM = 8
    TITLE_LEFT = 10
    TITLE_PAD = 6


class CompactButton(HaloButton):
    """Knopf, eng gesetzt.

    ROOM ist der Platz, in den der Strich unter der Maus nach AUSSEN wandert -
    bei HaloButton 16 Bildpunkte je Seite. Auf einer 45 Pixel hohen Leiste ist
    das ein Drittel, auf einer 26 Pixel hohen mehr als die Leiste selbst: der
    Knopf belegte 58 Bildpunkte, um 26 zu zeigen.

    Vier und nicht zwei wie bei den Eingabefeldern. Deren Schein ist ein
    Rahmen, der an Ort und Stelle aufglimmt; hier ist der wandernde Strich die
    ganze Wirkung, und bei zwei Bildpunkten wäre von der Bewegung nichts
    übrig.
    """

    HEIGHT = COMPACT_HEIGHT
    ROOM = 4
    PAD = 14


class StatusBarButton(HaloButton):
    """Knopf für eine Statusleiste.

    Eine Statusleiste richtet sich nach ihrem höchsten Element. Mit einem
    gewöhnlichen HaloButton darin wird sie 77 Bildpunkte hoch - 45 Pixel Höhe
    plus 16 Pixel Luft je Seite -, und die Textanzeigen daneben werden auf
    dieselben 77 mitgezogen, obwohl sie 16 brauchen. Gut anderthalb Zentimeter
    Leiste für eine Zeile Text.

    Hier zeigt eine Statusleiste kein Bedienelement, sondern eine Zahl, die
    man anklicken kann. 18 Pixel reichen für die Schrift, 3 für den Schein -
    die Leiste ist damit 26 Pixel hoch, etwa ein halber Zentimeter.
    """

    HEIGHT = 18
    ROOM = 3
    PAD = 10


class CompactCheckBox(HaloCheckBox):
    """Kästchen, eng gesetzt und mit umbrechender Beschriftung.

    Der Umbruch ist kein Schönheitsfehler, sondern nötig - siehe
    COMPACT_WRAP_WIDTH.
    """

    BOX = 13
    ROOM = 4
    GAP = 6
    WRAP_WIDTH = COMPACT_WRAP_WIDTH


class CompactRadioButton(HaloRadioButton):
    """Auswahlknopf, eng gesetzt."""

    RING = 13
    ROOM = 4
    GAP = 6
    CORE_PAD = 3.5


class CompactNumberField(NumberField):
    """Zahlenfeld mit Einheit, eng gesetzt."""

    SPIN = CompactDoubleSpinBox
    MIN_WIDTH = 72
    UNIT_WIDTH = 28
    GAP = 4
    NOTE_HEIGHT = 12


class CompactIntField(IntField):
    """Stückzahlfeld mit Einheit, eng gesetzt."""

    SPIN = CompactSpinBox
    MIN_WIDTH = 72
    UNIT_WIDTH = 28
    GAP = 4


class CompactResultGrid(ResultGrid):
    """Ergebniswerte, zweispaltig und eng gesetzt.

    Zweispaltig, weil der Block sonst nach unten aus der Spalte läuft: zehn
    bis sechzehn Werte sind in einer Spalte eine Säule.
    """

    COLUMNS = 2
    SPACING_X = 10
    SPACING_Y = 2
    PAIR_GAP = 18
    PAD_X = COMPACT_PAD
    PAD_TOP = 4
    PAD_BOTTOM = 8
    TITLE_LEFT = 10
    TITLE_PAD = 6


class WideResultGrid(CompactResultGrid):
    """Ergebniswerte über die volle Breite, vierspaltig.

    Für den Platz unter einer Zeichnung. Zweispaltig wäre der Block dort
    sieben Zeilen hoch und nimmt der Zeichnung ein Drittel ihrer Höhe -
    vierspaltig sind es vier, und die Zeichnung behält ihren Platz.
    """

    COLUMNS = 4


def compact_combo(combo: QComboBox, min_chars: int = 12, tooltip: str = "") -> QComboBox:
    """Verhindert, dass ein langer Eintrag die ganze Spalte auseinanderzieht.

    ``QComboBox`` meldet als bevorzugte Breite die des längsten Eintrags. Ein
    ausformulierter Eintrag von fünf oder sechs Wörtern macht damit
    das gesamte Formular so breit, dass es nicht mehr neben eine Zeichenfläche
    passt - und die Bedienspalte bekommt einen waagerechten Rollbalken.

    Die Breite wird deshalb auf eine feste Zeichenzahl begrenzt. Der
    vollständige Text bleibt beim Aufklappen sichtbar.

    Zum Tooltip: ohne eigenen Erklärungstext zeigt er den gekürzten Eintrag
    vollständig an und wird bei jedem Wechsel nachgeführt. Wird ein ``tooltip``
    übergeben, gilt dieser dauerhaft - eine Erklärung, was die Auswahl
    bedeutet, ist mehr wert als die Wiederholung des sichtbaren Textes.

    Ein schon gesetzter Tooltip zählt als eigener Erklärungstext und wird
    nicht überschrieben: sonst wäre die Erklärung genau dort verschwunden, wo
    sie jemand hingeschrieben hat.
    """
    combo.setSizeAdjustPolicy(
        QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
    )
    combo.setMinimumContentsLength(min_chars)
    combo.setSizePolicy(
        QSizePolicy.Policy.Expanding, combo.sizePolicy().verticalPolicy()
    )

    tooltip = tooltip or combo.toolTip()
    if tooltip:
        combo.setToolTip(tooltip)
        return combo

    def _show_full_text(_index: int = 0) -> None:
        combo.setToolTip(combo.currentText())

    combo.currentIndexChanged.connect(_show_full_text)
    _show_full_text()
    return combo
