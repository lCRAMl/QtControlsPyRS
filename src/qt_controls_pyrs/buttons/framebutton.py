# framebutton.py

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPropertyAnimation, QRectF, QSize, Qt, pyqtProperty
)
from PyQt6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QPushButton


class FrameButton(QPushButton):
    """Knopf, der unter der Maus seinen Schleier abgibt und einen Rahmen einfängt.

    Im Ruhezustand liegt ein hauchdünner Schleier über der ganzen Fläche. Kommt
    die Maus darauf, schrumpft der Schleier zur Mitte und verblasst, während
    gleichzeitig ein feiner Rahmen von außen hereinfährt und sichtbar wird.
    Verlässt die Maus den Knopf, läuft beides rückwärts.

    Nachbau des CSS-Musters ``.btn-three``: der Schleier ist dort ``::before``
    (Deckkraft 0.1, schrumpft auf ``scale(0.5)``), der Rahmen ``::after``
    (Deckkraft 0.5, kommt von ``scale(1.2)``), beide mit 0.3 s Übergang. Die
    Farben kommen aus der Palette statt fest aus Weiß, damit der Knopf im
    Hell- wie im Dunkelmodus stimmt.
    """

    RADIUS     = 0      # Eckenradius für Fläche, Schleier und Rahmen
    VEIL_A     = 26     # Deckkraft des Schleiers im Ruhezustand (0.1 in CSS)
    VEIL_END   = 0.5    # Größe, auf die der Schleier zusammenschrumpft
    RING_A     = 128    # Deckkraft des Rahmens, wenn er ganz da ist (0.5)
    RING_W     = 1.0    # Strichstärke des Rahmens
    RING_START = 1.2    # Größe, mit der der Rahmen hereinfährt (scale in CSS)
    RING_ROOM  = 10     # ... aber höchstens so viele Pixel weit draußen
    HOVER_MS   = 300    # Dauer von Schleier und Rahmen
    TINT_MS    = 500    # Dauer der Aufhellung darunter
    TINT       = 112    # Aufhellung der Fläche unter der Maus (100 = keine)

    def __init__(self, text: str = "", parent=None) -> None:
        self._hover = 0.0     # 0 = Maus weg, 1 = Maus darauf
        self._tint = 0.0      # 0 = Grundfarbe, 1 = aufgehellt
        super().__init__(text, parent)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._hover_anim = self._animation(b"hover", self.HOVER_MS)
        self._tint_anim = self._animation(b"tint", self.TINT_MS)

    def _animation(self, name: bytes, duration: int) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return anim

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
    def tint(self) -> float:
        return self._tint

    @tint.setter
    def tint(self, value: float) -> None:
        self._tint = value
        self.update()

    def _animate(self, target: float) -> None:
        for anim, current in ((self._hover_anim, self._hover), (self._tint_anim, self._tint)):
            anim.stop()
            anim.setStartValue(current)
            anim.setEndValue(target)
            anim.start()

    # ==============================
    # Mauszustand
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._animate(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate(0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Ein gesperrter Knopf bekommt kein leaveEvent mehr — ohne das hier
        # bliebe der Rahmen stehen, bis die Maus wiederkommt.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._animate(0.0)

    # ==============================
    # Geometrie
    # ==============================

    def _room(self) -> tuple[float, float]:
        """Rand, der für den hereinfahrenden Rahmen frei bleibt.

        `scale(1.2)` würde bei einem breiten Knopf einen sehr weiten Rand
        verlangen — ein Zehntel der Breite je Seite — und die Fläche entsprechend
        schmal machen. `RING_ROOM` begrenzt das: bis zu dieser Weite entspricht
        der Rahmen genau der CSS-Vorlage, darüber fährt er aus fester Entfernung
        herein statt aus immer weiterer.
        """
        grow = (self.RING_START - 1.0) / 2.0
        return (
            min(self.width() * grow, float(self.RING_ROOM)),
            min(self.height() * grow, float(self.RING_ROOM)),
        )

    def _surface(self) -> QRectF:
        """Die sichtbare Fläche des Knopfes — kleiner als das Widget."""
        room_x, room_y = self._room()
        return QRectF(self.rect()).adjusted(room_x, room_y, -room_x, -room_y)

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(
            hint.width() + 2 * self.RING_ROOM,
            hint.height() + 2 * self.RING_ROOM,
        )

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        return QSize(
            hint.width() + 2 * self.RING_ROOM,
            hint.height() + 2 * self.RING_ROOM,
        )

    @staticmethod
    def _scaled(rect: QRectF, factor: float) -> QRectF:
        """Dasselbe Rechteck, um die Mitte herum vergrößert oder verkleinert."""
        box = QRectF(0, 0, rect.width() * factor, rect.height() * factor)
        box.moveCenter(rect.center())
        return box

    def _rounded(self, rect: QRectF) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(rect, self.RADIUS, self.RADIUS)
        return path

    # ==============================
    # Darstellung
    # ==============================

    def _fill(self) -> QColor:
        group = (
            QPalette.ColorGroup.Normal if self.isEnabled()
            else QPalette.ColorGroup.Disabled
        )
        color = self.palette().color(group, QPalette.ColorRole.Button)
        if self.isDown():
            return color.darker(115)
        tint = 100 + (self.TINT - 100) * max(0.0, min(1.0, self._tint))
        return color.lighter(int(round(tint)))

    def _ink(self) -> QColor:
        # Auch im gesperrten Zustand gut lesbar bleiben.
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        surface = self._surface()
        ink = self._ink()
        hover = max(0.0, min(1.0, self._hover))

        painter.fillPath(self._rounded(surface), QBrush(self._fill()))

        # Der Knopf zeichnet seine Beschriftung selbst, damit Schleier und
        # Rahmen darüber liegen — in CSS haben beide z-index: 1.
        painter.setPen(QPen(ink))
        painter.setFont(self.font())
        painter.drawText(surface, int(Qt.AlignmentFlag.AlignCenter), self.text())

        # Schleier: verblasst und schrumpft zur Mitte.
        veil = QColor(ink)
        veil.setAlpha(int(self.VEIL_A * (1.0 - hover)))
        if veil.alpha() > 0:
            shrink = 1.0 - (1.0 - self.VEIL_END) * hover
            painter.fillPath(self._rounded(self._scaled(surface, shrink)), QBrush(veil))

        # Rahmen: fährt von außen herein und wird sichtbar. Der Strich liegt
        # dabei immer im Widget, sonst schnitte ihn der Rand unterwegs ab.
        ring = QColor(ink)
        ring.setAlpha(int(self.RING_A * hover))
        if ring.alpha() > 0:
            room_x, room_y = self._room()
            out = 1.0 - hover
            grow_x = max(room_x - self.RING_W / 2, 0.0) * out
            grow_y = max(room_y - self.RING_W / 2, 0.0) * out
            painter.setPen(QPen(ring, self.RING_W))
            painter.drawPath(
                self._rounded(surface.adjusted(-grow_x, -grow_y, grow_x, grow_y))
            )

        painter.end()
