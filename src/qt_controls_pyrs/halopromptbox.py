# halopromptbox.py
#
# Prompt-Eingabe im Stil der Halo-Widgets: ein feiner Rahmen, innen der
# Fensterhintergrund, weiß unter der Maus und während man tippt. Oben und
# unten im Feld liegt je eine dünne Leiste mit einem Pfeil in der Mitte. Ein
# Klick auf eine der beiden fährt das Feld nach unten aus und legt es über
# das, was darunter liegt; die Pfeile drehen sich dabei um.
#
# Wie die StatusBar hängt das Feld nicht im Layout, sondern schwebt über einem
# Platzhalter (`slot`). Nur so kann es beim Ausfahren über seine Nachbarn
# wachsen, ohne die Aufteilung darunter zu verschieben.

from __future__ import annotations

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QPoint, QPointF, QPropertyAnimation,
    QRect, QRectF, Qt, QTimer, pyqtProperty, pyqtSignal as Signal
)
from PyQt6.QtGui import QColor, QPainter, QPalette, QPen, QPolygonF
from PyQt6.QtWidgets import QFrame, QPlainTextEdit, QPushButton, QWidget

from .buttons.hoverbuttons import _crisp, _faded, _glow, _outline
from .haloscrollbar import HaloScrollBar


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class ExpandBar(QPushButton):
    """Die dünne Leiste mit dem Pfeil, oben und unten im Feld.

    Ein ganz normaler Knopf, nur anders gezeichnet: eine feine Linie über die
    ganze Breite, in der Mitte ein Pfeil. Die ganze Leiste ist die
    Klickfläche, und unter der Maus wird sie hell.

    `base_angle` sagt, wohin der Pfeil in Ruhe zeigt: 0 nach oben (Leiste
    oben im Feld), 180 nach unten (Leiste unten). Beim Umschalten dreht er
    sich um 180 Grad, zeigt also zur jeweils anderen Seite.
    """

    HEIGHT = 16      # Höhe der Klickfläche
    ARROW  = 4.5     # halbe Breite des Pfeils
    GAP    = 8.0     # Lücke in der Linie links und rechts vom Pfeil
    WIDTH  = 1.2     # Strichstärke

    IDLE_ALPHA  = 0.45    # Deckkraft in Ruhe
    HOVER_ALPHA = 1.0     # ... und unter der Maus

    TURN_MS  = 220   # so lange dreht sich der Pfeil
    HOVER_MS = 150   # so lange dauert das Aufhellen

    def __init__(self, parent: QWidget, base_angle: float) -> None:
        super().__init__(parent)
        self.base_angle = base_angle
        self._turn = 0.0      # 0 = wie base_angle, 1 = um 180 Grad gedreht
        self._hover = 0.0

        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        # Die Eingabe soll beim Klick im Textfeld bleiben.
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self._turn_anim = QPropertyAnimation(self, b"turn", self)
        self._turn_anim.setDuration(self.TURN_MS)
        self._turn_anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        self._hover_anim = QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(self.HOVER_MS)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # ==============================
    # Animierte Eigenschaften
    # ==============================

    @pyqtProperty(float)
    def turn(self) -> float:
        return self._turn

    @turn.setter
    def turn(self, value: float) -> None:
        self._turn = value
        self.update()

    @pyqtProperty(float)
    def hover(self) -> float:
        return self._hover

    @hover.setter
    def hover(self, value: float) -> None:
        self._hover = value
        self.update()

    def set_turned(self, turned: bool) -> None:
        """True dreht den Pfeil zur anderen Seite, False zurück."""
        target = 1.0 if turned else 0.0
        if not self.isVisible():
            self._turn_anim.stop()
            self.turn = target
            return
        self._run(self._turn_anim, self._turn, target)

    @staticmethod
    def _run(anim: QPropertyAnimation, current: float, target: float) -> None:
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    # ==============================
    # Maus
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._run(self._hover_anim, self._hover, 0.0)

    # ==============================
    # Darstellung
    # ==============================

    def _color(self) -> QColor:
        ink = self.palette().color(QPalette.ColorRole.ButtonText)
        alpha = self.IDLE_ALPHA + (self.HOVER_ALPHA - self.IDLE_ALPHA) * _clamp(self._hover)
        return _faded(ink, alpha)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(self._color(), self.WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        middle = self.height() / 2.0
        center = self.width() / 2.0
        free = self.ARROW + self.GAP      # so viel Platz bleibt für den Pfeil

        painter.drawLine(QPointF(0.0, middle), QPointF(center - free, middle))
        painter.drawLine(QPointF(center + free, middle), QPointF(float(self.width()), middle))

        # Der Pfeil in der Mitte. Ungedreht zeigt er nach oben; base_angle und
        # die Drehung kommen dazu.
        painter.translate(center, middle)
        painter.rotate(self.base_angle + 180.0 * _clamp(self._turn))
        painter.drawPolyline(QPolygonF([
            QPointF(-self.ARROW, self.ARROW / 2.0),
            QPointF(0.0, -self.ARROW / 2.0),
            QPointF(self.ARROW, self.ARROW / 2.0),
        ]))
        painter.end()


class HaloPromptBox(QWidget):
    """Mehrzeilige Eingabe im Halo-Stil, die sich über den Inhalt darunter ausfährt.

    Das Feld hängt nicht im Layout: dort steht ein Platzhalter (`slot`), der
    Lage und Breite vorgibt, und das Feld schwebt darüber — wie die StatusBar.
    Oben und unten liegt je eine dünne Leiste mit einem Pfeil; ein Klick auf
    eine davon fährt das Feld aus, bis an die Oberkante des Widgets aus
    `set_expand_stop()`. Ein zweiter Klick oder Escape fährt es wieder ein.
    Eingefahren zeigen die Pfeile nach außen, ausgefahren nach innen.

    Gescrollt wird mit der `HaloScrollBar`: einem glühenden Band, das sich
    beim Scrollen wellt.

    Der Text liegt im ganz normalen `QPlainTextEdit` unter `box.text`.
    `toPlainText()`, `setPlainText()`, `setPlaceholderText()`, `clear()` und
    das Signal `textChanged` sind direkt am Widget zu haben.

    Das Fenster muss zwei Dinge tun, sonst sitzt das Feld an der falschen
    Stelle: `sync_geometry()` in seinem `resizeEvent()` aufrufen und dem Feld
    mit `set_expand_stop()` sagen, wo unten Schluss ist.
    """

    # Meldet nach einem Klick auf eine Leiste: True = ausgefahren.
    expanded_changed = Signal(bool)
    # Wie bei QPlainTextEdit: meldet jede Änderung am Text.
    textChanged = Signal()

    ROOM          = 16      # Rand links und rechts, wie bei den Halo-Knöpfen
    ROOM_Y        = 4       # Rand oben und unten
    PAD           = 12      # Abstand des Inhalts zum Rahmen
    GAP           = 6       # Abstand zwischen Leiste und Text
    RADIUS        = 0       # Eckenradius des Rahmens
    OUTLINE_ALPHA = 0.5     # Deckkraft des Rahmens in Ruhe
    INNER_GLOW    = 20      # innerer Schein, wenn die Maus darauf steht oder getippt wird
    HOVER_MS      = 1250    # wie die Halo-Knöpfe: schnell hin, lang aus
    GROW_MS       = 300     # Aus- und Einfahren (0 = ohne Bewegung)
    BOTTOM_BAR    = True    # untere Leiste zeigen (sie tut dasselbe wie die obere)

    def __init__(self, slot: QWidget, parent: QWidget) -> None:
        super().__init__(parent)
        self._slot = slot                    # Platzhalter im Layout
        self._stop: QWidget | None = None    # bis dorthin fährt das Feld aus
        self._is_expanded = False
        self._bright = 0.0                   # 0 = Ruhe, 1 = Maus darauf oder Eingabe

        self.text = QPlainTextEdit(self)
        self.text.setFrameShape(QFrame.Shape.NoFrame)
        self.text.setVerticalScrollBar(HaloScrollBar(self.text))
        self.text.textChanged.connect(self.textChanged)
        # Für Escape zum Einfahren und für den hellen Rahmen beim Tippen.
        self.text.installEventFilter(self)

        # Oben zeigt der Pfeil in Ruhe nach oben, unten nach unten — nach
        # außen also. Ausgefahren zeigen beide nach innen.
        self.top_bar = ExpandBar(self, base_angle=0.0)
        self.bottom_bar = ExpandBar(self, base_angle=180.0)
        self.bottom_bar.setVisible(self.BOTTOM_BAR)
        for bar in (self.top_bar, self.bottom_bar):
            bar.setToolTip("Feld ausfahren")
            bar.clicked.connect(self.toggle)

        self._grow_anim = QPropertyAnimation(self, b"geometry", self)
        self._grow_anim.setDuration(self.GROW_MS)
        self._grow_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._bright_anim = QPropertyAnimation(self, b"bright", self)
        self._bright_anim.setDuration(self.HOVER_MS)
        self._bright_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

        self._apply_text_colors()

        # Der Platzhalter ändert seine Breite auch ohne Größenänderung des
        # Fensters, etwa wenn ein Nachbar längeren Text bekommt.
        self._slot.installEventFilter(self)

        self.sync_geometry()
        # Beim ersten Durchlauf steht das Layout oft noch nicht; sobald es
        # steht, noch einmal ausrichten.
        QTimer.singleShot(0, self.sync_geometry)

    # ==============================
    # Text (wie bei QPlainTextEdit)
    # ==============================

    def toPlainText(self) -> str:
        return self.text.toPlainText()

    def setPlainText(self, text: str) -> None:
        self.text.setPlainText(text)

    def setPlaceholderText(self, text: str) -> None:
        self.text.setPlaceholderText(text)

    def clear(self) -> None:
        self.text.clear()

    # ==============================
    # Aus- und Einfahren
    # ==============================

    def set_expand_stop(self, widget: QWidget | None) -> None:
        """Bis an die Oberkante dieses Widgets fährt das Feld aus.

        Im APIImageGenerator ist das der Generate-Knopf: er bleibt sichtbar,
        alles darüber wird zugedeckt. Ohne Angabe reicht das Feld bis an die
        Unterkante des Elternfensters.
        """
        self._stop = widget
        self.sync_geometry()

    def is_expanded(self) -> bool:
        return self._is_expanded

    def expand(self) -> None:
        if self._is_expanded:
            return
        self._set_expanded(True)

    def collapse(self) -> None:
        if not self._is_expanded:
            return
        self._set_expanded(False)

    def toggle(self) -> None:
        if self._is_expanded:
            self.collapse()
            return
        self.expand()

    def _set_expanded(self, expanded: bool) -> None:
        self._is_expanded = expanded
        for bar in (self.top_bar, self.bottom_bar):
            bar.set_turned(expanded)
            bar.setToolTip("Feld einfahren" if expanded else "Feld ausfahren")

        if expanded:
            self._animate_to(self._expanded_rect())
        else:
            self._animate_to(self._collapsed_rect())
        self.expanded_changed.emit(expanded)

    # ==============================
    # Lage und Größe
    # ==============================

    def sync_geometry(self) -> None:
        """Richtet das Feld neu über dem Platzhalter aus (nach einer Größenänderung)."""
        self.raise_()
        if self._is_expanded:
            target = self._expanded_rect()
        else:
            target = self._collapsed_rect()

        if self._grow_anim.state() == QAbstractAnimation.State.Running:
            self._grow_anim.setEndValue(target)   # laufende Bewegung umlenken
            return
        self.setGeometry(target)

    def _animate_to(self, target: QRect) -> None:
        self.raise_()
        self._grow_anim.stop()
        if not self.isVisible() or self.GROW_MS <= 0:
            # Noch nicht zu sehen, etwa beim Aufbau: ohne Bewegung hinsetzen.
            self.setGeometry(target)
            return
        self._grow_anim.setStartValue(self.geometry())
        self._grow_anim.setEndValue(target)
        self._grow_anim.start()

    def _collapsed_rect(self) -> QRect:
        """Genau über dem Platzhalter."""
        parent = self.parentWidget()
        if parent is None:
            return self.geometry()
        top_left = self._slot.mapTo(parent, QPoint(0, 0))
        return QRect(top_left, self._slot.size())

    def _expanded_rect(self) -> QRect:
        """Vom Platzhalter hinunter bis zum Stopp-Widget."""
        rect = self._collapsed_rect()
        height = max(rect.height(), self._expand_bottom() - rect.top())
        return QRect(rect.x(), rect.y(), rect.width(), height)

    def _expand_bottom(self) -> int:
        """Wo das ausgefahrene Feld endet, gemessen im Elternfenster."""
        parent = self.parentWidget()
        if parent is None:
            return self.geometry().bottom()
        if self._stop is None:
            return parent.height()
        return self._stop.mapTo(parent, QPoint(0, 0)).y()

    def _frame_rect(self) -> QRect:
        """Die sichtbare Fläche: das Widget ohne den Rand, in dem der Schein liegt."""
        return self.rect().adjusted(self.ROOM, self.ROOM_Y, -self.ROOM, -self.ROOM_Y)

    def _place_children(self) -> None:
        """Leisten und Textfeld in den Rahmen setzen: oben Leiste, Text, unten Leiste."""
        frame = self._frame_rect()
        left = frame.x() + self.PAD
        width = max(0, frame.width() - 2 * self.PAD)

        top = frame.y() + self.PAD
        self.top_bar.setGeometry(left, top, width, self.top_bar.height())
        text_top = top + self.top_bar.height() + self.GAP

        text_bottom = frame.y() + frame.height() - self.PAD
        # Nach der Einstellung fragen, nicht nach isVisible(): solange das
        # Fenster noch nicht gezeigt wurde, ist kein Kind sichtbar.
        if self.BOTTOM_BAR:
            self.bottom_bar.setGeometry(
                left, text_bottom - self.bottom_bar.height(), width, self.bottom_bar.height()
            )
            text_bottom -= self.bottom_bar.height() + self.GAP

        self.text.setGeometry(left, text_top, width, max(0, text_bottom - text_top))

    # ==============================
    # Heller Rahmen unter der Maus und beim Tippen
    # ==============================

    @pyqtProperty(float)
    def bright(self) -> float:
        return self._bright

    @bright.setter
    def bright(self, value: float) -> None:
        self._bright = value
        self.update()

    def _update_bright(self) -> None:
        """Hell, solange die Maus darauf steht oder jemand tippt."""
        if self.underMouse() or self.text.hasFocus():
            target = 1.0
        else:
            target = 0.0
        if self._bright == target:
            return
        self._bright_anim.stop()
        self._bright_anim.setStartValue(self._bright)
        self._bright_anim.setEndValue(target)
        self._bright_anim.start()

    # ==============================
    # Ereignisse
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._update_bright()

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._update_bright()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_children()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.sync_geometry()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange:
            self._apply_text_colors()

    def eventFilter(self, watched, event) -> bool:
        if watched is self._slot:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Move, QEvent.Type.Show):
                self.sync_geometry()
            return False

        if watched is self.text:
            if event.type() in (QEvent.Type.FocusIn, QEvent.Type.FocusOut):
                self._update_bright()
                return False
            if event.type() == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape and self._is_expanded:
                    self.collapse()
                    return True     # Escape fährt ein, statt weiterzulaufen

        return super().eventFilter(watched, event)

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _apply_text_colors(self) -> None:
        """Der Text sitzt auf dem Fensterhintergrund, nicht auf dem Grund eines Eingabefeldes."""
        window = self.palette().color(QPalette.ColorRole.Window)
        palette = self.text.palette()
        palette.setColor(QPalette.ColorRole.Base, window)
        self.text.setPalette(palette)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Das ganze Widget deckt ab, was darunter liegt — sonst schiene beim
        # Ausfahren der Inhalt darunter durch.
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))

        frame = QRectF(self._frame_rect())
        ink = self._ink()
        bright = _clamp(self._bright)
        radius = float(self.RADIUS)

        # Unter der Maus und beim Tippen glimmt es innen auf — wie beim
        # Auswahlfeld.
        if bright > 0.0:
            _glow(painter, frame, _faded(ink, 0.5 * bright), self.INNER_GLOW,
                  inside=True, radius=radius)

        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * bright
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(frame, 1.0), max(radius - 0.5, 0.0))
        painter.end()
