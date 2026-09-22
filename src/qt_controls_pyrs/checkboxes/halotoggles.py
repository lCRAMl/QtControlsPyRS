# halotoggles.py
#
# Drei Schalter im Stil der Halo-Knöpfe: feine Linien, innen leer, weiß unter
# der Maus, und eingeschaltet ein Kern in der Signalfarbe mit weichem Schein.
#
#   FrameToggle   ein kleiner Rahmen, in dem eine Kugel gleitet
#   LineToggle    ein Strich, auf dem eine Kugel läuft
#   HaloCheckBox  ein Kästchen, das sich füllt; beim Anhaken läuft einmal ein
#                 Strich nach außen, wie beim HaloButton
#
# Alle drei bleiben nach außen eine QCheckBox.

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, QSize, QSizeF, Qt,
    pyqtProperty
)
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen, QRadialGradient
from PyQt6.QtWidgets import QCheckBox

from ..buttons.hoverbuttons import _crisp, _faded, _glow, _mix, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class _HaloToggle(QCheckBox):
    """Was die drei Schalter teilen: Zustand, Gleiten, Maus und Beschriftung.

    Nach außen bleibt es eine QCheckBox: `isChecked()`, `setChecked()` und das
    `toggled`-Signal funktionieren unverändert; ein Klick auf die Beschriftung
    schaltet ebenfalls um. Die Anzeige selbst zeichnet `_paint_indicator()` in
    der jeweiligen Unterklasse.
    """

    GAP           = 8          # Abstand zwischen Anzeige und Beschriftung
    RADIUS        = 0          # Eckenradius des Rahmens
    ACCENT        = "#5a8cff"  # Farbe des eingeschalteten Kerns
    OUTLINE_ALPHA = 0.5        # Deckkraft von Rahmen und Strich in Ruhe
    SLIDE_MS      = 200        # Umschalten
    HOVER_MS      = 1250       # wie die Halo-Knöpfe: schnell hin, lang aus

    def __init__(self, text: str = "", parent=None) -> None:
        self._position = 0.0      # 0 = aus, 1 = an — gleitet dazwischen
        self._hover = 0.0
        self._accent = QColor(self.ACCENT)
        super().__init__(text, parent)

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self._slide = self._animation(b"position", self.SLIDE_MS, QEasingCurve.Type.InOutCubic)
        self._hover_anim = self._animation(b"hover", self.HOVER_MS, QEasingCurve.Type.OutExpo)

        self.toggled.connect(self._on_toggled)
        self._position = 1.0 if self.isChecked() else 0.0

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
    # Farbe
    # ==============================

    def accent_color(self) -> QColor:
        return QColor(self._accent)

    def setAccentColor(self, color) -> None:
        """Die Farbe des eingeschalteten Kerns, nur für diesen Schalter."""
        self._accent = QColor(color)
        self.update()

    # ==============================
    # Animierte Eigenschaften
    # ==============================

    @pyqtProperty(float)
    def position(self) -> float:
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        self._position = value
        self.update()

    @pyqtProperty(float)
    def hover(self) -> float:
        return self._hover

    @hover.setter
    def hover(self, value: float) -> None:
        self._hover = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        if not self.isVisible():
            # Noch nicht zu sehen — etwa beim Einlesen gespeicherter
            # Einstellungen: gleich richtig stehen, nichts animieren.
            self._slide.stop()
            self._position = target
            self.update()
            return
        self._run(self._slide, self._position, target)

    # ==============================
    # Maus
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._run(self._hover_anim, self._hover, 0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Ein gesperrter Schalter bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._run(self._hover_anim, self._hover, 0.0)

    def hitButton(self, pos) -> bool:
        # Auch ein Klick auf die Beschriftung schaltet um.
        return self.rect().contains(pos)

    # ==============================
    # Geometrie
    # ==============================

    def _indicator_size(self) -> QSizeF:
        """Wie viel Platz die Anzeige braucht — in den Unterklassen."""
        raise NotImplementedError

    def _indicator_rect(self) -> QRectF:
        size = self._indicator_size()
        return QRectF(0.0, (self.height() - size.height()) / 2, size.width(), size.height())

    def sizeHint(self) -> QSize:
        size = self._indicator_size()
        width = size.width()
        if self.text():
            width += self.GAP + self.fontMetrics().horizontalAdvance(self.text())
        height = max(size.height(), self.fontMetrics().height() + 4)
        return QSize(int(round(width)), int(round(height)))

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _line_color(self) -> QColor:
        """Rahmen und Strich: halbdurchsichtig in Ruhe, weiß unter der Maus."""
        ink = self._ink()
        hover = _clamp(self._hover)
        return _faded(ink, self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * hover)

    def _paint_knob(
        self, painter: QPainter, center: QPointF, radius: float,
        clip: QPainterPath | None = None,
    ) -> None:
        """Die Kugel: aus ein hohler Ring, an gefüllt und mit weichem Schein."""
        on = _clamp(self._position)
        ink = self._ink()

        if on > 0.0:
            painter.save()
            if clip is not None:
                painter.setClipPath(clip)
            glow = QRadialGradient(center, radius * 2.0)
            glow.setColorAt(0.0, _faded(self._accent, 0.55 * on))
            glow.setColorAt(1.0, _faded(self._accent, 0.0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(center, radius * 2.0, radius * 2.0)
            painter.restore()

        hover = _clamp(self._hover)
        ring = _mix(_faded(ink, 0.7 + 0.3 * hover), self._accent, on)
        painter.setPen(QPen(ring, 1.4))
        painter.setBrush(QBrush(_faded(self._accent, on)))
        painter.drawEllipse(center, radius, radius)

    def _paint_indicator(self, painter: QPainter, rect: QRectF) -> None:
        """Die Anzeige selbst — in den Unterklassen."""
        raise NotImplementedError

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        rect = self._indicator_rect()
        self._paint_indicator(painter, rect)

        if self.text():
            left = rect.right() + self.GAP
            painter.setPen(QPen(self.palette().color(
                QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText
            )))
            painter.drawText(
                QRectF(left, 0, max(self.width() - left, 0), self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )
        painter.end()


class FrameToggle(_HaloToggle):
    """Ein kleiner Rahmen, in dem eine Kugel gleitet — die Dropdown-Leiste im Kleinen.

    Aus steht links ein hohler Ring. Eingeschaltet gleitet er nach rechts,
    füllt sich in der Signalfarbe, und innen glimmt der Rahmen auf wie ein
    Halo-Knopf unter der Maus. Unter der Maus wird der Rahmen weiß.
    """

    TRACK_W    = 42      # Breite des Rahmens
    TRACK_H    = 22      # Höhe des Rahmens
    KNOB_PAD   = 4       # Abstand der Kugel zum Rahmen
    INNER_GLOW = 8       # Schein innen, wenn eingeschaltet

    def _indicator_size(self) -> QSizeF:
        return QSizeF(self.TRACK_W, self.TRACK_H)

    def _paint_indicator(self, painter: QPainter, rect: QRectF) -> None:
        on = _clamp(self._position)
        radius = float(self.RADIUS)
        frame = _crisp(rect, 1.0)

        # Eingeschaltet glimmt es innen in der Signalfarbe.
        if on > 0.0:
            _glow(painter, rect, _faded(self._accent, 0.55 * on), self.INNER_GLOW,
                  inside=True, radius=radius)

        painter.setPen(QPen(self._line_color(), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, frame, max(radius - 0.5, 0.0))

        knob = (self.TRACK_H - 2 * self.KNOB_PAD) / 2
        start = rect.left() + self.KNOB_PAD + knob
        end = rect.right() - self.KNOB_PAD - knob
        center = QPointF(start + (end - start) * on, rect.center().y())

        # Der Schein der Kugel bleibt im Rahmen.
        shape = QPainterPath()
        shape.addRoundedRect(frame, max(radius - 0.5, 0.0), max(radius - 0.5, 0.0))
        self._paint_knob(painter, center, knob, clip=shape)


class LineToggle(_HaloToggle):
    """Ein Strich, so fein wie der Rahmen eines Knopfes, auf dem eine Kugel läuft.

    Aus steht links ein hohler Ring. Eingeschaltet läuft er nach rechts, füllt
    sich in der Signalfarbe und bekommt einen weichen Schein; der Strich hinter
    ihm leuchtet mit auf. Unter der Maus wird der Strich weiß.
    """

    TRACK_W = 42         # Länge des Strichs — so breit wie der Rahmen-Schalter
    BALL    = 12         # Durchmesser der Kugel

    def _indicator_size(self) -> QSizeF:
        # Platz für den Schein der Kugel an beiden Enden und oben wie unten.
        return QSizeF(self.TRACK_W + 2 * self.BALL, 2 * self.BALL)

    def _paint_indicator(self, painter: QPainter, rect: QRectF) -> None:
        on = _clamp(self._position)
        y = int(rect.center().y()) + 0.5          # ein Pixel, gestochen scharf
        start = rect.left() + self.BALL
        end = rect.right() - self.BALL
        x = start + (end - start) * on

        painter.setPen(QPen(self._line_color(), 1.0))
        painter.drawLine(QPointF(start, y), QPointF(end, y))

        # Hinter der Kugel leuchtet der Strich in der Signalfarbe.
        if on > 0.0:
            pen = QPen(_faded(self._accent, on), 1.4)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen)
            painter.drawLine(QPointF(start, y), QPointF(x, y))

        self._paint_knob(painter, QPointF(x, y), self.BALL / 2)


class HaloCheckBox(_HaloToggle):
    """Ein Kästchen im Halo-Stil: es füllt sich, und einmal läuft ein Strich hinaus.

    Aus ein feiner, leerer Rahmen. Beim Anhaken füllt sich innen ein Kern in der
    Signalfarbe, und ein Strich löst sich aus dem Rahmen, wandert nach außen und
    verblasst — die Bewegung des HaloButton, einmal. Beim Abhaken blendet der
    Kern nur aus. Unter der Maus wird der Rahmen weiß.
    """

    BOX      = 18        # Kantenlänge des Kästchens
    ROOM     = 8         # Platz, in den der Strich hinauswandert
    FILL_PAD = 4         # Abstand des Kerns zum Rahmen
    BURST_MS = 600       # so lange läuft der Strich nach außen

    def __init__(self, text: str = "", parent=None) -> None:
        self._burst = 1.0         # 1 = kein Strich unterwegs
        super().__init__(text, parent)
        self._burst_anim = self._animation(b"burst", self.BURST_MS, QEasingCurve.Type.OutCubic)

    @pyqtProperty(float)
    def burst(self) -> float:
        return self._burst

    @burst.setter
    def burst(self, value: float) -> None:
        self._burst = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        super()._on_toggled(checked)
        # Nur beim Anhaken, und nur wenn es jemand sieht — beim Abhaken oder
        # beim Einlesen gespeicherter Einstellungen läuft nichts nach außen.
        if checked and self.isVisible():
            self._run(self._burst_anim, 0.0, 1.0)

    def _indicator_size(self) -> QSizeF:
        return QSizeF(self.BOX + 2 * self.ROOM, self.BOX + 2 * self.ROOM)

    def sizeHint(self) -> QSize:
        # Links hält das Kästchen Platz für den Strich frei. Mit Beschriftung
        # bleibt rechts derselbe Rand, damit es in einem mittigen Layout auch
        # wirklich mittig steht.
        hint = super().sizeHint()
        if self.text():
            hint.setWidth(hint.width() + self.ROOM)
        return hint

    def _paint_indicator(self, painter: QPainter, rect: QRectF) -> None:
        on = _clamp(self._position)
        radius = float(self.RADIUS)
        box = QRectF(rect.left() + self.ROOM, rect.top() + self.ROOM, self.BOX, self.BOX)

        # Der Kern in der Signalfarbe, dazu ein Hauch Schein im Kästchen.
        if on > 0.0:
            core = box.adjusted(self.FILL_PAD, self.FILL_PAD, -self.FILL_PAD, -self.FILL_PAD)
            core_radius = max(radius - self.FILL_PAD / 2, 0.0)
            _glow(painter, box, _faded(self._accent, 0.35 * on), self.FILL_PAD,
                  inside=True, radius=radius)
            path = QPainterPath()
            path.addRoundedRect(core, core_radius, core_radius)
            painter.fillPath(path, QBrush(_faded(self._accent, on)))

        painter.setPen(QPen(self._line_color(), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(box, 1.0), max(radius - 0.5, 0.0))

        # Einmal nach außen: der Strich wandert in den Rand und verblasst.
        burst = _clamp(self._burst)
        if burst < 1.0:
            out = self.ROOM * burst
            painter.setPen(QPen(_faded(self._accent, 0.8 * (1.0 - burst)), 1.2))
            _outline(painter, box.adjusted(-out, -out, out, out),
                     radius + out if radius > 0.0 else 0.0)
