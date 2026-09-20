# heartcheckbox.py
#
# Herz-Kästchen nach dem Muster "heart-container" von Uiverse.io (catraco).
# Die beiden Herz-Umrisse sind die Originalpfade der Vorlage, ebenso die sechs
# Striche, die beim Anhaken nach außen stieben.

from __future__ import annotations

from PyQt6.QtCore import (
    QByteArray, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSize, Qt,
    pyqtProperty
)
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QCheckBox

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    '<path fill="{color}" d="{path}"/></svg>'
)

# Umriss und volle Fläche, beide aus der Vorlage übernommen.
_OUTLINE = (
    "M17.5,1.917a6.4,6.4,0,0,0-5.5,3.3,6.4,6.4,0,0,0-5.5-3.3A6.8,6.8,0,0,0,0,"
    "8.967c0,4.547,4.786,9.513,8.8,12.88a4.974,4.974,0,0,0,6.4,0C19.214,18.48,"
    "24,13.514,24,8.967A6.8,6.8,0,0,0,17.5,1.917Zm-3.585,18.4a2.973,2.973,0,0,"
    "1-3.83,0C4.947,16.006,2,11.87,2,8.967a4.8,4.8,0,0,1,4.5-5.05A4.8,4.8,0,0,"
    "1,11,8.967a1,1,0,0,0,2,0,4.8,4.8,0,0,1,4.5-5.05A4.8,4.8,0,0,1,22,8.967C22,"
    "11.87,19.053,16.006,13.915,20.313Z"
)
_FILLED = (
    "M17.5,1.917a6.4,6.4,0,0,0-5.5,3.3,6.4,6.4,0,0,0-5.5-3.3A6.8,6.8,0,0,0,0,"
    "8.967c0,4.547,4.786,9.513,8.8,12.88a4.974,4.974,0,0,0,6.4,0C19.214,18.48,"
    "24,13.514,24,8.967A6.8,6.8,0,0,0,17.5,1.917Z"
)

# Ein Zeichner je Pfad und Farbe — das Aufbauen lohnt sich nur einmal.
_RENDERERS: dict[tuple[str, str], QSvgRenderer] = {}


def _renderer(path: str, color: QColor) -> QSvgRenderer:
    key = (path, color.name())
    found = _RENDERERS.get(key)
    if found is None:
        markup = _SVG.format(color=color.name(), path=path)
        found = QSvgRenderer(QByteArray(markup.encode("utf-8")))
        _RENDERERS[key] = found
    return found


class HeartCheckBox(QCheckBox):
    """Herz zum Anhaken: es füllt sich mit einem Hüpfer, Funken stieben weg.

    Nach außen bleibt es eine QCheckBox: `isChecked()`, `setChecked()` und das
    `toggled`-Signal funktionieren unverändert.

    Angehakt fährt das volle Herz in einem Sprung heraus (0 → 1.2 → 1) und
    leuchtet dabei kurz auf, während sechs Striche nach außen stieben und
    verblassen. Beim Abhaken verschwindet es sofort und nur der Umriss bleibt —
    die Vorlage blendet dort ebenfalls nicht aus, sondern schaltet hart um.
    """

    HEART      = 50         # Kantenlänge des Herzens
    SPARK_ROOM = 20         # Platz je Seite, in den die Funken stieben
    SPARK_END  = 1.4        # Größe, auf die die Funken wachsen
    GAP        = 8          # Abstand zwischen Herz und Beschriftung
    POP_MS     = 1000       # Dauer des Herz-Sprungs
    SPARK_MS   = 500        # Dauer der Funken
    COLOR      = "#ff5b89"  # rgb(255, 91, 137)

    # Die sechs Striche der Vorlage, in deren 100x100-Kasten um das Herz herum.
    SPARKS = (
        ((10, 10), (20, 20)),
        ((10, 50), (20, 50)),
        ((20, 80), (30, 70)),
        ((90, 10), (80, 20)),
        ((90, 50), (80, 50)),
        ((80, 80), (70, 70)),
    )

    def __init__(self, text: str = "", parent=None) -> None:
        self._pop = 0.0      # Größe des vollen Herzens, 0 = nicht da
        self._glow = 0.0     # kurzes Aufleuchten, 0..1
        self._spark = 0.0    # Fortschritt der Funken, 0..1
        super().__init__(text, parent)

        self._color = QColor(self.COLOR)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._pop_anim = self._keyframed(b"pop", self.POP_MS, {
            0.0: 0.0, 0.25: 1.2, 0.5: 1.0, 1.0: 1.0,
        })
        self._glow_anim = self._keyframed(b"glow", self.POP_MS, {
            0.0: 0.0, 0.25: 0.0, 0.5: 1.0, 1.0: 0.0,
        })
        self._spark_anim = self._keyframed(b"spark", self.SPARK_MS, {
            0.0: 0.0, 1.0: 1.0,
        })

        self.toggled.connect(self._on_toggled)
        self._pop = 1.0 if self.isChecked() else 0.0

    def _keyframed(
        self, name: bytes, duration: int, keys: dict[float, float]
    ) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(duration)
        # Den Schwung tragen die Zwischenwerte, deshalb bleibt die Kurve linear.
        anim.setEasingCurve(QEasingCurve.Type.Linear)
        for at, value in keys.items():
            anim.setKeyValueAt(at, value)
        return anim

    # ==============================
    # Farbe
    # ==============================

    def heart_color(self) -> QColor:
        return QColor(self._color)

    def setHeartColor(self, color) -> None:
        """Entspricht `--heart-color` in der Vorlage."""
        self._color = QColor(color)
        self.update()

    # ==============================
    # Geometrie
    # ==============================

    def _room(self) -> float:
        """Rand um das Herz, in den die Funken hinausdürfen."""
        return min(float(self.SPARK_ROOM), self.height() / 4.0)

    def _heart_rect(self) -> QRectF:
        """Das Herz füllt die Höhe — wird das Kästchen kleiner, wird es mit."""
        room = self._room()
        side = max(self.height() - 2 * room, 1.0)
        return QRectF(room, room, side, side)

    def sizeHint(self) -> QSize:
        side = self.HEART + 2 * self.SPARK_ROOM
        width = side
        if self.text():
            width += self.GAP + self.fontMetrics().horizontalAdvance(self.text())
        return QSize(width, side)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def hitButton(self, pos) -> bool:
        # Auch ein Klick auf die Beschriftung hakt an.
        return self.rect().contains(pos)

    # ==============================
    # Animierte Eigenschaften
    # ==============================

    @pyqtProperty(float)
    def pop(self) -> float:
        return self._pop

    @pop.setter
    def pop(self, value: float) -> None:
        self._pop = value
        self.update()

    @pyqtProperty(float)
    def glow(self) -> float:
        return self._glow

    @glow.setter
    def glow(self, value: float) -> None:
        self._glow = value
        self.update()

    @pyqtProperty(float)
    def spark(self) -> float:
        return self._spark

    @spark.setter
    def spark(self, value: float) -> None:
        self._spark = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        for anim in (self._pop_anim, self._glow_anim, self._spark_anim):
            anim.stop()

        if not checked:
            # Die Vorlage nimmt volles Herz und Funken hart weg (display: none).
            self._pop = self._glow = self._spark = 0.0
            self.update()
            return

        for anim in (self._pop_anim, self._glow_anim, self._spark_anim):
            anim.start()

    # ==============================
    # Darstellung
    # ==============================

    def _lit(self, amount: float) -> QColor:
        """Die Herzfarbe, kurz aufgehellt — das `brightness(1.5)` der Vorlage."""
        if amount <= 0.0:
            return QColor(self._color)
        return QColor(self._color).lighter(int(100 + 50 * amount))

    @staticmethod
    def _scaled(rect: QRectF, factor: float) -> QRectF:
        box = QRectF(0, 0, rect.width() * factor, rect.height() * factor)
        box.moveCenter(rect.center())
        return box

    def _draw_sparks(self, painter: QPainter, heart: QRectF) -> None:
        progress = max(0.0, min(1.0, self._spark))
        if progress <= 0.0 or progress >= 1.0:
            return

        # Bis zur Hälfte voll sichtbar, danach ausblenden; dazwischen kurz heller.
        opacity = 1.0 if progress <= 0.5 else 1.0 - (progress - 0.5) / 0.5
        amount = 1.0 - abs(progress - 0.5) / 0.5

        side = heart.width()
        center = heart.center()
        # Der Funkenkasten der Vorlage ist doppelt so groß wie das Herz. So weit
        # reicht der freie Rand selten, deshalb rücken die Funken so weit
        # zusammen, dass sie am Ende gerade noch ins Widget passen.
        reach = 0.8 * side * self.SPARK_END
        squeeze = min(1.0, (side / 2 + self._room()) / reach) if reach else 1.0
        unit = side / 50.0 * squeeze * self.SPARK_END * progress

        pen = QPen(self._lit(amount), max(2.0 * side / 50.0, 1.0))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        painter.save()
        painter.setOpacity(opacity)
        painter.setPen(pen)
        for (x1, y1), (x2, y2) in self.SPARKS:
            painter.drawLine(
                QPointF(center.x() + (x1 - 50) * unit, center.y() + (y1 - 50) * unit),
                QPointF(center.x() + (x2 - 50) * unit, center.y() + (y2 - 50) * unit),
            )
        painter.restore()

    def paintEvent(self, event) -> None:
        heart = self._heart_rect()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        _renderer(_OUTLINE, self._color).render(painter, heart)

        pop = max(0.0, self._pop)
        if pop > 0.0:
            _renderer(_FILLED, self._lit(self._glow)).render(
                painter, self._scaled(heart, pop)
            )

        self._draw_sparks(painter, heart)

        if self.text():
            group = (
                QPalette.ColorGroup.Normal if self.isEnabled()
                else QPalette.ColorGroup.Disabled
            )
            painter.setPen(
                QPen(self.palette().color(group, QPalette.ColorRole.WindowText))
            )
            left = heart.right() + self.GAP
            painter.drawText(
                QRectF(left, 0, max(self.width() - left, 0), self.height()),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.text(),
            )

        painter.end()
