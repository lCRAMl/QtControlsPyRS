# haloslider.py
#
# Ein selbst gezeichneter Schieberegler im Halo-Stil: eine vertiefte Schiene,
# darin ein glühendes Band vom Anfang bis zum Griff, und am Ende des Bandes
# ein Ring, der unter der Maus und beim Ziehen heller wird.
#
# Gezeichnet wird wie bei der Bildlaufleiste in Schichten übereinander
# (Schein, Saum, Hitze, Kern), jede schmaler und kräftiger als die davor. Qt
# kennt beim Zeichnen keinen Weichzeichner; das Glühen entsteht dadurch, dass
# die Schichten addiert werden (CompositionMode_Plus).
#
# Gerechnet wird nur, solange etwas passiert. Steht der Griff still und ist
# die Maus fort, läuft die Helligkeit aus, dann hält der Bildtakt an und
# kostet nichts mehr.
#
# Senkrecht und waagerecht: gerechnet wird in „längs" und „quer" statt in x
# und y. _point() und _bar() setzen das je nach Laufrichtung um. Damit bleibt
# der Griff in beiden Lagen ein Kreis - eine gedrehte Leinwand wie bei der
# Bildlaufleiste würde ihn zur Ellipse ziehen, sobald die Leiste nicht quadratisch ist.
#
# Nach außen bleibt es eine QSlider. Auch der Klick neben den Griff tut, was
# Qt tut: eine Seite weiterspringen, nicht an die Zeigerstelle hüpfen. Wer das
# andere will, schaltet es mit set_jump_to_click(True) ein.

from __future__ import annotations

import math
import time

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QSlider, QWidget

from ..buttons.hoverbuttons import _faded


class HaloSlider(QSlider):
    """Schieberegler als glühendes Band mit einem Ring als Griff.

    Nach außen eine ganz normale `QSlider`: `value()`, `setValue()`,
    `setRange()`, `valueChanged`, Tastatur und Mausrad verhalten sich
    unverändert, und `setOrientation()` dreht die Leiste:

        regler = HaloSlider(Qt.Orientation.Horizontal)
        regler.setRange(0, 100)
        regler.valueChanged.connect(zeige)

    Unter der Maus und beim Ziehen wird das Band heller; danach klingt es in
    etwa einer halben Sekunde ab, und der Bildtakt bleibt stehen, bis das
    Nächste passiert.
    """

    # --- Maße ---
    THICKNESS = 26      # Dicke der Leiste quer zur Laufrichtung
    TRACK_W   = 6.0     # Breite der Schiene; sie liegt mittig
    PADDING   = 13      # Rand an beiden Enden - der Griff braucht Platz
    HANDLE_R  = 7.0     # Radius des Griffs in Ruhe
    HANDLE_UP = 1.6     # so viel wächst er bei voller Helligkeit
    GRAB      = 6.0     # so weit daneben zählt ein Klick noch als Treffer

    # --- Schiene ---
    TRACK_FILL = 0.05   # Deckkraft der Fläche
    TRACK_LINE = 0.18   # Deckkraft des Randes

    # --- Band: (Breite, Deckkraft in Ruhe, Zuschlag bei voller Helligkeit) ---
    LAYERS = (
        (7.0, 0.03, 0.07),     # Schein
        (4.6, 0.07, 0.14),     # Saum
        (2.8, 0.20, 0.24),     # Hitze
        (1.1, 0.70, 0.25),     # Kern
    )

    # --- Griff: (Radius-Zuschlag, Deckkraft in Ruhe, Zuschlag) ---
    HANDLE_LAYERS = (
        (5.0, 0.05, 0.10),
        (2.5, 0.14, 0.20),
        (0.0, 0.55, 0.35),
    )

    # --- Bewegung ---
    HOVER_GLOW = 0.45   # Helligkeit, solange die Maus darauf steht
    DRAG_GLOW  = 1.0    # Helligkeit beim Ziehen
    DECAY      = 8.0    # so schnell läuft die Helligkeit aus (je Sekunde)
    FRAME_MS   = 16     # Bildtakt, solange etwas passiert

    def __init__(
        self,
        orientation: Qt.Orientation = Qt.Orientation.Horizontal,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(orientation, parent)

        self._glow = 0.0          # 0 = ruhig, 1 = volles Leuchten
        self._last_frame = 0.0
        self._dragging = False
        self._hovering = False
        self._jump_to_click = False

        self.setMouseTracking(True)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_frame)

    # ==============================
    # Verhalten
    # ==============================

    def jump_to_click(self) -> bool:
        return self._jump_to_click

    def set_jump_to_click(self, enabled: bool) -> None:
        """Ob ein Klick neben den Griff dorthin springt.

        Aus, weil QSlider es anders macht: dort springt ein Klick um eine
        Seite weiter. Die Sammlung hält sich an ihre Vorbilder, solange nichts
        dagegen spricht - wer das Springen will, schaltet es hier ein.
        """
        self._jump_to_click = bool(enabled)

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
        """Mitte quer zur Laufrichtung - dort liegt die Schiene."""
        return self._thickness() / 2.0

    def sizeHint(self) -> QSize:
        if self.is_vertical():
            return QSize(self.THICKNESS, 140)
        return QSize(140, self.THICKNESS)

    def minimumSizeHint(self) -> QSize:
        short = 2 * self.PADDING + 2 * round(self.HANDLE_R)
        if self.is_vertical():
            return QSize(self.THICKNESS, short)
        return QSize(short, self.THICKNESS)

    # ==============================
    # Längs und quer
    # ==============================

    def _point(self, along: float, across: float) -> QPointF:
        if self.is_vertical():
            return QPointF(across, along)
        return QPointF(along, across)

    def _bar(self, from_along: float, to_along: float, width: float) -> QRectF:
        """Ein Band zwischen zwei Stellen der Laufrichtung."""
        low, high = min(from_along, to_along), max(from_along, to_along)
        half = width / 2.0
        middle = self._center()
        if self.is_vertical():
            return QRectF(middle - half, low, width, high - low)
        return QRectF(low, middle - half, high - low, width)

    def _flipped(self) -> bool:
        """Ob das Minimum am hinteren Ende der Laufrichtung liegt.

        Senkrecht sitzt es bei Qt unten, also bei grossem y - und y waechst
        nach unten. Waagerecht sitzt es links, also bei kleinem x.
        setInvertedAppearance() dreht beides um.
        """
        return self.is_vertical() != self.invertedAppearance()

    def _track_span(self) -> tuple[float, float]:
        """Anfang und Länge der Schiene, in Laufrichtung gemessen."""
        return float(self.PADDING), max(0.0, self._length() - 2.0 * self.PADDING)

    def _progress(self) -> float:
        """Wo der Griff steht: 0 am Anfang der Laufrichtung, 1 am Ende."""
        span = self.maximum() - self.minimum()
        if span <= 0:
            return 0.0
        ratio = (self.value() - self.minimum()) / float(span)
        return 1.0 - ratio if self._flipped() else ratio

    def _handle_along(self) -> float:
        start, length = self._track_span()
        return start + self._progress() * length

    def _value_at(self, along: float) -> int:
        """Der Wert, der zu einer Stelle der Laufrichtung gehört.

        Das Ergebnis darf ausserhalb der Spanne liegen; `setValue()` schneidet
        es ab. Eine eigene Begrenzung stand hier und ist wieder weggefallen:
        eine Gegenprobe mit entfernter Begrenzung blieb gruen, weil Qt dasselbe
        ohnehin tut. Was nichts bewacht, soll auch nicht so aussehen.

        Die Abfrage auf eine Schiene ohne Länge bleibt - die traegt wirklich,
        sonst teilte die naechste Zeile durch null.
        """
        start, length = self._track_span()
        if length <= 0.0:
            return self.minimum()
        ratio = (along - start) / length
        if self._flipped():
            ratio = 1.0 - ratio
        span = self.maximum() - self.minimum()
        return self.minimum() + int(round(ratio * span))

    # ==============================
    # Bewegung
    # ==============================

    def glow(self) -> float:
        """0 = ruhig, 1 = volles Leuchten. Steuert Helligkeit und Griffgröße."""
        return self._glow

    def _target_glow(self) -> float:
        if self._dragging:
            return self.DRAG_GLOW
        if self._hovering:
            return self.HOVER_GLOW
        return 0.0

    def _wake(self) -> None:
        """Bildtakt laufen lassen, bis wieder Ruhe ist."""
        if self._timer.isActive():
            return
        self._last_frame = time.perf_counter()
        self._timer.start(self.FRAME_MS)

    def _on_frame(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_frame, 0.05)
        self._last_frame = now

        ziel = self._target_glow()
        if self._glow < ziel:
            # Hinauf geht es sofort - ein Griff, der erst eine halbe Sekunde
            # nach dem Anfassen hell wird, fühlt sich träge an.
            self._glow = ziel
        else:
            self._glow = ziel + (self._glow - ziel) * math.exp(-self.DECAY * dt)

        self.update()
        if self._is_calm():
            self._timer.stop()

    def _is_calm(self) -> bool:
        """Gibt es noch etwas zu rechnen?

        Massgeblich ist der ABSTAND zum Ziel, nicht die Helligkeit selbst und
        auch nicht, ob die Maus darauf steht. Mit "solange die Maus darauf
        steht" laeuft der Bildtakt endlos weiter, sobald der Zeiger irgendwo
        auf dem Regler liegenbleibt - und dabei aendert sich kein einziger
        Bildpunkt mehr. Dasselbe beim Ziehen: den Griff zeichnet ohnehin
        setValue() neu, der Takt wird nur fuer das Auf- und Abklingen
        gebraucht.
        """
        return abs(self._glow - self._target_glow()) <= 0.01

    # ==============================
    # Maus
    # ==============================

    def _pointer_along(self, event) -> float:
        position = event.position()
        return position.y() if self.is_vertical() else position.x()

    def _hits_handle(self, along: float) -> bool:
        return abs(along - self._handle_along()) <= self.HANDLE_R + self.GRAB

    def enterEvent(self, event) -> None:
        self._hovering = True
        self._wake()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovering = False
        self._wake()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        along = self._pointer_along(event)
        if self._hits_handle(along) or self._jump_to_click:
            self._dragging = True
            self.setSliderDown(True)
            if self._jump_to_click and not self._hits_handle(along):
                self.setValue(self._value_at(along))
            self._wake()
            event.accept()
            return

        # Daneben geklickt: eine Seite weiter, genau wie QSlider.
        vorwaerts = along > self._handle_along()
        if self._flipped():
            vorwaerts = not vorwaerts
        self.triggerAction(
            QSlider.SliderAction.SliderPageStepAdd if vorwaerts
            else QSlider.SliderAction.SliderPageStepSub
        )
        self._wake()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            self.setValue(self._value_at(self._pointer_along(event)))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._dragging and event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.setSliderDown(False)
            self._wake()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        super().wheelEvent(event)
        self._wake()

    def keyPressEvent(self, event) -> None:
        super().keyPressEvent(event)
        self._wake()

    # ==============================
    # Zeichnen
    # ==============================

    def _accent(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.Highlight)

    def _ink(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.WindowText)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # Kein Ausstieg bei einer Leiste ohne Laenge: _track_span() liefert
        # dann 0, und ein Band der Laenge null zeichnet sich ohne Schaden.
        # Eine Abfrage stand hier und ist weggefallen, weil eine Gegenprobe
        # ohne sie gruen blieb.
        start, length = self._track_span()
        self._paint_track(painter, start, start + length)
        self._paint_band(painter, start, length)
        self._paint_handle(painter)
        painter.end()

    def _paint_track(self, painter: QPainter, from_along: float, to_along: float) -> None:
        schiene = self._bar(from_along, to_along, self.TRACK_W)
        radius = self.TRACK_W / 2.0
        ink = self._ink()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(_faded(ink, self.TRACK_FILL))
        painter.drawRoundedRect(schiene, radius, radius)

        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(_faded(ink, self.TRACK_LINE), 1.0))
        painter.drawRoundedRect(schiene, radius, radius)

    def _paint_band(self, painter: QPainter, start: float, length: float) -> None:
        """Das Band vom Minimum bis zum Griff."""
        ende = start + length if self._flipped() else start
        griff = self._handle_along()
        if abs(griff - ende) < 0.5:
            return

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.setPen(Qt.PenStyle.NoPen)
        accent = self._accent()
        for breite, ruhe, zuschlag in self.LAYERS:
            painter.setBrush(_faded(accent, ruhe + zuschlag * self._glow))
            band = self._bar(ende, griff, breite)
            radius = breite / 2.0
            painter.drawRoundedRect(band, radius, radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

    def _paint_handle(self, painter: QPainter) -> None:
        mitte = self._point(self._handle_along(), self._center())
        grund = self.HANDLE_R + self.HANDLE_UP * self._glow

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        painter.setPen(Qt.PenStyle.NoPen)
        accent = self._accent()
        for zuschlag, ruhe, mehr in self.HANDLE_LAYERS:
            painter.setBrush(_faded(accent, ruhe + mehr * self._glow))
            radius = grund + zuschlag
            painter.drawEllipse(mitte, radius, radius)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
