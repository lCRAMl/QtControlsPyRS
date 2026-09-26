# haloscrollbar.py
#
# Eine selbst gezeichnete Bildlaufleiste nach einem Vorbild von CodePen
# (designfenix): eine vertiefte Schiene, darin ein glühendes Band, das sich
# beim Scrollen wellt und heller wird. Danach beruhigt es sich wieder.
#
# Gezeichnet wird in vier Schichten übereinander (Schein, Saum, Hitze, Kern),
# jede etwas schmaler und kräftiger als die davor. Qt kennt keinen
# Weichzeichner beim Zeichnen; das Glühen entsteht dadurch, dass die Schichten
# addiert werden (CompositionMode_Plus).
#
# Gerechnet wird nur, solange etwas passiert: Nach dem Scrollen läuft die
# Bewegung aus, dann steht der Bildtakt still und kostet nichts mehr.
#
# Senkrecht und waagerecht: gezeichnet wird immer senkrecht gedacht. Für eine
# waagerechte Leiste dreht der Maler zu Beginn um 90 Grad, der Rest bleibt
# gleich. „Länge" heißt deshalb überall die Strecke in Laufrichtung und
# „Dicke" die quer dazu.

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QScrollBar, QWidget

from .buttons.hoverbuttons import _faded


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class HaloScrollBar(QScrollBar):
    """Bildlaufleiste als glühendes Band in einer vertieften Schiene.

    Nach außen eine ganz normale `QScrollBar`: `value()`, `setValue()`,
    `maximum()`, `valueChanged` und das Mausrad funktionieren unverändert. Sie
    lässt sich überall einsetzen, wo Qt eine Bildlaufleiste annimmt:

        text_edit.setVerticalScrollBar(HaloScrollBar(text_edit))
        liste.setHorizontalScrollBar(HaloScrollBar(liste))

    Beim Scrollen wellt sich das Band und wird heller; nach etwa einer halben
    Sekunde ist es wieder ruhig, und der Bildtakt bleibt stehen, bis das
    Nächste passiert.
    """

    # --- Maße ---
    THICKNESS = 18      # Dicke der Leiste quer zur Laufrichtung
    TRACK_W   = 7.0     # Breite der Schiene; sie liegt mittig
    PADDING   = 12      # Rand an beiden Enden
    MIN_THUMB = 40      # so kurz wird das Band höchstens
    GRAB      = 8       # so weit daneben zählt ein Klick noch als Treffer

    # --- Schiene ---
    TRACK_FILL = 0.05   # Deckkraft der Fläche
    TRACK_LINE = 0.18   # Deckkraft des Randes

    # --- Band: (Breite, Deckkraft in Ruhe, Zuschlag bei voller Bewegung) ---
    # Die Breiten sind auf die schmale Leiste abgestimmt: im Vorbild ist der
    # Streifen viel breiter, dort dürfen die Schichten weiter ausladen.
    LAYERS = (
        (7.5, 0.03, 0.07),     # Schein
        (5.0, 0.07, 0.14),     # Saum
        (3.0, 0.20, 0.24),     # Hitze
        (1.1, 0.70, 0.25),     # Kern
    )
    TIP = 0.15          # so dünn läuft das Band an den Enden aus

    # --- Bewegung ---
    IDLE_WAVE   = 0.6   # Wellenhöhe, solange es noch nachschwingt
    ACTIVE_WAVE = 2.8   # Wellenhöhe bei vollem Scrollen
    DECAY       = 10.0  # so schnell läuft die Bewegung aus (je Sekunde)
    SENSITIVITY = 3.0   # eine Drittel-Seite Scrollen reicht für volle Bewegung
    FRAME_MS    = 16    # Bildtakt, solange etwas passiert

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(Qt.Orientation.Vertical, parent)

        self._activity = 0.0        # 0 = ruhig, 1 = volles Scrollen
        self._time = 0.0            # läuft für die Wellen mit
        self._last_frame = 0.0
        self._last_value = self.value()
        self._dragging = False
        self._drag_offset = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_frame)

        self.valueChanged.connect(self._on_value_changed)

    # ==============================
    # Größe und Laufrichtung
    # ==============================

    def is_vertical(self) -> bool:
        return self.orientation() == Qt.Orientation.Vertical

    def _length(self) -> float:
        """Die Strecke in Laufrichtung."""
        return float(self.height()) if self.is_vertical() else float(self.width())

    def _thickness(self) -> float:
        """Die Strecke quer dazu."""
        return float(self.width()) if self.is_vertical() else float(self.height())

    def _center(self) -> float:
        """Mitte quer zur Laufrichtung — dort liegt die Schiene."""
        return self._thickness() / 2.0

    def sizeHint(self) -> QSize:
        if self.is_vertical():
            return QSize(self.THICKNESS, 120)
        return QSize(120, self.THICKNESS)

    def minimumSizeHint(self) -> QSize:
        short = 2 * self.PADDING + self.MIN_THUMB
        if self.is_vertical():
            return QSize(self.THICKNESS, short)
        return QSize(short, self.THICKNESS)

    # ==============================
    # Bewegung
    # ==============================

    def activity(self) -> float:
        """0 = ruhig, 1 = volles Scrollen. Steuert Wellen und Helligkeit."""
        return self._activity

    def _on_value_changed(self, value: int) -> None:
        # Anhaltendes Scrollen hält die Bewegung oben; ein einzelner Sprung
        # klingt dagegen schnell wieder ab.
        step = abs(value - self._last_value) / max(1.0, float(self.pageStep()))
        self._last_value = value
        self._wake(self._activity + step * self.SENSITIVITY)

    def _wake(self, activity: float) -> None:
        """Bewegung anstoßen und den Bildtakt laufen lassen."""
        self._activity = _clamp(max(self._activity, activity))
        if self._timer.isActive():
            return
        self._last_frame = time.perf_counter()
        self._timer.start(self.FRAME_MS)

    def _on_frame(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_frame, 0.05)
        self._last_frame = now
        self._time += dt

        if not self._dragging:
            self._activity *= math.exp(-self.DECAY * dt)

        self.update()

        if self._is_calm():
            self._timer.stop()

    def _is_calm(self) -> bool:
        """Gibt es noch etwas zu rechnen?"""
        if self._dragging:
            return False
        return self._activity <= 0.01

    # ==============================
    # Lage des Bandes
    # ==============================

    def _track_span(self) -> tuple[float, float]:
        """Anfang und Länge der Schiene, in Laufrichtung gemessen."""
        return float(self.PADDING), max(0.0, self._length() - 2.0 * self.PADDING)

    def _thumb_span(self) -> tuple[float, float]:
        """Anfang und Länge des Bandes."""
        start, length = self._track_span()
        span = self.maximum() - self.minimum()
        visible = max(1, self.pageStep())

        ratio = visible / float(span + visible)
        thumb = min(max(float(self.MIN_THUMB), length * ratio), length)
        travel = max(0.0, length - thumb)
        progress = 0.0 if span <= 0 else (self.value() - self.minimum()) / float(span)
        return start + progress * travel, thumb

    # ==============================
    # Maus
    # ==============================

    def _pointer_along(self, event) -> float:
        """Wo der Zeiger in Laufrichtung steht."""
        position = event.position()
        return position.y() if self.is_vertical() else position.x()

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        along = self._pointer_along(event)
        start, length = self._thumb_span()

        if start - self.GRAB <= along <= start + length + self.GRAB:
            self._dragging = True
            self._drag_offset = along - start
            self._wake(1.0)
            return

        # Daneben geklickt: das Band springt mit seiner Mitte dorthin.
        self._drag_offset = length / 2.0
        self._scroll_to(along)
        self._wake(0.55)

    def mouseMoveEvent(self, event) -> None:
        if not self._dragging:
            return
        self._scroll_to(self._pointer_along(event))
        self._wake(1.0)

    def mouseReleaseEvent(self, event) -> None:
        self._dragging = False

    def _scroll_to(self, along: float) -> None:
        start, length = self._track_span()
        _, thumb = self._thumb_span()
        travel = max(1.0, length - thumb)

        progress = _clamp((along - self._drag_offset - start) / travel)
        span = self.maximum() - self.minimum()
        self.setValue(self.minimum() + round(progress * span))

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))

        if self.maximum() <= self.minimum():
            painter.end()      # nichts zu scrollen, nichts zu zeigen
            return

        if not self.is_vertical():
            # Ab hier wird senkrecht gedacht: die Laufrichtung zeigt nach
            # unten, quer dazu nach rechts.
            painter.translate(0.0, float(self.height()))
            painter.rotate(-90.0)

        self._draw_track(painter)
        self._draw_thumb(painter)
        painter.end()

    def _draw_track(self, painter: QPainter) -> None:
        """Die vertiefte Schiene, in der das Band läuft."""
        start, length = self._track_span()
        ink = self._ink()
        rect = QRectF(self._center() - self.TRACK_W / 2.0, start, self.TRACK_W, length)

        painter.setPen(QPen(_faded(ink, self.TRACK_LINE), 1.0))
        painter.setBrush(QBrush(_faded(ink, self.TRACK_FILL)))
        painter.drawRoundedRect(rect, self.TRACK_W / 2.0, self.TRACK_W / 2.0)

    def _draw_thumb(self, painter: QPainter) -> None:
        """Das Band: vier Schichten übereinander, addiert ergibt das ein Glühen."""
        start, length = self._thumb_span()
        end = start + length
        amplitude = self.IDLE_WAVE + self._activity * self.ACTIVE_WAVE
        ink = self._ink()

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)

        for width, idle_alpha, active_alpha in self.LAYERS:
            path = self._ribbon(start, end, width * (1.0 + 0.3 * self._activity), amplitude)
            painter.setBrush(QBrush(_faded(ink, idle_alpha + self._activity * active_alpha)))
            painter.drawPath(path)

        painter.restore()

    def _ribbon(self, start: float, end: float, width: float, amplitude: float) -> QPainterPath:
        """Ein Band: in der Mitte am breitesten, an den Enden dünn, leicht gewellt."""
        steps = max(30, int((end - start) / 3))
        center = self._center()
        left_edge: list[QPointF] = []
        right_edge: list[QPointF] = []

        for index in range(steps + 1):
            t = index / steps
            along = start + (end - start) * t
            taper = math.sin(t * math.pi) ** 0.52
            half = (self.TIP + (width - self.TIP) * taper) / 2.0
            across = center + self._wave(along, t, amplitude)
            left_edge.append(QPointF(across - half, along))
            right_edge.append(QPointF(across + half, along))

        path = QPainterPath(left_edge[0])
        for point in left_edge[1:]:
            path.lineTo(point)
        for point in reversed(right_edge):
            path.lineTo(point)
        path.closeSubpath()
        return path

    def _wave(self, along: float, t: float, amplitude: float) -> float:
        """Vier Sinuswellen übereinander — davon wirkt die Bewegung lebendig.

        Der Umschlag (`envelope`) hält die Enden ruhig, damit das Band nicht
        aus der Schiene rutscht.
        """
        envelope = math.sin(t * math.pi) ** 0.62
        first  = math.sin(along * 0.052 + self._time * 3.4) * 0.48
        second = math.sin(along * 0.021 - self._time * 2.3) * 0.30
        third  = math.sin(along * 0.112 + self._time * 5.4) * 0.17
        fourth = math.sin(along * 0.176 - self._time * 3.8) * 0.05
        return (first + second + third + fourth) * amplitude * envelope
