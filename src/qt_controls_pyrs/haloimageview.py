# haloimageview.py
#
# Bildvorschau im Stil der Halo-Widgets: derselbe feine Rahmen wie bei der
# HaloPromptBox, der unter der Maus hell wird und innen aufglimmt. Ohne Bild
# steht ein Platzhaltertext in der Mitte; ein Bild wird passend verkleinert
# und mittig gezeigt. Ein Klick meldet `clicked`.
#
# Während eine Aufgabe läuft (start_busy / stop_busy), liegt über dem Bild
# eine weichgezeichnete Kopie, darauf pulsieren drei Kopien eines Symbols —
# etwa die Sterne beim Warten auf ein generiertes Bild. Die Animation wird
# hier mitgezeichnet, unter Rahmen und Schein, damit sie den Rahmen nie
# zudeckt.

from __future__ import annotations

import math

from PyQt6.QtCore import (
    QEasingCurve, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty, pyqtSignal as Signal
)
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PyQt6.QtWidgets import QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene, QWidget

from .buttons.hoverbuttons import _crisp, _faded, _glow, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class HaloImageView(QWidget):
    """Bildvorschau mit Halo-Rahmen, Platzhaltertext und Warte-Animation.

    Wie ein `QLabel` für Bilder: `setPixmap()`, `pixmap()`, `setText()` und
    `clear()`. Das Bild wird mit gleichem Seitenverhältnis in den Rahmen
    eingepasst — das Fenster muss es nicht selbst verkleinern.

    `start_busy()` legt die Warte-Animation darüber, `stop_busy()` nimmt sie
    weg. Das Symbol dafür gibt das Programm mit `setBusyIcon()` vor; ohne
    Symbol bleibt es beim weichgezeichneten Bild.
    """

    # Meldet einen Klick mit der linken Maustaste.
    clicked = Signal()

    # --- Rahmen: dieselben Werte wie bei der HaloPromptBox -----------------
    ROOM          = 0       # Rand links und rechts außerhalb des Rahmens
    ROOM_Y        = 0       # Rand oben und unten
    RADIUS        = 0       # Eckenradius des Rahmens
    OUTLINE_ALPHA = 0.5     # Deckkraft des Rahmens in Ruhe
    INNER_GLOW    = 20      # innerer Schein, wenn die Maus darauf steht
    HOVER_MS      = 1250    # wie die Halo-Knöpfe: schnell hin, lang aus

    # --- Inhalt ---------------------------------------------------------------
    PLACEHOLDER_PX = 40     # Schriftgröße des Platzhaltertextes in Pixeln

    # --- Warte-Animation ------------------------------------------------------
    BUSY_BLUR        = 15      # Weichzeichnung des Bildes darunter
    BUSY_FILL_ALPHA  = 50      # ohne Bild: helle Fläche, Deckkraft 0..255
    BUSY_INTERVAL_MS = 30      # Bildtakt
    BUSY_SPEED       = 0.1     # Phasenschritt je Takt
    BUSY_SCALE_BASE  = 0.8     # Mindestgröße der Symbole ...
    BUSY_SCALE_SWING = 0.2     # ... und ihre Schwingbreite (BASE ± SWING)
    # Drei Symbole: Größe in Pixeln, Versatz zur Mitte, Phasenversatz
    BUSY_ICONS = (
        {"size": 120, "dx": -10, "dy":   0, "phase": 0.0},
        {"size":  30, "dx":  60, "dy":  20, "phase": 0.5},
        {"size":  60, "dx":  45, "dy": -30, "phase": 1.0},
    )

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._text = text
        self._pixmap = QPixmap()          # das Bild in Originalgröße
        self._scaled = QPixmap()          # ... eingepasst in den Rahmen
        self._bright = 0.0                # 0 = Ruhe, 1 = Maus darauf

        self._busy = False
        self._busy_icon = QPixmap()
        self._busy_background = QPixmap() # weichgezeichnetes Bild während des Wartens
        self._busy_phase = 0.0

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._bright_anim = QPropertyAnimation(self, b"bright", self)
        self._bright_anim.setDuration(self.HOVER_MS)
        self._bright_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

        self._busy_timer = QTimer(self)
        self._busy_timer.setInterval(self.BUSY_INTERVAL_MS)
        self._busy_timer.timeout.connect(self._advance_busy)

    # ==============================
    # Inhalt (wie bei QLabel)
    # ==============================

    def text(self) -> str:
        return self._text

    def setText(self, text: str) -> None:
        self._text = text
        self.update()

    def pixmap(self) -> QPixmap:
        return self._pixmap

    def setPixmap(self, pixmap: QPixmap) -> None:
        self._pixmap = QPixmap(pixmap)
        self._rescale()
        if self._busy:
            self._busy_background = self._blurred(self._scaled)
        self.update()

    def clear(self) -> None:
        """Bild und Text entfernen."""
        self._text = ""
        self.setPixmap(QPixmap())

    # ==============================
    # Warte-Animation
    # ==============================

    def setBusyIcon(self, icon: QPixmap) -> None:
        """Das Symbol, das während des Wartens pulsiert."""
        self._busy_icon = QPixmap(icon)
        self.update()

    def is_busy(self) -> bool:
        return self._busy

    def start_busy(self) -> None:
        self._busy = True
        self._busy_background = self._blurred(self._scaled)
        self._busy_timer.start()
        self.update()

    def stop_busy(self) -> None:
        self._busy = False
        self._busy_timer.stop()
        self._busy_background = QPixmap()
        self.update()

    def _advance_busy(self) -> None:
        self._busy_phase = (self._busy_phase + self.BUSY_SPEED) % (2 * math.pi)
        self.update()

    def _blurred(self, pixmap: QPixmap) -> QPixmap:
        """Weichgezeichnete Kopie; ein leeres Bild bleibt leer."""
        if pixmap.isNull():
            return QPixmap()

        effect = QGraphicsBlurEffect()
        effect.setBlurRadius(self.BUSY_BLUR)
        item = QGraphicsPixmapItem(pixmap)
        item.setGraphicsEffect(effect)
        scene = QGraphicsScene()
        scene.addItem(item)

        result = QPixmap(pixmap.size())
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)
        scene.render(painter)
        painter.end()
        return result

    # ==============================
    # Heller Rahmen unter der Maus
    # ==============================

    @pyqtProperty(float)
    def bright(self) -> float:
        return self._bright

    @bright.setter
    def bright(self, value: float) -> None:
        self._bright = value
        self.update()

    def _fade_bright(self, target: float) -> None:
        self._bright_anim.stop()
        self._bright_anim.setStartValue(self._bright)
        self._bright_anim.setEndValue(target)
        self._bright_anim.start()

    # ==============================
    # Ereignisse
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._fade_bright(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._fade_bright(0.0)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        # Annehmen, sonst reicht Qt den Klick ans Elternwidget weiter.
        if event.button() == Qt.MouseButton.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._rescale()
        if self._busy:
            self._busy_background = self._blurred(self._scaled)

    def hideEvent(self, event) -> None:
        # Ohne Anzeige kein Bildtakt; showEvent nimmt ihn wieder auf.
        self._busy_timer.stop()
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._busy:
            self._busy_timer.start()

    # ==============================
    # Darstellung
    # ==============================

    def _frame_rect(self) -> QRectF:
        """Die sichtbare Fläche: das Widget ohne den Rand außerhalb des Rahmens."""
        return QRectF(self.rect().adjusted(self.ROOM, self.ROOM_Y, -self.ROOM, -self.ROOM_Y))

    def _content_rect(self) -> QRectF:
        """Innerhalb des Rahmenstrichs: hier liegen Bild und Animation."""
        return self._frame_rect().adjusted(1.0, 1.0, -1.0, -1.0)

    def _rescale(self) -> None:
        if self._pixmap.isNull():
            self._scaled = QPixmap()
            return
        area = self._content_rect().size().toSize()
        if area.width() <= 0 or area.height() <= 0:
            self._scaled = QPixmap()
            return
        self._scaled = self._pixmap.scaled(
            area, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        content = self._content_rect()
        painter.save()
        painter.setClipRect(content)
        if self._busy:
            self._paint_busy(painter, content)
        elif not self._scaled.isNull():
            self._paint_centered(painter, content, self._scaled)
        elif self._text:
            self._paint_text(painter, content)
        painter.restore()

        self._paint_frame(painter)
        painter.end()

    @staticmethod
    def _paint_centered(painter: QPainter, area: QRectF, pixmap: QPixmap) -> None:
        x = area.x() + (area.width() - pixmap.width()) / 2.0
        y = area.y() + (area.height() - pixmap.height()) / 2.0
        painter.drawPixmap(round(x), round(y), pixmap)

    def _paint_text(self, painter: QPainter, area: QRectF) -> None:
        font = QFont(self.font())
        font.setPixelSize(self.PLACEHOLDER_PX)
        painter.setFont(font)
        painter.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        painter.drawText(area, Qt.AlignmentFlag.AlignCenter, self._text)

    def _paint_busy(self, painter: QPainter, area: QRectF) -> None:
        # Unten das weichgezeichnete Bild, so vergrößert, dass es die Fläche
        # ganz ausfüllt; ohne Bild eine helle Fläche.
        if self._busy_background.isNull():
            painter.fillRect(area, QColor(255, 255, 255, self.BUSY_FILL_ALPHA))
        else:
            filled = self._busy_background.scaled(
                area.size().toSize(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._paint_centered(painter, area, filled)

        if self._busy_icon.isNull():
            return

        center_x = area.center().x()
        center_y = area.center().y()
        for icon in self.BUSY_ICONS:
            scale = self.BUSY_SCALE_BASE + self.BUSY_SCALE_SWING * math.sin(
                self._busy_phase + icon["phase"]
            )
            size = max(1, int(icon["size"] * scale))
            pixmap = self._busy_icon.scaled(
                size, size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            painter.drawPixmap(
                round(center_x + icon["dx"] - pixmap.width() / 2.0),
                round(center_y + icon["dy"] - pixmap.height() / 2.0),
                pixmap,
            )

    def _paint_frame(self, painter: QPainter) -> None:
        """Rahmen und innerer Schein — wie bei der HaloPromptBox."""
        frame = self._frame_rect()
        ink = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText)
        bright = _clamp(self._bright)
        radius = float(self.RADIUS)

        if bright > 0.0:
            _glow(painter, frame, _faded(ink, 0.5 * bright), self.INNER_GLOW,
                  inside=True, radius=radius)

        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * bright
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(frame, 1.0), max(radius - 0.5, 0.0))
