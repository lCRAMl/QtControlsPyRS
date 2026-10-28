# halospinbox.py
#
# Zahlenfelder im Stil der Halo-Knöpfe: dieselbe Leiste wie beim HaloDropdown,
# rechts zwei feine Pfeile zum Schrittschalten.
#
#   HaloSpinBox        ganze Zahlen        — ersetzt QSpinBox
#   HaloDoubleSpinBox  mit Nachkommastellen — ersetzt QDoubleSpinBox
#
# Beide teilen sich _HaloSpin. Das geht, weil QSpinBox und QDoubleSpinBox
# denselben Vorfahren QAbstractSpinBox haben — die gemeinsame Hälfte steht
# einmal da und nicht zweimal.
#
# Qts eigene Pfeile sind abgeschaltet (ButtonSymbols.NoButtons), nicht
# überzeichnet: ein abgeschalteter Knopf nimmt keine Klicks mehr an, ein
# überzeichneter schon. Tastatur und Mausrad schalten weiterhin von selbst —
# das steckt in QAbstractSpinBox und nicht in den Pfeilen.

from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, QSize, QTimer, Qt,
    pyqtProperty
)
from PyQt6.QtGui import QColor, QFontMetricsF, QPainter, QPalette, QPen, QPolygonF
from PyQt6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QSpinBox

from ..buttons.hoverbuttons import _crisp, _faded, _glow, _mix, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class _HaloSpin:
    """Was beide Zahlenfelder teilen: Leiste, Pfeile, Maus und Tastatur.

    Nach außen bleibt es ein ``QSpinBox`` beziehungsweise ``QDoubleSpinBox``:
    ``value()``, ``setValue()``, ``setRange()``, ``setSuffix()``,
    ``valueChanged`` und alles Weitere verhalten sich unverändert.
    """

    HEIGHT        = 45        # Höhe der Fläche, wie beim HaloDropdown
    ROOM          = 16        # Rand links und rechts — bündig mit den Knöpfen
    ROOM_Y        = 4         # Rand oben und unten
    PAD           = 16        # Abstand der Zahl zum Rahmen
    RADIUS        = 0         # Eckenradius
    OUTLINE_ALPHA = 0.5       # Deckkraft des Rahmens in Ruhe
    INNER_GLOW    = 20        # innerer Schein unter der Maus
    HOVER_MS      = 1250      # wie die Halo-Knöpfe: schnell hin, lang aus
    FOCUS_MS      = 220       # die Schreibmarke kommt schneller als die Maus

    ARROW_ZONE  = 26          # Breite der Pfeilspalte
    ARROW_W     = 5           # halbe Breite eines Pfeils
    ARROW_H     = 3.5         # halbe Höhe
    ARROW_ALPHA = 0.45        # Deckkraft eines Pfeils in Ruhe
    ARROW_MS    = 160         # Aufleuchten unter der Maus

    ACCENT     = "#5a8cff"    # Farbe des Aufblitzens beim Schalten
    FLASH_MS   = 260          # so lange blitzt der benutzte Pfeil
    REPEAT_MS  = 400          # Haltedauer, bis das Weiterschalten beginnt
    INTERVAL_MS = 60          # danach ein Schritt je Intervall

    MIN_CHARS = 6             # so viel Platz hält das Feld mindestens frei

    # ==============================
    # Aufbau
    # ==============================

    def _init_halo(self) -> None:
        self._hover = 0.0
        self._focus = 0.0
        self._alert = None
        self._up = 0.0          # Deckkraft des oberen Pfeils
        self._down = 0.0
        self._flash_up = 0.0    # Aufblitzen nach einem Schritt
        self._flash_down = 0.0
        self._held = 0          # +1 oder -1, solange die Maus gedrückt ist
        self._accent = QColor(self.ACCENT)

        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setFrame(False)    # der Rahmen kommt aus paintEvent, nicht aus dem Stil
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        # Qt füllt die Fläche des Zahlenfelds mit der Palettenfarbe `Base`
        # — und zwar in super().paintEvent(), also NACH dem Rahmen. Der Rahmen
        # verschwände darunter, und innen stünde ein graues Rechteck statt der
        # leeren Halo-Leiste. Die Füllung wird deshalb durchsichtig gesetzt.
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Base, QColor(Qt.GlobalColor.transparent))
        self.setPalette(palette)
        self.setAutoFillBackground(False)

        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        edit = self.lineEdit()
        if edit is not None:
            edit.setPalette(palette)
            edit.setAutoFillBackground(False)
            edit.setTextMargins(
                self.ROOM + self.PAD, 0, self.ROOM + self._arrow_space(), 0
            )

        self._hover_anim = self._animation(b"hover", self.HOVER_MS, QEasingCurve.Type.OutExpo)
        self._focus_anim = self._animation(b"focus", self.FOCUS_MS, QEasingCurve.Type.OutCubic)
        self._up_anim = self._animation(b"up", self.ARROW_MS, QEasingCurve.Type.OutCubic)
        self._down_anim = self._animation(b"down", self.ARROW_MS, QEasingCurve.Type.OutCubic)
        self._flash_up_anim = self._animation(b"flashUp", self.FLASH_MS, QEasingCurve.Type.OutCubic)
        self._flash_down_anim = self._animation(b"flashDown", self.FLASH_MS, QEasingCurve.Type.OutCubic)

        # Halten schaltet weiter — erst nach einer Pause, dann zügig. Dieselbe
        # Staffelung wie bei Qts eigenen Pfeilen, sonst fühlt es sich fremd an.
        self._repeat = QTimer(self)
        self._repeat.setSingleShot(True)
        self._repeat.timeout.connect(self._begin_repeat)
        self._ticker = QTimer(self)
        self._ticker.setInterval(self.INTERVAL_MS)
        self._ticker.timeout.connect(self._repeat_step)

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
        """Die Farbe des Aufblitzens, nur für dieses Feld."""
        self._accent = QColor(color)
        self.update()


    # ==============================
    # Hinweisfarbe
    # ==============================

    def alert_color(self) -> QColor | None:
        return QColor(self._alert) if self._alert is not None else None

    def setAlert(self, color=None) -> None:  # noqa: N802 - Qt-Namensschema
        """Färbt den Rahmen, solange etwas nicht stimmt. ``None`` hebt es auf.

        Gedacht für Fehler und Warnungen am Feld selbst. Ein Stylesheet-Rand
        griffe hier nicht: der Rahmen wird gezeichnet und nicht vom Stil
        gesetzt. Die Farbe bleibt stehen, bis sie zurückgenommen wird - anders
        als das kurze Aufblitzen nach einem Schritt.
        """
        self._alert = QColor(color) if color is not None else None
        self.update()

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

    @pyqtProperty(float)
    def up(self) -> float:
        return self._up

    @up.setter
    def up(self, value: float) -> None:
        self._up = value
        self.update()

    @pyqtProperty(float)
    def down(self) -> float:
        return self._down

    @down.setter
    def down(self, value: float) -> None:
        self._down = value
        self.update()

    @pyqtProperty(float)
    def flashUp(self) -> float:  # noqa: N802 - Qt-Namensschema
        return self._flash_up

    @flashUp.setter
    def flashUp(self, value: float) -> None:  # noqa: N802
        self._flash_up = value
        self.update()

    @pyqtProperty(float)
    def flashDown(self) -> float:  # noqa: N802
        return self._flash_down

    @flashDown.setter
    def flashDown(self, value: float) -> None:  # noqa: N802
        self._flash_down = value
        self.update()

    def _level(self) -> float:
        """Wie hell der Rahmen steht — Maus und Schreibmarke, je nachdem was mehr ist."""
        return max(_clamp(self._hover), _clamp(self._focus))

    # ==============================
    # Geometrie
    # ==============================

    def _surface(self) -> QRectF:
        room_x = min(float(self.ROOM), self.width() / 4.0)
        room_y = min(float(self.ROOM_Y), self.height() / 4.0)
        return QRectF(self.rect()).adjusted(room_x, room_y, -room_x, -room_y)

    def _arrow_space(self) -> float:
        """Was die Pfeile rechts belegen, Einrückung eingeschlossen.

        Um PAD eingerückt wie der Pfeil des HaloDropdown — sonst klebten die
        Pfeile am Rahmen, während der Haken nebenan Luft hat.
        """
        return self.ARROW_ZONE + self.PAD

    def _arrow_rects(self) -> tuple[QRectF, QRectF]:
        """Die beiden Hälften der Pfeilspalte: oben hoch, unten herunter."""
        surface = self._surface()
        zone = QRectF(
            surface.right() - self._arrow_space(), surface.top(),
            self.ARROW_ZONE, surface.height(),
        )
        middle = zone.center().y()
        return (
            QRectF(zone.left(), zone.top(), zone.width(), middle - zone.top()),
            QRectF(zone.left(), middle, zone.width(), zone.bottom() - middle),
        )

    def _zone_at(self, pos) -> int:
        """+1 über dem oberen Pfeil, -1 über dem unteren, sonst 0."""
        point = QPointF(pos)
        up_rect, down_rect = self._arrow_rects()
        if up_rect.contains(point):
            return 1
        if down_rect.contains(point):
            return -1
        return 0

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        texts = [self.textFromValue(self.minimum()), self.textFromValue(self.maximum())]
        widest = max((metrics.horizontalAdvance(t) for t in texts), default=0.0)
        widest = max(widest, metrics.averageCharWidth() * self.MIN_CHARS)
        widest += metrics.horizontalAdvance(self.prefix() + self.suffix())
        width = widest + 2 * self.PAD + self._arrow_space() + 2 * self.ROOM
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    def minimumSizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        width = (metrics.averageCharWidth() * self.MIN_CHARS
                 + 2 * self.PAD + self._arrow_space() + 2 * self.ROOM)
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    # ==============================
    # Maus, Schreibmarke, Schritte
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._run(self._hover_anim, self._hover, 0.0)
        self._light_arrows(0)

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
            self._stop_repeat()
            self._run(self._hover_anim, self._hover, 0.0)
            self._run(self._focus_anim, self._focus, 0.0)
            self._light_arrows(0)

    def _light_arrows(self, zone: int) -> None:
        self._run(self._up_anim, self._up, 1.0 if zone > 0 else 0.0)
        self._run(self._down_anim, self._down, 1.0 if zone < 0 else 0.0)

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        if self._held == 0:
            self._light_arrows(self._zone_at(event.position()))

    def mousePressEvent(self, event) -> None:
        zone = self._zone_at(event.position()) if event.button() == Qt.MouseButton.LeftButton else 0
        if zone == 0:
            super().mousePressEvent(event)
            return
        # Der Klick gilt dem Pfeil, nicht dem Text darunter: nicht weitergeben,
        # sonst setzt QLineEdit nebenbei die Schreibmarke.
        self._held = zone
        self._light_arrows(zone)
        self._step(zone)
        self._repeat.start(self.REPEAT_MS)
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._held != 0:
            self._stop_repeat()
            self._light_arrows(self._zone_at(event.position()))
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _begin_repeat(self) -> None:
        if self._held != 0:
            self._ticker.start()

    def _repeat_step(self) -> None:
        if self._held == 0:
            self._stop_repeat()
            return
        self._step(self._held)

    def _stop_repeat(self) -> None:
        self._held = 0
        self._repeat.stop()
        self._ticker.stop()

    def _step(self, direction: int) -> None:
        """Einen Schritt gehen und den benutzten Pfeil aufblitzen lassen."""
        self.stepBy(direction)
        if direction > 0:
            self._run(self._flash_up_anim, 1.0, 0.0)
        else:
            self._run(self._flash_down_anim, 1.0, 0.0)

    def stepBy(self, steps: int) -> None:
        # Auch Tastatur und Mausrad sollen den Pfeil aufblitzen lassen - sie
        # gehen durch stepBy() und nicht durch _step().
        super().stepBy(steps)
        if self._held == 0 and steps != 0:
            if steps > 0:
                self._run(self._flash_up_anim, 1.0, 0.0)
            else:
                self._run(self._flash_down_anim, 1.0, 0.0)

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

        Dieselben zwei Schritte wie beim HaloDropdown und beim HaloLineEdit,
        damit die drei nebeneinander gleich aussehen.
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

        if self._alert is not None:
            # Kräftig, auch wenn das Feld gesperrt ist - ein Fehler soll
            # sichtbar bleiben.
            painter.save()
            painter.setOpacity(1.0)
            _glow(painter, rect, _faded(self._alert, 0.3), self.INNER_GLOW,
                  inside=True, radius=radius)
            painter.setPen(QPen(_faded(self._alert, 0.95), 1.4))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            _outline(painter, _crisp(rect, 1.4), max(radius - 0.7, 0.0))
            painter.restore()

    def _paint_arrow(
        self, painter: QPainter, box: QRectF, pointing_up: bool,
        light: float, flash: float,
    ) -> None:
        ink = self._ink()
        alpha = self.ARROW_ALPHA + (1.0 - self.ARROW_ALPHA) * _clamp(light)
        color = _mix(_faded(ink, alpha), self._accent, _clamp(flash))

        center = box.center()
        tip = center.y() - self.ARROW_H if pointing_up else center.y() + self.ARROW_H
        base = center.y() + self.ARROW_H if pointing_up else center.y() - self.ARROW_H
        triangle = QPolygonF([
            QPointF(center.x() - self.ARROW_W, base),
            QPointF(center.x() + self.ARROW_W, base),
            QPointF(center.x(), tip),
        ])

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawPolygon(triangle)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        surface = self._surface()
        self._paint_surface(painter, surface, self._level())

        up_rect, down_rect = self._arrow_rects()
        self._paint_arrow(painter, up_rect, True, self._up, self._flash_up)
        self._paint_arrow(painter, down_rect, False, self._down, self._flash_down)
        painter.end()

        # Und darüber die Zahl, von Qt gezeichnet — wie beim HaloLineEdit.
        super().paintEvent(event)


class HaloSpinBox(_HaloSpin, QSpinBox):
    """Zahlenfeld für ganze Zahlen statt ``QSpinBox``, im Stil der Halo-Knöpfe."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._init_halo()


class HaloDoubleSpinBox(_HaloSpin, QDoubleSpinBox):
    """Zahlenfeld mit Nachkommastellen statt ``QDoubleSpinBox``."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._init_halo()
