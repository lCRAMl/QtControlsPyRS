# fiberhalobutton.py
#
# `BusyHaloButton`, dessen Anzeige die ganze Fläche füllt: dahinter ziehen
# weiche Flächen in Nuancen der Grundfarbe durch, darüber schwingen dünne
# Glasfasern. Zustand, Takt und die überblendende Beschriftung kommen aus
# busyhalo.py.

from __future__ import annotations

import math

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QRadialGradient

from .busyhalo import BusyHaloButton, _clamp
from .hoverbuttons import _faded, _mix


class FiberHaloButton(BusyHaloButton):
    """Arbeitet auffällig: die ganze Fläche des Knopfes füllt sich.

    Unter der Maus verhält er sich wie der `HaloButton`. Nach dem Klick — oder
    nach `start_busy()` — liegt zuunterst ein tiefer Ton der Grundfarbe, darüber
    ziehen weiche Flächen in verschiedenen Nuancen davon langsam durch den
    Knopf, dazwischen blitzen ein paar helle Lichter auf. Darüber schwingen
    dünne Glasfasern von Rand zu Rand, und in jeder wandert ein Lichtpaket
    entlang. Weil alle Bewegungen gegeneinander verschoben sind, wiederholt sich
    das Bild nie sichtbar.

    Alle Nuancen leiten sich von der Grundfarbe ab, ein Wechsel über `ACCENT`
    oder `setAccentColor()` färbt also das ganze Bild um.
    """

    FIBERS   = 5        # Anzahl der Fasern
    SWING    = 0.34     # größte Auslenkung, Anteil der Höhe
    PACKET   = 0.16     # Länge des Lichtpakets, Anteil der Breite
    CYCLE_MS = 9000     # Dauer eines vollen Durchlaufs

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
    # Die ziehenden Flächen
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

    # ==============================
    # Die Fasern
    # ==============================

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
            # Innen die Farbe der Schrift, nach außen die Grundfarbe.
            color = _mix(
                _faded(ink, 0.55), self._nuance(0.02, 0.55, 1.30, 0.85),
                0.12 + 0.88 * (index / span),
            )
            # Erst das weiche Leuchten, dann der Kern mit dem Lichtpaket.
            painter.setPen(QPen(_faded(color, color.alphaF() * 0.30), 3.4))
            painter.drawPath(path)
            painter.setPen(self._light_pen(rect, color, position, 1.3))
            painter.drawPath(path)

    # ==============================
    # Die Anzeige
    # ==============================

    def _paint_busy(self, painter: QPainter, rect: QRectF, ink: QColor) -> None:
        painter.setClipRect(rect)
        self._paint_ground(painter, rect)
        self._paint_fibers(painter, rect, ink)
