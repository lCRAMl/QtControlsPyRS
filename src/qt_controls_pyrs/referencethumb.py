# referencethumb.py
#
# Bild-Miniatur im Stil einer Karte, deren Rahmen dort aufleuchtet, wo der
# Mauszeiger steht — nachgebaut nach dem bekannten CSS-Muster mit dem
# `radial-gradient`, der dem Zeiger folgt. Liegt ein Bild darin, wandert das
# Leuchten auf den Rahmen; darüber legt sich unter der Maus eine halbdurch-
# sichtige Decke mit einem runden X-Knopf.

from __future__ import annotations

import logging

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QPointF, QPropertyAnimation, QRectF, QSizeF,
    Qt, pyqtProperty, pyqtSignal as Signal
)
from PyQt6.QtGui import (
    QBrush, QColor, QCursor, QPainter, QPainterPath, QPalette, QPen, QPixmap,
    QRadialGradient
)
from PyQt6.QtWidgets import QFileDialog, QLabel, QPushButton, QWidget

from .imgbb import ImgBBClient, ImgBBUploadWorker

logger = logging.getLogger(__name__)


def _faded(color: QColor, alpha: float) -> QColor:
    """Dieselbe Farbe mit anderer Deckkraft (0..1)."""
    out = QColor(color)
    out.setAlpha(max(0, min(255, round(alpha * 255))))
    return out


# ---------------------------------------------------------------------------
# Hilfklassen
# ---------------------------------------------------------------------------

class ClickableLabel(QLabel):
    """QLabel, das Mausklicks als Qt-konformes Signal weitergibt."""
    clicked = Signal()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class CloseButton(QPushButton):
    """Runder X-Knopf, der sich beim Erscheinen einmal ausdreht.

    `spin_up()` dreht ihn zwei Umdrehungen weit: schnell los und dann immer
    langsamer, bis er still steht. Unter der Maus färbt er sich rot ein, damit
    klar ist, dass er etwas wegnimmt.
    """

    SIZE       = 34
    RING_W     = 1.4
    ARM        = 0.30     # Länge der X-Arme, Anteil der Größe
    SPIN_MS    = 1100
    SPIN_TURNS = 2
    DANGER     = "#dc3232"

    def __init__(self, parent: QWidget | None = None) -> None:
        self._spin = 0.0
        self._fade = 1.0
        super().__init__(parent)

        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("Bild entfernen")

        self._spin_anim = QPropertyAnimation(self, b"spin", self)
        self._spin_anim.setDuration(self.SPIN_MS)
        # Schnell anlaufen, weich auslaufen.
        self._spin_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

    def spin_up(self) -> None:
        """Dreht einmal durch und kommt zum Stillstand."""
        self._spin_anim.stop()
        self._spin_anim.setStartValue(0.0)
        self._spin_anim.setEndValue(360.0 * self.SPIN_TURNS)
        self._spin_anim.start()

    @pyqtProperty(float)
    def spin(self) -> float:
        return self._spin

    @spin.setter
    def spin(self, value: float) -> None:
        self._spin = value
        self.update()

    @pyqtProperty(float)
    def fade(self) -> float:
        return self._fade

    @fade.setter
    def fade(self, value: float) -> None:
        self._fade = value
        self.update()

    def paintEvent(self, event) -> None:
        if self._fade <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(max(0.0, min(1.0, self._fade)))

        ink = self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )
        warm = self.underMouse() and self.isEnabled()

        disc = QColor(self.DANGER) if warm else QColor(0, 0, 0)
        disc.setAlpha(225 if warm else 150)
        if self.isDown():
            disc = disc.darker(115)

        rect = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        painter.setBrush(QBrush(disc))
        painter.setPen(QPen(_faded(ink, 0.85 if warm else 0.45), self.RING_W))
        painter.drawEllipse(rect)

        painter.translate(rect.center())
        painter.rotate(self._spin)

        arm = self.SIZE * self.ARM / 2
        pen = QPen(_faded(ink, 1.0 if warm else 0.85), 2.0)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(QPointF(-arm, -arm), QPointF(arm, arm))
        painter.drawLine(QPointF(arm, -arm), QPointF(-arm, arm))

        painter.end()


class ThumbOverlay(QWidget):
    """Halbdurchsichtige Decke über einer Miniatur, mit rundem X in der Mitte.

    `reveal()` blendet sie auf und lässt das X einmal ausdrehen, `conceal()`
    nimmt sie wieder weg. Ein Klick neben das X meldet sich als `clicked` —
    die Miniatur öffnet damit den Dateidialog, tauscht das Bild also aus.
    """

    clicked = Signal()

    DIM     = 0.55    # Deckkraft der Decke
    FADE_MS = 180
    RADIUS  = 8

    def __init__(self, parent: QWidget | None = None) -> None:
        self._fade = 0.0
        super().__init__(parent)

        self.setMouseTracking(True)
        self.button = CloseButton(self)
        self.button.fade = 0.0

        # Ein QGraphicsOpacityEffect wäre der kürzere Weg, aber `render()`
        # überspringt Kinder mit Effekt — dann fehlte die Decke auf jedem
        # Bildschirmfoto. Decke und Knopf blenden sich deshalb selbst aus.
        self._anim = QPropertyAnimation(self, b"fade", self)
        self._anim.setDuration(self.FADE_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._anim.finished.connect(self._on_fade_finished)

        self.hide()

    @pyqtProperty(float)
    def fade(self) -> float:
        return self._fade

    @fade.setter
    def fade(self, value: float) -> None:
        self._fade = value
        self.button.fade = value
        self.update()

    # ------------------------------------------------------------------
    # Auf- und Zudecken
    # ------------------------------------------------------------------

    def reveal(self) -> None:
        if not self.isVisible():
            self.show()
            self.raise_()
        self.button.spin_up()
        self._animate(1.0)

    def conceal(self) -> None:
        if self.isVisible():
            self._animate(0.0)

    def _animate(self, target: float) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._fade)
        self._anim.setEndValue(target)
        self._anim.start()

    def _on_fade_finished(self) -> None:
        # Unsichtbar allein genügt nicht — sonst fängt sie weiter Mausklicks.
        if self._fade <= 0.0:
            self.hide()

    # ------------------------------------------------------------------
    # Ereignisse
    # ------------------------------------------------------------------

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.button.move(
            (self.width() - self.button.width()) // 2,
            (self.height() - self.button.height()) // 2,
        )

    def _thumb(self) -> QWidget | None:
        """Die Miniatur darunter — sie führt Licht und Decke."""
        parent = self.parentWidget()
        return parent if hasattr(parent, "pointer_moved") else None

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        # Die Decke liegt über der Karte, sonst bekäme die keine Bewegung mehr.
        thumb = self._thumb()
        if thumb is not None:
            thumb.pointer_moved(event.globalPosition())

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        thumb = self._thumb()
        if thumb is not None:
            thumb.pointer_left()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event) -> None:
        if self._fade <= 0.0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(max(0.0, min(1.0, self._fade)))

        shape = QPainterPath()
        shape.addRoundedRect(QRectF(self.rect()), self.RADIUS, self.RADIUS)
        painter.fillPath(shape, QBrush(_faded(QColor(0, 0, 0), self.DIM)))

        painter.end()


# ---------------------------------------------------------------------------
# Hauptklasse
# ---------------------------------------------------------------------------

class ReferenceThumb(QWidget):
    """Bild-Miniatur zum Anklicken, mit Upload-Fortschritt und Löschknopf.

    Leer ist sie eine dunkle Karte, deren feiner Rahmen dort aufleuchtet, wo
    der Mauszeiger steht; innen liegt dann zusätzlich ein weicher Schein. Zieht
    der Zeiger über eine Nachbarin, leuchten alle mit — wie im Vorbild, wo die
    Karten gemeinsam auf die Maus reagieren. Unter der Maus schrumpft die Karte
    eine Spur.

    Liegt ein Bild darin, bleibt das Leuchten auf dem Rahmen, und unter der
    Maus legt sich eine halbdurchsichtige Decke mit einem runden X darüber:
    das X entfernt das Bild, ein Klick daneben tauscht es aus.
    """

    cleared = Signal(int)
    uploaded = Signal(int, str)
    upload_failed = Signal(int, str)

    # --- Layout-Konstanten ---
    THUMB_SIZE = 100
    WIDGET_HEIGHT = 110
    PROGRESS_HEIGHT = 2
    RADIUS = 8              # Eckenradius der Karte

    # --- Bewegung ---
    HOVER_SCALE = 0.98      # so weit schrumpft die Karte unter der Maus
    HOVER_MS = 150
    GLOW_MS = 220

    # --- Style ---
    GLOW_COLOR = "#5a8cff"  # Farbe des Scheins
    GLOW_REACH = 1.5        # Reichweite des Scheins, Vielfaches der Kartenseite
    INNER_REACH = 3.0       # Reichweite des Scheins innen (nur wenn leer)
    INNER_ALPHA = 0.18
    RIM_ALPHA = 0.16        # ruhiger Rahmen, wenn der Zeiger weit weg ist
    _COLOR_PROGRESS = "#4caf50"
    _COLOR_UPLOADING = "#00bfff"
    _COLOR_ERROR = "#ff0000"

    def __init__(self, index: int, imgbb_api_key: str, parent: QWidget | None = None) -> None:
        self._hover = 0.0
        self._glow = 0.0
        super().__init__(parent)

        self.index = index
        self.imgbb_api_key = imgbb_api_key
        self.upload_url: str | None = None

        self._worker: ImgBBUploadWorker | None = None
        self._uploading = False
        self._pixmap: QPixmap | None = None
        self._message = ""
        self._glow_color = QColor(self.GLOW_COLOR)
        self._light = QPointF(self.THUMB_SIZE / 2, self.THUMB_SIZE / 2)

        self.setFixedSize(self.THUMB_SIZE, self.WIDGET_HEIGHT)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()

        self._hover_anim = self._animation(b"hover", self.HOVER_MS)
        self._glow_anim = self._animation(b"glow", self.GLOW_MS)

    def _animation(self, name: bytes, duration: int) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(duration)
        anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
        return anim

    # ------------------------------------------------------------------
    # UI-Aufbau
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # Fortschrittsbalken unter der Karte
        self.progress = QLabel(self)
        self.progress.setGeometry(0, self.THUMB_SIZE, 0, self.PROGRESS_HEIGHT)
        self.progress.setStyleSheet(f"background-color: {self._COLOR_PROGRESS};")

        # Decke mit dem X, genau über der Karte
        self.overlay = ThumbOverlay(self)
        self.overlay.RADIUS = self.RADIUS
        self.overlay.setGeometry(0, 0, self.THUMB_SIZE, self.THUMB_SIZE)
        self.overlay.button.clicked.connect(self.clear)
        self.overlay.clicked.connect(self.load_image_dialog)

    # ------------------------------------------------------------------
    # Öffentliche API
    # ------------------------------------------------------------------

    def set_image(self, path: str) -> None:
        """Lädt ein Bild aus einem Dateipfad und startet den Upload."""
        if self._uploading:
            self._cancel_worker()

        self._pixmap = QPixmap(path).scaled(
            self.THUMB_SIZE, self.THUMB_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._message = ""
        self.update()
        # Steht die Maus schon darauf, deckt sie sich gleich auf — das X dreht
        # sich dann direkt nach dem Laden aus.
        if self.underMouse() or self.overlay.underMouse():
            self.overlay.reveal()
        self._upload_to_imgbb(path)

    def clear(self) -> None:
        """Setzt das Thumbnail zurück und bricht einen laufenden Upload ab."""
        self._cancel_worker()
        self._pixmap = None
        self._message = ""
        self._reset_progress()
        self.overlay.conceal()
        self.upload_url = None
        self.update()
        self.cleared.emit(self.index)

    def has_image(self) -> bool:
        return self._pixmap is not None and not self._pixmap.isNull()

    def pixmap(self) -> QPixmap | None:
        """Die angezeigte Vorschau, oder nichts."""
        return self._pixmap

    def message(self) -> str:
        """Der Text, der gerade statt eines Bildes in der Karte steht."""
        return self._message

    def set_progress(self, value: float, color: str = _COLOR_PROGRESS) -> None:
        """Setzt den Fortschrittsbalken. value wird auf [0.0, 1.0] geclampt."""
        value = max(0.0, min(1.0, value))
        width = int(self.THUMB_SIZE * value)
        self.progress.setGeometry(0, self.THUMB_SIZE, width, self.PROGRESS_HEIGHT)
        self.progress.setStyleSheet(f"background-color:{color};")

    def glow_color(self) -> QColor:
        return QColor(self._glow_color)

    def setGlowColor(self, color) -> None:
        """Die Farbe, in der Rahmen und Innenschein leuchten."""
        self._glow_color = QColor(color)
        self.update()

    # ------------------------------------------------------------------
    # Upload-Logik
    # ------------------------------------------------------------------

    def load_image_dialog(self) -> None:
        file, _ = QFileDialog.getOpenFileName(
            self, "Bild auswählen", "", "Images (*.png *.jpg *.jpeg)"
        )
        if file:
            self.set_image(file)

    def _upload_to_imgbb(self, path: str) -> None:
        if not self.imgbb_api_key:
            logger.debug("Kein ImgBB-API-Key gesetzt – Upload wird übersprungen.")
            return

        self._uploading = True
        client = ImgBBClient(self.imgbb_api_key)
        self._worker = ImgBBUploadWorker(client, path)
        self._worker.progress.connect(lambda v: self.set_progress(v, self._COLOR_UPLOADING))
        self._worker.finished.connect(self._on_upload_finished)
        self._worker.error.connect(self._on_upload_failed)
        self._worker.start()

    def _cancel_worker(self) -> None:
        """Trennt Signals des laufenden Workers, damit keine veralteten Callbacks feuern."""
        if self._worker is not None:
            try:
                self._worker.progress.disconnect()
                self._worker.finished.disconnect()
                self._worker.error.disconnect()
            except RuntimeError:
                pass  # bereits getrennt
            self._worker = None
        self._uploading = False

    def _reset_progress(self) -> None:
        self.progress.setGeometry(0, self.THUMB_SIZE, 0, self.PROGRESS_HEIGHT)
        self.progress.setStyleSheet(f"background-color: {self._COLOR_PROGRESS};")

    # ------------------------------------------------------------------
    # Upload-Callbacks
    # ------------------------------------------------------------------

    def _on_upload_finished(self, url: str) -> None:
        self._uploading = False
        self.upload_url = url
        self.set_progress(1.0, self._COLOR_PROGRESS)
        self.uploaded.emit(self.index, url)

    def _on_upload_failed(self, error: str) -> None:
        self._uploading = False
        self.set_progress(1.0, self._COLOR_ERROR)
        logger.error("Upload Thumb %d fehlgeschlagen: %s", self.index, error)
        self._message = "Upload\nfailed"
        self.update()
        self.upload_failed.emit(self.index, error)

    # ------------------------------------------------------------------
    # Mauszeiger: Licht setzen, Decke auf und zu
    # ------------------------------------------------------------------

    @pyqtProperty(float)
    def hover(self) -> float:
        return self._hover

    @hover.setter
    def hover(self, value: float) -> None:
        self._hover = value
        self.update()

    @pyqtProperty(float)
    def glow(self) -> float:
        return self._glow

    @glow.setter
    def glow(self, value: float) -> None:
        self._glow = value
        self.update()

    def _animate(self, anim: QPropertyAnimation, current: float, target: float) -> None:
        running = anim.state() == QAbstractAnimation.State.Running
        if running and anim.endValue() == target:
            return
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    def _pointer_inside(self) -> bool:
        """Steht der Zeiger auf der Karte — die Decke darüber zählt mit dazu?"""
        if self.underMouse() or self.overlay.underMouse():
            return True
        # Beim Wechsel auf ein Kind ist `underMouse` noch nicht gesetzt, deshalb
        # zusätzlich die Lage prüfen.
        return self.rect().contains(self.mapFromGlobal(QCursor.pos()))

    def _family(self) -> list["ReferenceThumb"]:
        """Alle Miniaturen nebenan — sie leuchten gemeinsam auf."""
        parent = self.parentWidget()
        if parent is None:
            return [self]
        family = parent.findChildren(ReferenceThumb)
        return family if self in family else [*family, self]

    def _aim(self, global_pos: QPointF) -> None:
        """Setzt das Licht auf die Stelle, an der der Zeiger steht."""
        self._light = QPointF(self.mapFromGlobal(global_pos.toPoint()))
        self._animate(self._glow_anim, self._glow, 1.0)
        self.update()

    def _dim(self) -> None:
        self._animate(self._glow_anim, self._glow, 0.0)

    def pointer_moved(self, global_pos: QPointF) -> None:
        """Wird auch von der Decke gerufen, die ja über der Karte liegt."""
        for thumb in self._family():
            thumb._aim(global_pos)

    def pointer_entered(self) -> None:
        self._animate(self._hover_anim, self._hover, 1.0)
        if self.has_image():
            self.overlay.reveal()

    def pointer_left(self) -> None:
        # Der Weg auf die Decke zählt nicht als Verlassen — sie gehört dazu.
        if self._pointer_inside():
            return
        self._animate(self._hover_anim, self._hover, 0.0)
        self.overlay.conceal()
        for thumb in self._family():
            thumb._dim()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self.pointer_entered()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self.pointer_left()

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        self.pointer_moved(event.globalPosition())

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.load_image_dialog()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if not self.isEnabled():
            self.overlay.conceal()

    # ------------------------------------------------------------------
    # Darstellung
    # ------------------------------------------------------------------

    def _card_rect(self) -> QRectF:
        """Die Karte — unter der Maus eine Spur kleiner, wie im Vorbild."""
        card = QRectF(0, 0, self.THUMB_SIZE, self.THUMB_SIZE)
        shrink = self.THUMB_SIZE * (1.0 - self.HOVER_SCALE) / 2 * max(0.0, min(1.0, self._hover))
        return card.adjusted(shrink, shrink, -shrink, -shrink)

    def _spotlight(self, card: QRectF, reach: float, alpha: float) -> QRadialGradient:
        """Der Schein, der dem Zeiger folgt."""
        radius = max(card.width(), card.height()) * reach
        gradient = QRadialGradient(self._light, radius)
        gradient.setColorAt(0.0, _faded(self._glow_color, alpha))
        gradient.setColorAt(1.0, _faded(self._glow_color, 0.0))
        return gradient

    def _rounded(self, rect: QRectF, radius: float) -> QPainterPath:
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        palette = self.palette()
        ink = palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        glow = max(0.0, min(1.0, self._glow))

        card = self._card_rect()
        shape = self._rounded(card, self.RADIUS)

        # Der Rahmen ist die ganze Fläche — gleich darauf deckt sie der Inhalt
        # bis auf einen Streifen von einem Pixel wieder zu.
        painter.fillPath(shape, QBrush(_faded(ink, self.RIM_ALPHA)))
        if glow > 0.0:
            painter.fillPath(shape, QBrush(self._spotlight(card, self.GLOW_REACH, glow)))

        inner = card.adjusted(1, 1, -1, -1)
        inner_shape = self._rounded(inner, max(self.RADIUS - 1, 0))
        painter.fillPath(inner_shape, QBrush(palette.color(QPalette.ColorRole.Base)))

        if self.has_image():
            painter.save()
            painter.setClipPath(inner_shape)
            size = QSizeF(self._pixmap.size().scaled(
                inner.size().toSize(), Qt.AspectRatioMode.KeepAspectRatio
            ))
            target = QRectF(QPointF(0, 0), size)
            target.moveCenter(inner.center())
            painter.drawPixmap(target, self._pixmap, QRectF(self._pixmap.rect()))
            painter.restore()
        else:
            # Leer: der Schein liegt auch innen, dazu ein Pluszeichen.
            if glow > 0.0:
                painter.fillPath(
                    inner_shape,
                    QBrush(self._spotlight(card, self.INNER_REACH, self.INNER_ALPHA * glow)),
                )
            self._paint_plus(painter, inner, ink, glow)

        if self._message:
            painter.setPen(QPen(QColor(self._COLOR_ERROR)))
            painter.drawText(
                inner,
                int(Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap),
                self._message,
            )

        painter.end()

    def _paint_plus(self, painter: QPainter, inner: QRectF, ink: QColor, glow: float) -> None:
        arm = inner.width() * 0.11
        center = inner.center()
        pen = QPen(_faded(ink, 0.22 + 0.45 * glow), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(
            QPointF(center.x() - arm, center.y()), QPointF(center.x() + arm, center.y())
        )
        painter.drawLine(
            QPointF(center.x(), center.y() - arm), QPointF(center.x(), center.y() + arm)
        )
