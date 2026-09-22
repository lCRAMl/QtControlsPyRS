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
* :class:`AnimatedToggle` – Schiebeschalter als Ersatz für ``QCheckBox``.
* :class:`FrameToggle`, :class:`LineToggle`, :class:`HaloCheckBox` – Schalter im
  Halo-Stil: ein Rahmen mit gleitender Kugel, ein Strich mit laufender Kugel
  und ein Kästchen, aus dem beim Anhaken ein Strich nach außen läuft.
* :class:`HeartCheckBox` – Herz zum Anhaken, das sich mit einem Hüpfer
  füllt und Funken wegstieben lässt.
* :class:`StatusBar` – Statuszeile, die lange Meldungen kurz aufklappt, ohne
  die Fensteraufteilung zu verändern.
* :class:`ReferenceThumb` – Bild-Miniatur als Karte, deren Rahmen dem Zeiger
  nachleuchtet; lädt die gewählte Datei zu ImgBB hoch und zeigt den Fortschritt.
* :class:`PromptEditor` – Eingabefeld, das Abschnittsüberschriften hervorhebt.
* :func:`flash_taskbar` – lässt den Taskleisten-Eintrag blinken (Windows).
"""

from .buttons import (
    BusyHaloButton, DashBorderButton, FiberHaloButton, FrameButton,
    GenerateButton, GlowButton, HaloButton, PulseHaloButton, RaisedButton,
    ShineButton, SpreadButton
)
from .checkboxes import (
    AnimatedToggle, FrameToggle, HaloCheckBox, HeartCheckBox, LineToggle
)
from .dropdowns import HaloDropdown
from .flashtaskbar import flash_taskbar, stop_flashing
from .imgbb import (
    ImgBBApiError, ImgBBClient, ImgBBError, ImgBBFileNotFoundError,
    ImgBBNetworkError, ImgBBUploadWorker, UploadResult
)
from .prompt_editor import PromptEditor, PromptHighlighter
from .referencethumb import (
    ClickableLabel, CloseButton, ReferenceThumb, ThumbOverlay
)
from .statusbar import StatusBar

__version__ = "0.2.0"

__all__ = [
    "AnimatedToggle",
    "BusyHaloButton",
    "ClickableLabel",
    "CloseButton",
    "DashBorderButton",
    "FiberHaloButton",
    "FrameButton",
    "FrameToggle",
    "GenerateButton",
    "GlowButton",
    "HaloButton",
    "HaloCheckBox",
    "HaloDropdown",
    "HeartCheckBox",
    "ImgBBApiError",
    "ImgBBClient",
    "ImgBBError",
    "ImgBBFileNotFoundError",
    "ImgBBNetworkError",
    "ImgBBUploadWorker",
    "LineToggle",
    "PromptEditor",
    "PromptHighlighter",
    "PulseHaloButton",
    "RaisedButton",
    "ReferenceThumb",
    "ShineButton",
    "SpreadButton",
    "StatusBar",
    "ThumbOverlay",
    "UploadResult",
    "__version__",
    "flash_taskbar",
    "stop_flashing",
]
