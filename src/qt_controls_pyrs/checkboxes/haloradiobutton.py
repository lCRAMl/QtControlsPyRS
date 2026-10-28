# haloradiobutton.py
#
# Auswahlknopf im Halo-Stil: ein feiner Ring, der sich beim Wählen mit einem
# Kern in der Signalfarbe füllt. Einmal löst sich dabei ein Ring vom Rand,
# wandert nach außen und verblasst — dieselbe Bewegung wie beim HaloButton und
# bei der HaloCheckBox, nur rund.
#
# Rund und nicht eckig ist Absicht und keine Laune: an der Form erkennt man im
# Vorbeigehen, ob eine Entscheidung mehrere Haken erlaubt oder genau eine.
# Qt hält sich daran, Windows hält sich daran, und wer es umdreht, verwirrt.
#
# Die Ausschließlichkeit kommt von QRadioButton selbst: Knöpfe mit demselben
# Elternteil oder in derselben QButtonGroup schalten einander aus. Hier steht
# davon nichts — es wird nur gezeichnet.

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPointF, QRectF, QSizeF, Qt, pyqtProperty
from PyQt6.QtGui import QBrush, QPainter, QPen, QRadialGradient
from PyQt6.QtWidgets import QRadioButton

from ..buttons.hoverbuttons import _faded
from .halotoggles import _HaloTick, _clamp


class HaloRadioButton(_HaloTick, QRadioButton):
    """Auswahlknopf statt ``QRadioButton``, im Stil der Halo-Knöpfe.

    Nach außen bleibt es ein ``QRadioButton``: ``isChecked()``,
    ``setChecked()``, das ``toggled``-Signal und vor allem die
    Ausschließlichkeit innerhalb einer Gruppe verhalten sich unverändert. Ein
    Klick auf die Beschriftung wählt ebenfalls aus.

    Ungewählt steht ein leerer Ring. Beim Wählen wächst innen ein Kern in der
    Signalfarbe heran, darum liegt ein weicher Schein, und einmal läuft ein
    Ring nach außen. Beim Abwählen blendet der Kern nur aus — hinaus läuft
    nichts, sonst blitzte bei jedem Wechsel die halbe Gruppe auf.
    """

    RING     = 18        # Durchmesser des Rings
    ROOM     = 8         # Platz, in den der Ring hinauswandert
    CORE_PAD = 4.5       # Abstand des Kerns zum Ring
    BURST_MS = 600       # so lange läuft der Ring nach außen

    def __init__(self, text: str = "", parent=None) -> None:
        self._burst = 1.0         # 1 = kein Ring unterwegs
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
        # Nur beim Wählen, und nur wenn es jemand sieht — beim Abwählen oder
        # beim Einlesen gespeicherter Einstellungen läuft nichts nach außen.
        if checked and self.isVisible():
            self._run(self._burst_anim, 0.0, 1.0)

    # ==============================
    # Geometrie
    # ==============================

    def _indicator_size(self) -> QSizeF:
        return QSizeF(self.RING + 2 * self.ROOM, self.RING + 2 * self.ROOM)

    def sizeHint(self):
        # Links hält der Knopf Platz für den auslaufenden Ring frei. Mit
        # Beschriftung bleibt rechts derselbe Rand, damit er in einem mittigen
        # Layout auch wirklich mittig steht.
        hint = super().sizeHint()
        if self.text():
            hint.setWidth(hint.width() + self.ROOM)
        return hint

    # ==============================
    # Darstellung
    # ==============================

    def _paint_indicator(self, painter: QPainter, rect: QRectF) -> None:
        on = _clamp(self._position)
        center = QPointF(rect.left() + self.ROOM + self.RING / 2,
                         rect.top() + self.ROOM + self.RING / 2)
        radius = self.RING / 2

        # Der Schein unter dem Kern, weich auslaufend.
        if on > 0.0:
            glow = QRadialGradient(center, radius * 1.9)
            glow.setColorAt(0.0, _faded(self._accent, 0.45 * on))
            glow.setColorAt(1.0, _faded(self._accent, 0.0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow))
            painter.drawEllipse(center, radius * 1.9, radius * 1.9)

            # Der Kern selbst wächst von innen heraus mit.
            core = (radius - self.CORE_PAD) * on
            if core > 0.0:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(_faded(self._accent, on)))
                painter.drawEllipse(center, core, core)

        # Der Ring: halbdurchsichtig in Ruhe, weiß unter der Maus.
        painter.setPen(QPen(self._line_color(), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius - 0.5, radius - 0.5)

        # Einmal nach außen: der Ring wandert in den Rand und verblasst.
        burst = _clamp(self._burst)
        if burst < 1.0:
            out = self.ROOM * burst
            painter.setPen(QPen(_faded(self._accent, 0.8 * (1.0 - burst)), 1.2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius + out, radius + out)
