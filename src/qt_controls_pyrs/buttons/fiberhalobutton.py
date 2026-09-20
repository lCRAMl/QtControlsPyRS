# fiberhalobutton.py
#
# `HaloButton` mit Arbeitsanzeige: solange die Aufgabe läuft, füllt eine
# Animation die ganze Fläche des Knopfes — dahinter ziehen weiche Flächen in
# Nuancen der Grundfarbe durch, darüber schwingen dünne Glasfasern.

from __future__ import annotations

import math

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize,
    Qt, pyqtProperty
)
from PyQt6.QtGui import (
    QBrush, QColor, QFontMetricsF, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient
)

from .hoverbuttons import HaloButton, _faded, _mix


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class FiberHaloButton(HaloButton):
    """Wie der `HaloButton`, zeigt aber an, dass gerade etwas läuft.

    Unter der Maus verhält er sich unverändert: der Strich wandert nach außen
    und verblasst, innen wie außen kommt ein Schein auf.

    Nach dem Klick — oder nach `start_busy()` — füllt sich die ganze Fläche.
    Zuunterst liegt ein tiefer Ton der Grundfarbe, darüber ziehen weiche
    Flächen in verschiedenen Nuancen davon langsam durch den Knopf, dazwischen
    blitzen ein paar helle Lichter auf. Darüber schwingen dünne Glasfasern von
    Rand zu Rand, und in jeder wandert ein Lichtpaket entlang. Alles läuft
    absichtlich langsam: ein voller Durchlauf dauert `CYCLE_MS`, und die
    einzelnen Bewegungen sind gegeneinander verschoben, sodass sich das Bild
    nie sichtbar wiederholt. `stop_busy()` blendet alles wieder aus.

    Die Grundfarbe der Animation ist die einzige Farbe, die nicht aus der
    Palette kommt — sie soll auffallen. Alle Nuancen leiten sich von ihr ab,
    ein Wechsel über `ACCENT` oder `setAccentColor()` färbt also das ganze
    Bild um.
    """

    ACCENT     = "#5a8cff"   # Grundfarbe der Animation
    FIBERS     = 5           # Anzahl der Fasern
    SWING      = 0.34        # größte Auslenkung, Anteil der Höhe
    CYCLE_MS   = 9000        # Dauer eines vollen Durchlaufs
    FADE_MS    = 450         # Ein- und Ausblenden der Anzeige
    PACKET     = 0.16        # Länge des Lichtpakets, Anteil der Breite
    AUTO_BUSY  = True        # Ein Klick startet die Anzeige von allein

    # Der Grund, auf dem alles liegt: ein tiefer, satter Ton der Grundfarbe.
    GROUND = (-0.02, 0.95, 0.30)   # Farbton-Versatz, Sättigung, Helligkeit

    # Die Flächen, die durch den Knopf ziehen. Je Fläche:
    # Farbton-Versatz, Sättigung, Helligkeit, Deckkraft, Breite und Höhe
    # (Vielfaches der Knopfhöhe), Lage der Mitte, Tempo.
    CLOUDS = (
        (-0.06, 0.90, 0.75, 0.55, 3.0, 1.9, 0.35, 0.34),
        (0.04, 0.75, 0.95, 0.45, 2.2, 1.5, 0.70, -0.46),
        (0.09, 0.85, 0.70, 0.50, 2.6, 1.7, 0.55, 0.62),
        (-0.03, 0.60, 1.00, 0.35, 1.7, 1.2, 0.25, -0.78),
    )

    # Die hellen Lichter dazwischen: Tempo, Lage der Mitte, Größe, Deckkraft.
    SPARKS = (
        (0.90, 0.40, 0.55, 0.95),
        (-1.20, 0.68, 0.38, 0.80),
        (1.45, 0.52, 0.30, 0.70),
    )

    def __init__(self, text: str = "", busy_text: str = "", parent=None) -> None:
        self._phase = 0.0        # Position der Bewegung, 0..1, läuft um
        self._busy_fade = 0.0    # 0 = keine Anzeige, 1 = ganz da
        self._busy = False
        self._busy_text = busy_text
        self._accent = QColor(self.ACCENT)
        super().__init__(text, parent)

        self._cycle = QPropertyAnimation(self, b"phase", self)
        self._cycle.setStartValue(0.0)
        self._cycle.setEndValue(1.0)
        self._cycle.setDuration(self.CYCLE_MS)
        self._cycle.setEasingCurve(QEasingCurve.Type.Linear)
        self._cycle.setLoopCount(-1)

        self._fade = QPropertyAnimation(self, b"busy_fade", self)
        self._fade.setDuration(self.FADE_MS)
        self._fade.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._fade.finished.connect(self._on_fade_finished)

        if self.AUTO_BUSY:
            self.clicked.connect(self._on_clicked)

    # ==============================
    # Öffentliche API
    # ==============================

    def start_busy(self, label: str | None = None) -> None:
        """Blendet die Animation auf."""
        if label is not None:
            self.setBusyText(label)
        self._busy = True
        if self._cycle.state() != QAbstractAnimation.State.Running:
            self._cycle.start()
        self._animate_fade(1.0)

    def stop_busy(self) -> None:
        """Blendet die Animation wieder aus."""
        self._busy = False
        self._animate_fade(0.0)

    def is_busy(self) -> bool:
        return self._busy

    def busy_text(self) -> str:
        return self._busy_text

    def setBusyText(self, label: str) -> None:
        """Beschriftung, solange die Aufgabe läuft. Leer heißt: gleich bleiben."""
        self._busy_text = label
        self.updateGeometry()
        self.update()

    def accent_color(self) -> QColor:
        return QColor(self._accent)

    def setAccentColor(self, color) -> None:
        """Die Grundfarbe der Animation, nur für diesen Knopf."""
        self._accent = QColor(color)
        self.update()

    # ==============================
    # Animierte Eigenschaften
    # ==============================

    @pyqtProperty(float)
    def phase(self) -> float:
        return self._phase

    @phase.setter
    def phase(self, value: float) -> None:
        self._phase = value
        if self._busy_fade > 0.0:
            self.update()

    @pyqtProperty(float)
    def busy_fade(self) -> float:
        return self._busy_fade

    @busy_fade.setter
    def busy_fade(self, value: float) -> None:
        self._busy_fade = value
        self.update()

    def _animate_fade(self, target: float) -> None:
        self._fade.stop()
        self._fade.setStartValue(self._busy_fade)
        self._fade.setEndValue(target)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        # Die Bewegung erst anhalten, wenn nichts mehr davon zu sehen ist.
        if not self._busy and self._busy_fade <= 0.0:
            self._cycle.stop()
            self.update()

    def _on_clicked(self) -> None:
        if not self._busy:
            self.start_busy()

    # ==============================
    # Beschriftung
    # ==============================

    def _label_text(self) -> str:
        if self._busy and self._busy_text:
            return self._busy_text
        return self.text()

    def sizeHint(self) -> QSize:
        # Beide Beschriftungen müssen passen, sonst rutscht das Fenster, sobald
        # die Aufgabe losläuft.
        hint = super().sizeHint()
        if not self._busy_text:
            return hint
        text = self._busy_text.upper() if self.UPPERCASE else self._busy_text
        width = QFontMetricsF(self._label_font(1.0)).horizontalAdvance(text)
        needed = int(round(width)) + 2 * self.PAD + 2 * self.ROOM
        return QSize(max(hint.width(), needed), hint.height())

    # ==============================
    # Farbnuancen
    # ==============================

    def _nuance(
        self, shift: float, saturation: float, value: float, alpha: float = 1.0
    ) -> QColor:
        """Eine Abwandlung der Grundfarbe: verschobener Farbton, andere Tiefe."""
        hue, sat, val, _ = self._accent.getHsvF()
        if hue < 0:                      # grau hat keinen Farbton
            hue = 0.0
        return QColor.fromHsvF(
            (hue + shift) % 1.0,
            _clamp(sat * saturation),
            _clamp(val * value),
            _clamp(alpha),
        )

    # ==============================
    # Darstellung
    # ==============================

    def _drift(self, speed: float, rect: QRectF, width: float) -> float:
        """Waagrechte Lage einer Fläche, die immer wieder durchzieht."""
        travel = rect.width() + width
        return rect.left() - width / 2 + ((self._phase * speed) % 1.0) * travel

    def _paint_cloud(
        self, painter: QPainter, center: QPointF, width: float, height: float,
        color: QColor, focus: float = 0.45,
    ) -> None:
        """Eine weiche Fläche: in der Mitte satt, zum Rand hin nicht mehr da.

        `focus` sagt, wie eng der satte Kern ist — kleine Werte ergeben ein
        Licht mit scharfer Mitte, große eine flächige Wolke.
        """
        painter.save()
        painter.translate(center)
        # Aus dem runden Verlauf wird durch das Dehnen eine liegende Fläche.
        painter.scale(width / height, 1.0)

        gradient = QRadialGradient(QPointF(0, 0), height / 2)
        gradient.setColorAt(0.0, color)
        gradient.setColorAt(focus, _faded(color, color.alphaF() * 0.55))
        gradient.setColorAt(1.0, _faded(color, 0.0))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(QPointF(0, 0), height / 2, height / 2)
        painter.restore()

    def _paint_ground(self, painter: QPainter, rect: QRectF) -> None:
        """Der Grund und alles, was darüber hinwegzieht."""
        shift, saturation, value = self.GROUND
        painter.fillRect(rect, self._nuance(shift, saturation, value))

        unit = rect.height()
        for shift, saturation, value, alpha, wide, high, lane, speed in self.CLOUDS:
            width, height = wide * unit, high * unit
            # Die Flächen heben und senken sich langsam, während sie ziehen.
            bob = math.sin(2 * math.pi * (self._phase * speed * 1.3 + lane))
            center = QPointF(
                self._drift(speed, rect, width),
                rect.top() + unit * lane + bob * unit * 0.18,
            )
            self._paint_cloud(
                painter, center, width, height,
                self._nuance(shift, saturation, value, alpha),
            )

        for speed, lane, size, alpha in self.SPARKS:
            # Die Lichter atmen, damit sie aufblitzen statt gleichmäßig zu ziehen.
            breath = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(
                2 * math.pi * (self._phase * speed * 0.8 + lane)
            ))
            width = height = size * unit
            center = QPointF(
                self._drift(speed, rect, width),
                rect.top() + unit * lane,
            )
            self._paint_cloud(
                painter, center, width * 1.6, height,
                self._nuance(0.0, 0.14, 1.45, alpha * breath), focus=0.20,
            )

    def _light_pen(
        self, rect: QRectF, base: QColor, position: float, width: float
    ) -> QPen:
        """Faserfarbe mit einem hellen Paket, das an `position` (0..1) sitzt."""
        gradient = QLinearGradient(rect.left(), 0.0, rect.right(), 0.0)
        gradient.setColorAt(0.0, base)
        gradient.setColorAt(1.0, base)

        bright = self._nuance(0.0, 0.10, 1.45, 0.95)
        half = self.PACKET / 2
        for at, color in ((position - half, base), (position, bright), (position + half, base)):
            if 0.0 < at < 1.0:
                gradient.setColorAt(at, color)

        pen = QPen(QBrush(gradient), width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _fiber_path(self, rect: QRectF, index: int) -> tuple[QPainterPath, float]:
        """Eine schwingende Faser und die Stelle, an der ihr Licht gerade steht."""
        span = max(self.FIBERS - 1, 1)
        share = index / span                      # 0 = innen, 1 = außen
        amplitude = rect.height() * self.SWING * (0.25 + 0.75 * share)
        waves = 0.9 + 0.45 * index                # Wellen über die Länge
        drift = (0.55 + 0.18 * index) * (1 if index % 2 == 0 else -1)
        offset = index / self.FIBERS

        # Die Auslenkung atmet langsam, damit die Bewegung nie gleichförmig wirkt.
        breath = 0.72 + 0.28 * math.sin(2 * math.pi * (self._phase * 0.5 + share))

        path = QPainterPath()
        steps = 64
        for step in range(steps + 1):
            along = step / steps
            # An den Rändern läuft die Faser aus, dort schwingt sie nicht.
            anchored = math.sin(math.pi * along) ** 0.6
            wave = math.sin(2 * math.pi * (waves * along + self._phase * drift + offset))
            point = QPointF(
                rect.left() + along * rect.width(),
                rect.center().y() + amplitude * breath * anchored * wave,
            )
            if step == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)

        return path, (self._phase * drift + offset) % 1.0

    def _paint_fibers(self, painter: QPainter, rect: QRectF, ink: QColor) -> None:
        span = max(self.FIBERS - 1, 1)
        for index in range(self.FIBERS):
            path, position = self._fiber_path(rect, index)
            # Innen hell wie die Schrift, nach außen in der Grundfarbe.
            color = _mix(
                _faded(ink, 0.55), self._nuance(0.02, 0.55, 1.30, 0.85),
                0.15 + 0.85 * (index / span),
            )
            # Erst das weiche Leuchten, dann der Kern mit dem Lichtpaket.
            painter.setPen(QPen(_faded(color, color.alphaF() * 0.30), 3.4))
            painter.drawPath(path)
            painter.setPen(self._light_pen(rect, color, position, 1.3))
            painter.drawPath(path)

    def _paint_busy(self, painter: QPainter, rect: QRectF, ink: QColor) -> None:
        if rect.width() < 12 or rect.height() < 6:
            return

        painter.save()
        # Die Anzeige bleibt kräftig, auch wenn der Knopf während der Aufgabe
        # gesperrt ist — sonst wäre gerade das nicht zu sehen, worauf man wartet.
        painter.setOpacity(_clamp(self._busy_fade))
        painter.setClipRect(rect)

        self._paint_ground(painter, rect)
        self._paint_fibers(painter, rect, ink)

        painter.restore()

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        # Erst die Animation, dann der Halo — sein Strich und sein Schein
        # sollen darüber liegen, nicht darunter verschwinden.
        if self._busy_fade > 0.0:
            self._paint_busy(painter, rect, self._ink(hover))
        super()._paint_surface(painter, rect, hover)
