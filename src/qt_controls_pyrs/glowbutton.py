# glowbutton.py

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QPointF, QPropertyAnimation, QRectF, Qt, pyqtProperty
)
from PyQt6.QtGui import (
    QBrush, QColor, QGradient, QLinearGradient, QPainter, QPainterPath, QPalette, QPen
)
from PyQt6.QtWidgets import QPushButton


class GlowButton(QPushButton):
    """Knopf mit Regenbogen-Rahmen und überblendender Beschriftung.

    Im Ruhezustand: abgerundete Fläche mit ruhigem Rahmen in der Akzentfarbe.
    Nach `start_busy()` zoomt die Ruhe-Beschriftung heraus und blendet aus,
    während die Arbeits-Beschriftung hereinzoomt und aufblendet. Gleichzeitig
    wandern Regenbogenfarben waagrecht durch den Rahmen — mehrere Farben sind
    dabei immer gleichzeitig zu sehen. `stop_busy()` spielt alles rückwärts.
    """

    RADIUS    = 6       # Eckenradius
    BORDER_W  = 1.6     # Strichstärke des Rahmens
    GLOW_W    = 5.0     # Strichstärke des weichen Leuchtens darunter
    GLOW_A    = 70      # Deckkraft des Leuchtens
    MORPH_MS  = 320     # Dauer der Textüberblendung
    CYCLE_MS  = 2600    # Dauer eines Farbdurchlaufs
    ZOOM      = 0.30    # Zoomweite der Beschriftungen

    # Erste und letzte Farbe sind gleich, damit das Band nahtlos umläuft.
    RAINBOW = (
        "#ff4d4d", "#ff9f1c", "#ffe74c", "#4cd964",
        "#4cc9f0", "#7b61ff", "#ff4d9d", "#ff4d4d",
    )

    def __init__(self, text: str = "", busy_text: str = "Generating", parent=None) -> None:
        self._phase = 0.0     # Position des Farbbandes, 0..1
        self._morph = 0.0     # 0 = Ruhetext, 1 = Arbeitstext
        super().__init__(text, parent)

        self._busy = False
        self._busy_text = busy_text
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._colors = QPropertyAnimation(self, b"phase", self)
        self._colors.setStartValue(0.0)
        self._colors.setEndValue(1.0)
        self._colors.setDuration(self.CYCLE_MS)
        self._colors.setLoopCount(-1)

        self._morph_anim = QPropertyAnimation(self, b"morph", self)
        self._morph_anim.setDuration(self.MORPH_MS)
        self._morph_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._morph_anim.finished.connect(self._on_morph_finished)

    # ==============================
    # Öffentliche API
    # ==============================

    def start_busy(self, label: str | None = None) -> None:
        """Blendet auf die Arbeits-Beschriftung um und startet den Regenbogen."""
        if label is not None:
            self._busy_text = label
        self._busy = True
        self._colors.start()
        self._animate_morph(1.0)

    def stop_busy(self) -> None:
        """Blendet zurück auf die Ruhe-Beschriftung."""
        self._busy = False
        self._animate_morph(0.0)

    def is_busy(self) -> bool:
        return self._busy

    def busy_text(self) -> str:
        return self._busy_text

    def setBusyText(self, label: str) -> None:
        self._busy_text = label
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
        self.update()

    @pyqtProperty(float)
    def morph(self) -> float:
        return self._morph

    @morph.setter
    def morph(self, value: float) -> None:
        self._morph = value
        self.update()

    def _animate_morph(self, target: float) -> None:
        self._morph_anim.stop()
        self._morph_anim.setStartValue(self._morph)
        self._morph_anim.setEndValue(target)
        self._morph_anim.start()

    def _on_morph_finished(self) -> None:
        # Farbband erst anhalten, wenn es vollständig ausgeblendet ist.
        if not self._busy and self._morph <= 0.0:
            self._colors.stop()
            self.update()

    # ==============================
    # Darstellung
    # ==============================

    def _background(self) -> QColor:
        group = (
            QPalette.ColorGroup.Normal if self.isEnabled()
            else QPalette.ColorGroup.Disabled
        )
        color = self.palette().color(group, QPalette.ColorRole.Button)
        if self.isDown():
            return color.darker(115)
        if self.underMouse() and self.isEnabled():
            return color.lighter(115)
        return color

    def _rainbow_pen(self, rect: QRectF, width: float, alpha: int) -> QPen:
        """Waagrechtes Farbband, das sich mit der Phase über den Rahmen schiebt."""
        span = max(rect.width() * 0.6, 120.0)
        shift = (self._phase % 1.0) * span
        gradient = QLinearGradient(
            rect.left() - span + shift, 0.0,
            rect.left() + shift, 0.0,
        )
        gradient.setSpread(QGradient.Spread.RepeatSpread)

        last = len(self.RAINBOW) - 1
        for index, value in enumerate(self.RAINBOW):
            color = QColor(value)
            color.setAlpha(alpha)
            gradient.setColorAt(index / last, color)

        pen = QPen(QBrush(gradient), width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        return pen

    def _draw_label(
        self, painter: QPainter, text: str, dots: str,
        scale: float, opacity: float, color: QColor,
    ) -> None:
        if opacity <= 0.01:
            return

        painter.save()
        painter.setOpacity(opacity)

        center = QPointF(self.width() / 2, self.height() / 2)
        painter.translate(center)
        painter.scale(scale, scale)
        painter.translate(-center)

        painter.setPen(QPen(color))
        painter.setFont(self.font())

        if dots:
            # Platz für alle Punkte reservieren, damit der Text nicht wandert.
            metrics = self.fontMetrics()
            full = metrics.horizontalAdvance(f"{text}...")
            box = QRectF(center.x() - full / 2, 0, full, self.height())
            painter.drawText(
                box,
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                f"{text}{dots}",
            )
        else:
            painter.drawText(
                QRectF(self.rect()),
                int(Qt.AlignmentFlag.AlignCenter),
                text,
            )

        painter.restore()

    def paintEvent(self, event) -> None:
        group = (
            QPalette.ColorGroup.Normal if self.isEnabled()
            else QPalette.ColorGroup.Disabled
        )
        palette = self.palette()
        accent = palette.color(group, QPalette.ColorRole.Highlight)
        # Auch im gesperrten Zustand gut lesbar bleiben:
        text_color = palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        inset = self.GLOW_W / 2
        rect = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        shape = QPainterPath()
        shape.addRoundedRect(rect, self.RADIUS, self.RADIUS)

        painter.fillPath(shape, QBrush(self._background()))

        # Rahmen: ruhiges Blau und Regenbogen ineinander überblenden
        morph = max(0.0, min(1.0, self._morph))
        if morph < 1.0:
            calm = QColor(accent)
            calm.setAlpha(int(255 * (1.0 - morph)))
            painter.setPen(QPen(calm, self.BORDER_W))
            painter.drawPath(shape)

        if morph > 0.0:
            painter.setPen(self._rainbow_pen(rect, self.GLOW_W, int(self.GLOW_A * morph)))
            painter.drawPath(shape)
            painter.setPen(self._rainbow_pen(rect, self.BORDER_W, int(255 * morph)))
            painter.drawPath(shape)

        # Beschriftungen: die eine zoomt heraus und verblasst,
        # die andere zoomt herein und wird sichtbar.
        dots = "." * (1 + int(self._phase * 3) % 3)
        self._draw_label(
            painter, self.text(), "",
            1.0 + self.ZOOM * morph, 1.0 - morph, text_color,
        )
        self._draw_label(
            painter, self._busy_text, dots,
            1.0 - self.ZOOM * (1.0 - morph), morph, text_color,
        )

        painter.end()


# Frueherer Name, damit bestehender Code unveraendert weiterlaeuft.
GenerateButton = GlowButton
