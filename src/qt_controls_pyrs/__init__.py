"""qt_controls_pyrs – Bedienelemente für PyQt6-Anwendungen.

Eigenständige Widgets und Helfer, die sich wie ihre Qt-Vorbilder verhalten:

* :class:`GlowButton` – Knopf, der während einer laufenden Aufgabe die
  Beschriftung überblendet und den Rahmen in wandernden Regenbogenfarben
  leuchten lässt.
* :class:`FrameButton` – Knopf, der unter der Maus seinen Schleier abgibt und
  einen feinen Rahmen von außen hereinfahren lässt.
* :class:`DashBorderButton`, :class:`SpreadButton`, :class:`RaisedButton`,
  :class:`ShineButton`, :class:`HaloButton` – fünf Knöpfe aus einer
  CSS-Sammlung, jeder mit einer eigenen Bewegung unter der Maus.
* :class:`PulseHaloButton` – wie :class:`HaloButton`, lässt während einer
  laufenden Aufgabe aber Striche aus dem Rahmen wandern.
* :class:`FiberHaloButton` – dasselbe auffälliger: ziehende Farbflächen
  und schwingende Fasern füllen die ganze Fläche.
* :class:`HaloDropdown` – Auswahlfeld statt ``QComboBox`` im Stil der
  Halo-Knöpfe; die Liste kommt beim Aufklappen aus der Tiefe herein.
* :class:`HaloLineEdit` – einzeilige Eingabe statt ``QLineEdit`` mit
  derselben Leiste; hell, solange die Maus darauf steht oder darin
  geschrieben wird.
* :class:`HaloSpinBox`, :class:`HaloDoubleSpinBox` – Zahlenfelder statt
  ``QSpinBox`` und ``QDoubleSpinBox``, mit zwei feinen Pfeilen rechts.
* :class:`HaloGroupBox` – Gruppenrahmen statt ``QGroupBox``; die
  Überschrift sitzt in einer Lücke im oberen Strich.
* :class:`HaloImageView` – Bildvorschau mit dem Rahmen der HaloPromptBox,
  Platzhaltertext und eingebauter Warte-Animation (pulsierende Symbole über
  dem weichgezeichneten Bild).
* :class:`HaloPromptBox` – mehrzeilige Eingabe im Halo-Stil, die sich über
  den Inhalt darunter ausfahren lässt.
* :class:`HaloScrollBar` – Bildlaufleiste als glühendes Band, das sich beim
  Scrollen wellt; senkrecht wie waagerecht.
* :class:`HaloTabWidget` – Reiter statt ``QTabWidget``; beim Wechsel gleitet
  ein Strich zum neuen Reiter, und der Inhalt schiebt sich seitlich hinaus,
  während der nächste hereinkommt.
* :class:`AnimatedToggle` – Schiebeschalter als Ersatz für ``QCheckBox``.
* :class:`FrameToggle`, :class:`LineToggle`, :class:`HaloCheckBox` – Schalter im
  Halo-Stil: ein Rahmen mit gleitender Kugel, ein Strich mit laufender Kugel
  und ein Kästchen, aus dem beim Anhaken ein Strich nach außen läuft.
* :class:`HaloRadioButton` – Auswahlknopf statt ``QRadioButton``: ein
  Ring, der sich beim Wählen füllt und einmal einen Ring nach außen
  schickt.
* :class:`HeartCheckBox` – Herz zum Anhaken, das sich mit einem Hüpfer
  füllt und Funken wegstieben lässt.
* :class:`NumberField`, :class:`IntField` – Zahl und Stückzahl mit Einheit
  daneben; das Zahlenfeld hält darunter Platz für eine Meldung und färbt
  bei :meth:`NumberField.set_error` den Rahmen.
* :class:`ResultGrid` – beschriftete Ergebniswerte in zwei Spalten, in
  einem Halo-Rahmen; die Zahlen stehen in fester Laufweite untereinander.
* :class:`StaleBanner` – Band über einer Anzeige, die nicht mehr zu den
  aktuellen Eingaben gehört.
* :class:`StatusBar` – Statuszeile, die lange Meldungen kurz aufklappt, ohne
  die Fensteraufteilung zu verändern.
* :class:`ReferenceThumb` – Bild-Miniatur als Karte, deren Rahmen dem Zeiger
  nachleuchtet; lädt die gewählte Datei zu ImgBB hoch und zeigt den Fortschritt.
* :class:`PromptEditor` – Eingabefeld, das Abschnittsüberschriften hervorhebt.
* :func:`flash_taskbar` – lässt den Taskleisten-Eintrag blinken (Windows).
* ``Compact…`` – dichter gesetzte Fassungen von Knopf, Auswahlfeld,
  Eingabefeld, Zahlenfeld, Gruppenrahmen, Kästchen, Auswahlknopf und
  Ergebnisraster, dazu :class:`StatusBarButton` und :class:`WideResultGrid`.
  Für Formulare mit dreißig Zeilen untereinander, wo die großzügigen Vorgaben
  zur Verschwendung werden. Die Vorbilder selbst bleiben unverändert.
* :func:`compact_combo` – begrenzt die Breite eines Auswahlfeldes auf eine
  Zeichenzahl, damit ein langer Eintrag nicht das ganze Formular aufzieht.
"""

from .buttons import (
    BusyHaloButton, DashBorderButton, FiberHaloButton, FrameButton,
    GenerateButton, GlowButton, HaloButton, PulseHaloButton, RaisedButton,
    ShineButton, SpreadButton
)
from .checkboxes import (
    AnimatedToggle, FrameToggle, HaloCheckBox, HaloRadioButton, HeartCheckBox,
    LineToggle
)
from .compact import (
    COMPACT_GROUP_SPACING, COMPACT_HEIGHT, COMPACT_PAD, COMPACT_ROOM,
    COMPACT_SPACING, COMPACT_SPACING_X, COMPACT_WRAP_WIDTH, CompactButton, CompactCheckBox, CompactDoubleSpinBox,
    CompactDropdown, CompactGroupBox, CompactIntField, CompactLineEdit,
    CompactNumberField, CompactRadioButton, CompactResultGrid,
    CompactSpinBox, StatusBarButton, WideResultGrid, compact_combo
)
from .dropdowns import HaloDropdown
from .flashtaskbar import flash_taskbar, stop_flashing
from .formfields import (
    IntField, MONO_FAMILY, NumberField, ResultGrid, StaleBanner, mono_font
)
from .halogroupbox import HaloGroupBox
from .haloimageview import HaloImageView
from .halolineedit import HaloLineEdit
from .halopromptbox import ExpandBar, HaloPromptBox
from .haloscrollbar import HaloScrollBar
from .imgbb import (
    ImgBBApiError, ImgBBClient, ImgBBError, ImgBBFileNotFoundError,
    ImgBBNetworkError, ImgBBUploadWorker, UploadResult
)
from .prompt_editor import PromptEditor, PromptHighlighter
from .referencethumb import (
    ClickableLabel, CloseButton, ReferenceThumb, ThumbOverlay
)
from .spinboxes import HaloDoubleSpinBox, HaloSpinBox
from .statusbar import StatusBar
from .tabs import HaloTabWidget

__version__ = "0.4.0"

__all__ = [
    "AnimatedToggle",
    "BusyHaloButton",
    "COMPACT_GROUP_SPACING",
    "COMPACT_HEIGHT",
    "COMPACT_PAD",
    "COMPACT_ROOM",
    "COMPACT_SPACING",
    "COMPACT_SPACING_X",
    "COMPACT_WRAP_WIDTH",
    "ClickableLabel",
    "CloseButton",
    "CompactButton",
    "CompactCheckBox",
    "CompactDoubleSpinBox",
    "CompactDropdown",
    "CompactGroupBox",
    "CompactIntField",
    "CompactLineEdit",
    "CompactNumberField",
    "CompactRadioButton",
    "CompactResultGrid",
    "CompactSpinBox",
    "DashBorderButton",
    "ExpandBar",
    "FiberHaloButton",
    "FrameButton",
    "FrameToggle",
    "GenerateButton",
    "GlowButton",
    "HaloButton",
    "HaloCheckBox",
    "HaloDoubleSpinBox",
    "HaloDropdown",
    "HaloGroupBox",
    "HaloImageView",
    "HaloLineEdit",
    "HaloPromptBox",
    "HaloRadioButton",
    "HaloScrollBar",
    "HaloSpinBox",
    "HaloTabWidget",
    "HeartCheckBox",
    "ImgBBApiError",
    "ImgBBClient",
    "ImgBBError",
    "ImgBBFileNotFoundError",
    "ImgBBNetworkError",
    "ImgBBUploadWorker",
    "IntField",
    "LineToggle",
    "MONO_FAMILY",
    "NumberField",
    "PromptEditor",
    "PromptHighlighter",
    "PulseHaloButton",
    "RaisedButton",
    "ReferenceThumb",
    "ResultGrid",
    "ShineButton",
    "SpreadButton",
    "StaleBanner",
    "StatusBar",
    "StatusBarButton",
    "ThumbOverlay",
    "UploadResult",
    "WideResultGrid",
    "__version__",
    "compact_combo",
    "flash_taskbar",
    "mono_font",
    "stop_flashing",
]
