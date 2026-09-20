"""qt_controls_pyrs – Bedienelemente für PyQt6-Anwendungen.

Eigenständige Widgets und Helfer, die sich wie ihre Qt-Vorbilder verhalten:

* :class:`GlowButton` – Knopf, der während einer laufenden Aufgabe die
  Beschriftung überblendet und den Rahmen in wandernden Regenbogenfarben
  leuchten lässt.
* :class:`FrameButton` – Knopf, der unter der Maus seinen Schleier abgibt und
  einen feinen Rahmen von außen hereinfahren lässt.
* :class:`AnimatedToggle` – Schiebeschalter als Ersatz für ``QCheckBox``.
* :class:`HeartCheckBox` – Herz zum Anhaken, das sich mit einem Hüpfer
  füllt und Funken wegstieben lässt.
* :class:`StatusBar` – Statuszeile, die lange Meldungen kurz aufklappt, ohne
  die Fensteraufteilung zu verändern.
* :class:`ReferenceThumb` – Bild-Miniatur zum Anklicken, die die gewählte Datei
  zu ImgBB hochlädt und den Fortschritt anzeigt.
* :class:`PromptEditor` – Eingabefeld, das Abschnittsüberschriften hervorhebt.
* :func:`flash_taskbar` – lässt den Taskleisten-Eintrag blinken (Windows).
"""

from .buttons import FrameButton, GenerateButton, GlowButton
from .checkboxes import AnimatedToggle, HeartCheckBox
from .flashtaskbar import flash_taskbar, stop_flashing
from .imgbb import (
    ImgBBApiError, ImgBBClient, ImgBBError, ImgBBFileNotFoundError,
    ImgBBNetworkError, ImgBBUploadWorker, UploadResult
)
from .prompt_editor import PromptEditor, PromptHighlighter
from .referencethumb import ClickableLabel, CloseButton, ReferenceThumb
from .statusbar import StatusBar

__version__ = "0.2.0"

__all__ = [
    "AnimatedToggle",
    "ClickableLabel",
    "CloseButton",
    "FrameButton",
    "GenerateButton",
    "GlowButton",
    "HeartCheckBox",
    "ImgBBApiError",
    "ImgBBClient",
    "ImgBBError",
    "ImgBBFileNotFoundError",
    "ImgBBNetworkError",
    "ImgBBUploadWorker",
    "PromptEditor",
    "PromptHighlighter",
    "ReferenceThumb",
    "StatusBar",
    "UploadResult",
    "__version__",
    "flash_taskbar",
    "stop_flashing",
]
