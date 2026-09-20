# busyhalo.py
#
# `HaloButton` mit Arbeitsanzeige. Hier steht, was alle arbeitenden Halo-Knöpfe
# teilen — der Zustand, die überblendende Beschriftung und der Takt —, dazu die
# zurückhaltende Fassung, die dafür nur ihren Rahmen benutzt.

from __future__ import annotations

import math

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QPropertyAnimation, QRectF, QSize,
    pyqtProperty
)
from PyQt6.QtGui import QColor, QFontMetricsF, QPainter, QPen

from .hoverbuttons import HaloButton, _faded


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class BusyHaloButton(HaloButton):
    """`HaloButton`, der anzeigen kann, dass gerade etwas läuft.

    Unter der Maus verhält er sich wie sein Vorfahr. Dazu kommt ein Zustand
    „arbeitet", den die Anwendung schaltet:

        button.start_busy("Generating")
        button.stop_busy()

    Beim Umschalten blendet die Ruhe-Beschriftung aus und die Arbeits-
    Beschriftung an derselben Stelle ein; beim Anhalten umgekehrt. Ohne
    `busy_text` bleibt die Beschriftung einfach stehen.

    Diese Klasse allein zeichnet noch keine Anzeige — sie hält nur den Takt
    (`phase` läuft in `CYCLE_MS` von 0 nach 1 und wieder von vorn) und die
    Deckkraft (`busy_fade`). Was daraus wird, bestimmt `_paint_busy()` in einer
    Unterklasse: `PulseHaloButton` lässt den Rahmen wandern, `FiberHaloButton`
    füllt die ganze Fläche.
    """

    ACCENT    = "#5a8cff"   # Farbe der Anzeige, das Einzige nicht aus der Palette
    CYCLE_MS  = 2800        # Dauer eines vollen Durchlaufs
    FADE_MS   = 450         # Ein- und Ausblenden der Anzeige
    SWAP_MS   = 260         # Überblenden der Beschriftung
    AUTO_BUSY = True        # Ein Klick startet die Anzeige von allein

    def __init__(self, text: str = "", busy_text: str = "", parent=None) -> None:
        self._phase = 0.0        # Takt der Anzeige, 0..1, läuft um
        self._busy_fade = 0.0    # 0 = keine Anzeige, 1 = ganz da
        self._label_fade = 0.0   # 0 = Ruhetext, 1 = Arbeitstext
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

        self._swap = QPropertyAnimation(self, b"label_fade", self)
        self._swap.setDuration(self.SWAP_MS)
        self._swap.setEasingCurve(QEasingCurve.Type.InOutCubic)

        if self.AUTO_BUSY:
            self.clicked.connect(self._on_clicked)

    # ==============================
    # Öffentliche API
    # ==============================

    def start_busy(self, label: str | None = None) -> None:
        """Blendet die Anzeige auf und wechselt auf die Arbeits-Beschriftung."""
        if label is not None:
            self.setBusyText(label)
        self._busy = True
        if self._cycle.state() != QAbstractAnimation.State.Running:
            self._cycle.start()
        self._run(self._fade, self._busy_fade, 1.0)
        self._run(self._swap, self._label_fade, 1.0 if self._busy_text else 0.0)

    def stop_busy(self) -> None:
        """Blendet die Anzeige aus und die Ruhe-Beschriftung zurück."""
        self._busy = False
        self._run(self._fade, self._busy_fade, 0.0)
        self._run(self._swap, self._label_fade, 0.0)

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
        """Die Farbe der Anzeige, nur für diesen Knopf."""
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

    @pyqtProperty(float)
    def label_fade(self) -> float:
        return self._label_fade

    @label_fade.setter
    def label_fade(self, value: float) -> None:
        self._label_fade = value
        self.update()

    @staticmethod
    def _run(anim: QPropertyAnimation, current: float, target: float) -> None:
        """Eine Animation von hier nach dort starten.

        Heißt bewusst nicht `_animate` — so nennt der Basisknopf schon den
        Hover-Weg.
        """
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    def _on_fade_finished(self) -> None:
        # Den Takt erst anhalten, wenn nichts mehr davon zu sehen ist.
        if not self._busy and self._busy_fade <= 0.0:
            self._cycle.stop()
            self.update()

    def _on_clicked(self) -> None:
        if not self._busy:
            self.start_busy()

    # ==============================
    # Beschriftung
    # ==============================

    def _cased(self, text: str) -> str:
        return text.upper() if self.UPPERCASE else text

    def _paint_label(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        swap = _clamp(self._label_fade)

        if swap < 1.0:
            painter.save()
            painter.setOpacity(painter.opacity() * (1.0 - swap))
            self._draw_label(painter, rect, hover, self._cased(self.text()))
            painter.restore()

        if swap > 0.0 and self._busy_text:
            painter.save()
            painter.setOpacity(painter.opacity() * swap)
            self._draw_label(painter, rect, hover, self._cased(self._busy_text))
            painter.restore()

    def sizeHint(self) -> QSize:
        # Beide Beschriftungen müssen passen, sonst rutscht das Fenster, sobald
        # die Aufgabe losläuft.
        hint = super().sizeHint()
        if not self._busy_text:
            return hint
        width = QFontMetricsF(self._label_font(1.0)).horizontalAdvance(
            self._cased(self._busy_text)
        )
        needed = int(round(width)) + 2 * self.PAD + 2 * self.ROOM
        return QSize(max(hint.width(), needed), hint.height())

    # ==============================
    # Darstellung
    # ==============================

    def _paint_busy(self, painter: QPainter, rect: QRectF, ink: QColor) -> None:
        """Die Anzeige selbst — in den Unterklassen."""

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        # Erst die Anzeige, dann der Halo — sein Strich und sein Schein sollen
        # darüber liegen, nicht darin verschwinden.
        if self._busy_fade > 0.0 and rect.width() > 12 and rect.height() > 6:
            painter.save()
            # Die Anzeige bleibt kräftig, auch wenn der Knopf während der
            # Aufgabe gesperrt ist — sonst wäre gerade das nicht zu sehen,
            # worauf man wartet.
            painter.setOpacity(_clamp(self._busy_fade))
            self._paint_busy(painter, rect, self._ink(hover))
            painter.restore()

        super()._paint_surface(painter, rect, hover)


class PulseHaloButton(BusyHaloButton):
    """Arbeitet ruhig: aus dem Rahmen laufen langsam Striche nach außen.

    Die Fläche bleibt leer, die Beschriftung wechselt weich auf den Arbeitstext.
    Aus dem Rand des Knopfes löst sich in jedem Durchlauf ein Strich, wandert in
    den freien Rand hinaus und verblasst dabei; `RINGS` davon sind gleichzeitig
    unterwegs, gegeneinander versetzt, damit nie eine Lücke entsteht.

    Gedacht für Stellen, an denen eine Anzeige nötig ist, aber nichts blinken
    oder flimmern soll — etwa der Knopf, der eine lange Aufgabe startet.
    """

    RINGS      = 2      # wie viele Striche gleichzeitig unterwegs sind
    RING_W     = 1.4    # Strichstärke
    RING_ALPHA = 0.75   # Deckkraft in der Mitte des Weges
    CYCLE_MS   = 2800

    def _paint_busy(self, painter: QPainter, rect: QRectF, ink: QColor) -> None:
        room = self._room()
        if room <= 0:
            return

        for index in range(self.RINGS):
            part = (self._phase + index / self.RINGS) % 1.0
            # Auf halbem Weg am kräftigsten, am Rand und am Ziel unsichtbar.
            alpha = self.RING_ALPHA * math.sin(math.pi * part)
            if alpha <= 0.01:
                continue
            out = room * part
            painter.setPen(QPen(_faded(self._accent, alpha), self.RING_W))
            painter.drawRect(rect.adjusted(-out, -out, out, out))
