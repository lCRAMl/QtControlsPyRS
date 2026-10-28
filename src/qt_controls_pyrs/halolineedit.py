# halolineedit.py
#
# Einzeilige Eingabe im Stil der Halo-Knöpfe: feiner Rahmen, innen leer, unter
# der Maus glimmt es auf und der Rahmen wird weiß.
#
# Anders als beim HaloDropdown steht hier nicht nur Text, sondern ein Text, der
# bearbeitet wird. Deshalb malt dieses Feld die Schrift NICHT selbst: Cursor,
# Auswahl, Rollen bei langem Inhalt und die Eingabe fremder Schriftsysteme
# macht QLineEdit seit Jahren richtig, und wer das nachbaut, baut es schlechter
# nach. Gezeichnet wird nur der Rahmen darunter — der Text kommt von Qt
# obendrauf.
#
# Zwei Wege führen zum hellen Rahmen: die Maus und die Schreibmarke. Ein Feld,
# in das gerade getippt wird, soll hell bleiben, auch wenn die Maus längst
# woanders ist.

from __future__ import annotations

import math

from PyQt6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty
from PyQt6.QtGui import QColor, QFontMetricsF, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QLineEdit

from .buttons.hoverbuttons import _crisp, _faded, _glow, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class HaloLineEdit(QLineEdit):
    """Eingabefeld statt ``QLineEdit``, im Stil der Halo-Knöpfe.

    Nach außen bleibt es ein ``QLineEdit``: ``text()``, ``setText()``,
    ``setPlaceholderText()``, ``setValidator()``, ``textChanged`` und alles
    Übrige verhalten sich unverändert.

    Die Ränder der Schrift setzt das Feld selbst, damit die Buchstaben nicht am
    Rahmen kleben. Wer sie anders haben will, ruft ``setTextMargins()`` nach dem
    Erzeugen — die eigene Vorgabe wird dann nicht noch einmal überschrieben.
    """

    HEIGHT        = 45        # Höhe der Fläche, wie beim HaloDropdown
    ROOM          = 16        # Rand links und rechts — bündig mit den Knöpfen
    ROOM_Y        = 4         # Rand oben und unten
    PAD           = 16        # Abstand der Schrift zum Rahmen
    RADIUS        = 0         # Eckenradius
    OUTLINE_ALPHA = 0.5       # Deckkraft des Rahmens in Ruhe
    INNER_GLOW    = 20        # innerer Schein unter der Maus
    HOVER_MS      = 1250      # wie die Halo-Knöpfe: schnell hin, lang aus
    FOCUS_MS      = 220       # die Schreibmarke kommt schneller als die Maus
    MIN_CHARS     = 8         # so viel Platz hält das Feld mindestens frei

    def __init__(self, *args, **kwargs) -> None:
        self._hover = 0.0
        self._focus = 0.0
        super().__init__(*args, **kwargs)

        self.setFrame(False)      # der Rahmen kommt aus paintEvent, nicht aus dem Stil
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # Qt füllt die Fläche eines Eingabefelds mit der Palettenfarbe `Base`
        # — und zwar in super().paintEvent(), also NACH dem Rahmen. Der Rahmen
        # verschwände darunter, und innen stünde ein graues Rechteck statt der
        # leeren Halo-Leiste. Die Füllung wird deshalb durchsichtig gesetzt.
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(Qt.GlobalColor.transparent))
        self.setPalette(palette)
        self.setAutoFillBackground(False)
        self.setTextMargins(self.ROOM + self.PAD, 0, self.ROOM + self.PAD, 0)

        self._hover_anim = self._animation(b"hover", self.HOVER_MS, QEasingCurve.Type.OutExpo)
        self._focus_anim = self._animation(b"focus", self.FOCUS_MS, QEasingCurve.Type.OutCubic)

    def _animation(self, name: bytes, duration: int, curve) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(duration)
        anim.setEasingCurve(curve)
        return anim

    @staticmethod
    def _run(anim: QPropertyAnimation, current: float, target: float) -> None:
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    # ==============================
    # Animierte Eigenschaften
    # ==============================

    @pyqtProperty(float)
    def hover(self) -> float:
        return self._hover

    @hover.setter
    def hover(self, value: float) -> None:
        self._hover = value
        self.update()

    @pyqtProperty(float)
    def focus(self) -> float:
        return self._focus

    @focus.setter
    def focus(self, value: float) -> None:
        self._focus = value
        self.update()

    def _level(self) -> float:
        """Wie hell der Rahmen steht — Maus und Schreibmarke, je nachdem was mehr ist."""
        return max(_clamp(self._hover), _clamp(self._focus))

    # ==============================
    # Maus und Schreibmarke
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._run(self._hover_anim, self._hover, 0.0)

    def focusInEvent(self, event) -> None:
        super().focusInEvent(event)
        self._run(self._focus_anim, self._focus, 1.0)

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self._run(self._focus_anim, self._focus, 0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Ein gesperrtes Feld bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._run(self._hover_anim, self._hover, 0.0)
            self._run(self._focus_anim, self._focus, 0.0)

    # ==============================
    # Größe
    # ==============================

    def _surface(self) -> QRectF:
        room_x = min(float(self.ROOM), self.width() / 4.0)
        room_y = min(float(self.ROOM_Y), self.height() / 4.0)
        return QRectF(self.rect()).adjusted(room_x, room_y, -room_x, -room_y)

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        chars = max(len(self.text()), len(self.placeholderText()), self.MIN_CHARS)
        width = metrics.averageCharWidth() * chars + 2 * self.PAD + 2 * self.ROOM
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    def minimumSizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        width = metrics.averageCharWidth() * self.MIN_CHARS + 2 * self.PAD + 2 * self.ROOM
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        # Auch im gesperrten Zustand lesbar bleiben — abgeblasst wird global.
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _paint_surface(self, painter: QPainter, rect: QRectF, level: float) -> None:
        """Der Halo-Rahmen: innen glimmen, außen ein feiner Strich.

        Dieselben zwei Schritte wie beim HaloDropdown, damit Eingabefeld und
        Auswahlfeld nebeneinander gleich aussehen.
        """
        ink = self._ink()
        radius = float(self.RADIUS)

        if level > 0.0:
            _glow(painter, rect, _faded(ink, 0.5 * level), self.INNER_GLOW,
                  inside=True, radius=radius)

        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * level
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(rect, 1.0), max(radius - 0.5, 0.0))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)
        self._paint_surface(painter, self._surface(), self._level())
        painter.end()

        # Und darüber der Text, von Qt gezeichnet: Schreibmarke, Auswahl,
        # Rollen bei langem Inhalt. Der Aufruf steht BEWUSST am Ende - sonst
        # läge der Rahmen über den Buchstaben.
        super().paintEvent(event)
