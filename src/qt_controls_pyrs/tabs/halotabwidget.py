# halotabwidget.py
#
# Reiter im Stil der Halo-Widgets. Unter dem aktiven Reiter liegt ein dünner
# Strich in der Signalfarbe; beim Wechsel gleitet er zum neuen Reiter, und der
# ganze Inhalt schiebt sich seitlich hinaus, während der nächste auf dieselbe
# Weise hereinkommt. Die hinausgehende Seite wird dabei unscharf, die
# hereinkommende scharf.
#
# Vorbild ist animate-ui (Tabs): dort gleiten Inhalt und Strich auf Federn,
# und ein Wechsel mitten in der Bewegung lenkt sie einfach um. Die Federn hier
# rechnen dasselbe in geschlossener Form.
#
# Während des Gleitens liegt über dem Inhalt eine Decke, die zwei Aufnahmen
# zeichnet: die alte Seite und die neue. Die echten Seiten bewegen sich nicht —
# so gleitet es ruckfrei, egal wie viel auf einer Seite steht, und die
# Unschärfe kostet nur einmal Rechenzeit, nicht in jedem Bild.

from __future__ import annotations

import math

from PyQt6 import sip
from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QPoint, QPropertyAnimation, QRect,
    QRectF, QSize, Qt, pyqtProperty
)
from PyQt6.QtGui import QColor, QPainter, QPalette, QPixmap
from PyQt6.QtWidgets import (
    QGraphicsBlurEffect, QGraphicsPixmapItem, QGraphicsScene, QTabBar, QTabWidget,
    QWidget
)

from ..buttons.hoverbuttons import _faded

# Dämpfung der beiden Federn wie bei animate-ui. 1 hieße: gerade eben ohne
# Überschwingen; knapp darunter schwingen sie kaum merklich nach.
_SLIDE_DAMPING = 32 / (2 * math.sqrt(300))   # Inhalt: stiffness 300, damping 32
_LINE_DAMPING = 25 / (2 * math.sqrt(200))    # Strich: stiffness 200, damping 25

# Nach der eingestellten Dauer fehlt nur noch ein Tausendstel des Wegs.
_REST = math.log(1000.0)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class _Spring:
    """Gedämpfte Feder, wie Motion sie für animate-ui rechnet.

    `aim()` startet sie an `start` mit dem Tempo `velocity` in Richtung
    `target`; `state()` sagt, wo sie nach so und so vielen Millisekunden steht
    und wie schnell sie ist. Lenkt man sie unterwegs um, übergibt man Lage und
    Tempo von eben — dann springt nichts, und nichts bleibt ruckartig stehen.
    """

    def __init__(self, damping: float) -> None:
        assert 0.0 < damping < 1.0
        self.damping = damping
        self.target = 0.0
        self._offset = 0.0        # Abstand zum Ziel beim Start
        self._velocity = 0.0      # Tempo beim Start, in Einheiten je Sekunde
        self._omega = 1.0

    def aim(self, start: float, target: float, velocity: float, duration_ms: int) -> None:
        self.target = target
        self._offset = start - target
        self._velocity = velocity
        self._omega = _REST / (self.damping * max(1, duration_ms) / 1000.0)

    def state(self, elapsed_ms: float) -> tuple[float, float]:
        t = elapsed_ms / 1000.0
        omega = self._omega
        decay = self.damping * omega
        swing = omega * math.sqrt(1.0 - self.damping ** 2)
        a = self._offset
        b = (self._velocity + decay * a) / swing
        fade = math.exp(-decay * t)
        cos, sin = math.cos(swing * t), math.sin(swing * t)
        position = self.target + fade * (a * cos + b * sin)
        velocity = fade * (
            self._velocity * cos - (decay * self._velocity + omega * omega * a) / swing * sin
        )
        return position, velocity


def _blurred(pixmap: QPixmap, radius: float, background: QColor) -> QPixmap:
    """Eine unscharfe Kopie. Der Rand verläuft in den Hintergrund, nicht ins Leere."""
    ratio = pixmap.devicePixelRatio()
    effect = QGraphicsBlurEffect()
    effect.setBlurRadius(radius * ratio)
    effect.setBlurHints(QGraphicsBlurEffect.BlurHint.QualityHint)
    item = QGraphicsPixmapItem(pixmap)
    item.setGraphicsEffect(effect)
    scene = QGraphicsScene()
    scene.addItem(item)

    result = QPixmap(pixmap.size())
    result.setDevicePixelRatio(ratio)
    result.fill(background)
    size = pixmap.deviceIndependentSize()
    area = QRectF(0.0, 0.0, size.width(), size.height())
    painter = QPainter(result)
    scene.render(painter, area, area)
    painter.end()
    return result


class HaloTabWidget(QTabWidget):
    """Reiter, deren Inhalt beim Wechsel seitlich hinaus- und hereingleitet.

    Nach außen bleibt es ein QTabWidget: `addTab()`, `insertTab()`,
    `removeTab()`, `setCurrentIndex()`, `currentWidget()`, `setTabText()`,
    `setTabEnabled()` und das Signal `currentChanged` funktionieren
    unverändert. `currentWidget()` ist sofort die neue Seite — das Gleiten ist
    nur die Anzeige.

    Die Reiter teilen sich die ganze Breite. Unter dem aktiven liegt ein dünner
    Strich in der Signalfarbe auf einer blassen Grundlinie; beim Wechsel gleitet
    er hinüber, und die Beschriftungen blenden mit ihm um. Der Inhalt schiebt
    sich zur Seite hinaus und wird dabei unscharf, der neue kommt von der
    anderen Seite scharf herein — nach rechts, wenn der neue Reiter rechts
    liegt. Ein Wechsel mitten im Gleiten lenkt die Bewegung einfach um.

    Die Höhe ist fest: alle Seiten bekommen dieselbe Fläche.

    `ROOM` rückt Leiste und Gleiten links und rechts ein, so wie der Rand der
    Halo-Knöpfe: steht das Widget in einer Spalte mit ihnen, enden Grundlinie
    und gleitender Inhalt genau an ihrem Rahmen. Die Seiten selbst bekommen
    weiter die ganze Breite — ein HaloDropdown darauf hält seinen Rand selbst.

    Nicht unterstützt: Reiter an der Seite oder unten, Symbole, Schließknöpfe
    und verschiebbare Reiter — die Leiste zeichnet nur ihre Beschriftungen.
    """

    # --- Leiste ---
    HEIGHT      = 36          # Höhe der Reiterleiste
    ROOM        = 0           # Rand links und rechts von Leiste und Gleiten (Halo-Knöpfe: 16)
    PAD         = 16          # Abstand der Beschriftung zum Rand des Reiters
    LINE        = 2           # Dicke des Strichs unter dem aktiven Reiter
    ACCENT      = "#5a8cff"   # Farbe des Strichs
    BASE_ALPHA  = 0.2         # Deckkraft der Grundlinie über die ganze Breite
    IDLE_ALPHA  = 0.5         # Deckkraft der Beschriftung, wenn der Reiter nicht aktiv ist
    HOVER_ALPHA = 0.8         # ... und wenn die Maus darauf steht
    LINE_MS     = 550         # so lange gleitet der Strich
    HOVER_MS    = 1250        # wie die Halo-Knöpfe: schnell hin, lang aus

    # --- Inhalt ---
    SLIDE_MS    = 430         # so lange gleitet der Inhalt
    BLUR        = 8           # Unschärfe der gleitenden Seiten (0 = keine)

    def __init__(self, parent: QWidget | None = None) -> None:
        self._accent = QColor(self.ACCENT)
        self._shown: QWidget | None = None      # die Seite, die zuletzt aktiv war
        super().__init__(parent)

        self.setTabBar(_HaloTabBar(self))
        # Ohne Rahmen um die Seiten; die Leiste bekommt so die ganze Breite.
        # setDocumentMode() schaltet an der Leiste das Verteilen des Platzes
        # ab und die Qt-Grundlinie an — beides wird danach zurückgestellt.
        self.setDocumentMode(True)
        self.tabBar().setExpanding(True)
        self.tabBar().setDrawBase(False)

        self._curtain = _SlideCurtain(self)
        self._curtain.hide()

        self.currentChanged.connect(self._on_current_changed)

    # ==============================
    # Farbe
    # ==============================

    def accent_color(self) -> QColor:
        return QColor(self._accent)

    def setAccentColor(self, color) -> None:
        """Die Farbe des Strichs, nur für dieses Widget."""
        self._accent = QColor(color)
        self.tabBar().update()

    # ==============================
    # Wechsel
    # ==============================

    def is_sliding(self) -> bool:
        """Gleitet der Inhalt gerade?"""
        return self._curtain.isVisible()

    def _on_current_changed(self, index: int) -> None:
        old, new = self._shown, self.currentWidget()
        self._shown = new
        if not self._can_slide(old, new):
            self._curtain.stop()
            return
        self._curtain.slide(old, new, forward=self.indexOf(new) > self.indexOf(old))

    def _can_slide(self, old: QWidget | None, new: QWidget | None) -> bool:
        if old is None or new is None or old is new or sip.isdeleted(old):
            return False
        # Die alte Seite wurde entfernt, oder es ist noch nichts zu sehen —
        # etwa beim Einlesen gespeicherter Einstellungen: gleich richtig stehen.
        return self.indexOf(old) >= 0 and self.isVisible() and self.SLIDE_MS > 0

    def _page_rect(self, page: QWidget) -> QRect:
        """Wo die Seiten liegen, in Koordinaten dieses Widgets."""
        return QRect(page.mapTo(self, QPoint(0, 0)), page.size())

    # ==============================
    # Ereignisse
    # ==============================

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place_bar()
        # Die Aufnahmen passen nicht mehr — gleich ans Ziel.
        self._curtain.stop()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._curtain.stop()

    # Qt legt die Leiste bei jeder dieser Gelegenheiten wieder über die ganze
    # Breite; danach wird sie jeweils um ROOM eingerückt.
    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._place_bar()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        self._place_bar()

    def event(self, event) -> bool:
        handled = super().event(event)
        if event.type() == QEvent.Type.LayoutRequest:
            self._place_bar()
        return handled

    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._place_bar()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._place_bar()

    def _place_bar(self) -> None:
        """Die Leiste um ROOM eingerückt, damit sie bündig mit den Halo-Knöpfen endet."""
        room = max(0, self.ROOM)
        if room == 0:
            return
        bar = self.tabBar()
        now = bar.geometry()
        wanted = QRect(room, now.y(), max(0, self.width() - 2 * room), now.height())
        if now != wanted:
            bar.setGeometry(wanted)


class _SlideCurtain(QWidget):
    """Liegt während des Gleitens über dem Inhalt und zeichnet beide Seiten.

    `value` läuft von 0 (alte Seite ganz da) nach 1 (neue Seite ganz da).
    Solange die Decke liegt, kommt kein Klick zu den Seiten darunter durch.
    """

    def __init__(self, tabs: HaloTabWidget) -> None:
        super().__init__(tabs)
        self._tabs = tabs
        self._value = 0.0
        self._clock = 0.0
        self._forward = True
        self._spring = _Spring(_SLIDE_DAMPING)
        # Die beiden Seiten, scharf und unscharf; bei `_from_page = None` ist
        # die alte Aufnahme ein Zwischenstand aus einem früheren Gleiten.
        self._from_page: QWidget | None = None
        self._to_page: QWidget | None = None
        self._from = self._from_blur = self._to = self._to_blur = QPixmap()

        self._anim = QPropertyAnimation(self, b"clock", self)
        self._anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._anim.finished.connect(self._arrived)

    # ==============================
    # Steuerung
    # ==============================

    def slide(self, old: QWidget, new: QWidget, forward: bool) -> None:
        if self.isVisible():
            position, velocity = self._spring.state(self._clock)
            # Zurück zu einer der beiden Seiten, die gerade gleiten: die
            # Bewegung kehrt einfach um, mit dem Schwung von eben.
            if new is self._from_page:
                self._aim(position, 0.0, velocity)
                return
            if new is self._to_page:
                self._aim(position, 1.0, velocity)
                return
            # Ein dritter Reiter: was gerade zu sehen ist, gleitet als Ganzes hinaus.
            before, before_page = self.grab(), None
        else:
            before, before_page = old.grab(), old

        self.setGeometry(self._tabs._page_rect(new))
        after = new.grab()
        background = self._tabs.palette().color(QPalette.ColorRole.Window)
        blur = self._tabs.BLUR
        self._from, self._to = before, after
        self._from_blur = _blurred(before, blur, background) if blur > 0 else before
        self._to_blur = _blurred(after, blur, background) if blur > 0 else after
        self._from_page, self._to_page = before_page, new
        self._forward = forward

        self._value = 0.0
        self.raise_()
        self.show()
        self._aim(0.0, 1.0, 0.0)

    def stop(self) -> None:
        """Sofort ans Ziel, ohne Gleiten."""
        self._anim.stop()
        self._arrived()

    def _aim(self, start: float, target: float, velocity: float) -> None:
        duration = self._tabs.SLIDE_MS
        self._spring.aim(start, target, velocity, duration)
        self._anim.stop()
        self._anim.setDuration(duration)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(float(duration))
        self._anim.start()

    def _arrived(self) -> None:
        self.hide()
        self._from = self._from_blur = self._to = self._to_blur = QPixmap()
        self._from_page = self._to_page = None

    # ==============================
    # Animierte Eigenschaft
    # ==============================

    @pyqtProperty(float)
    def clock(self) -> float:
        return self._clock

    @clock.setter
    def clock(self, value: float) -> None:
        self._clock = value
        self._value, _ = self._spring.state(value)
        self.update()

    def value(self) -> float:
        return self._value

    # ==============================
    # Maus: nichts kommt durch
    # ==============================

    def mousePressEvent(self, event) -> None:
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        event.accept()

    def wheelEvent(self, event) -> None:
        event.accept()

    # ==============================
    # Darstellung
    # ==============================

    def paintEvent(self, event) -> None:
        if self._to.isNull():
            return
        painter = QPainter(self)
        width = self.width()
        room = max(0, self._tabs.ROOM)
        if room > 0:
            # Der Inhalt verschwindet genau am Rand, nicht erst am Widgetrand.
            background = self._tabs.palette().color(QPalette.ColorRole.Window)
            painter.fillRect(0, 0, room, self.height(), background)
            painter.fillRect(width - room, 0, room, self.height(), background)
            painter.setClipRect(room, 0, max(0, width - 2 * room), self.height())
        # Vorwärts wandert alles nach links: die alte Seite hinaus, die neue
        # von rechts herein. Rückwärts spiegelbildlich.
        side = -1.0 if self._forward else 1.0
        value = self._value
        self._paint_page(painter, side * value * width, self._from, self._from_blur, value)
        self._paint_page(
            painter, -side * (1.0 - value) * width, self._to, self._to_blur, 1.0 - value
        )
        painter.end()

    @staticmethod
    def _paint_page(
        painter: QPainter, x: float, sharp: QPixmap, blurred: QPixmap, blur: float,
    ) -> None:
        """Eine Seite an ihrer Stelle: je weiter draußen, desto unschärfer."""
        blur = _clamp(blur)
        left = int(round(x))
        if blur > 0.0:
            painter.drawPixmap(left, 0, blurred)
        if blur < 1.0:
            painter.setOpacity(1.0 - blur)
            painter.drawPixmap(left, 0, sharp)
            painter.setOpacity(1.0)


class _HaloTabBar(QTabBar):
    """Die Leiste: gleich breite Reiter, darunter Grundlinie und Strich.

    Ihre Einstellungen holt sie sich aus dem HaloTabWidget, zu dem sie gehört.
    """

    def __init__(self, tabs: HaloTabWidget) -> None:
        self._tabs = tabs
        self._line = 0.0          # Lage des Strichs, gezählt in Reitern
        self._line_clock = 0.0
        self._line_spring = _Spring(_LINE_DAMPING)
        self._hot = -1            # Reiter unter der Maus
        self._cold = -1           # Reiter, den die Maus eben verlassen hat
        self._hot_level = 0.0
        self._cold_level = 0.0
        super().__init__(tabs)

        self.setExpanding(True)
        self.setUsesScrollButtons(False)
        self.setElideMode(Qt.TextElideMode.ElideRight)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._line_anim = QPropertyAnimation(self, b"line_clock", self)
        self._line_anim.setEasingCurve(QEasingCurve.Type.Linear)
        self._line_anim.finished.connect(self._line_arrived)
        self._hot_anim = self._hover_animation(b"hot_level")
        self._cold_anim = self._hover_animation(b"cold_level")

        self.currentChanged.connect(self._on_current_changed)

    def _hover_animation(self, name: bytes) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(self._tabs.HOVER_MS)
        anim.setEasingCurve(QEasingCurve.Type.OutExpo)
        return anim

    @staticmethod
    def _run(anim: QPropertyAnimation, current: float, target: float) -> None:
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    # ==============================
    # Strich
    # ==============================

    def _on_current_changed(self, index: int) -> None:
        tabs = self._tabs
        if index < 0 or not self.isVisible() or tabs.LINE_MS <= 0:
            self._jump_line()
            return
        if self._line_anim.state() == QAbstractAnimation.State.Running:
            position, velocity = self._line_spring.state(self._line_clock)
        else:
            position, velocity = self._line, 0.0
        self._line_spring.aim(position, float(index), velocity, tabs.LINE_MS)
        self._line_anim.stop()
        self._line_anim.setDuration(tabs.LINE_MS)
        self._line_anim.setStartValue(0.0)
        self._line_anim.setEndValue(float(tabs.LINE_MS))
        self._line_anim.start()

    def _jump_line(self) -> None:
        self._line_anim.stop()
        self._line = float(max(0, self.currentIndex()))
        self.update()

    def _line_arrived(self) -> None:
        self._line = float(max(0, self.currentIndex()))
        self.update()

    def line_position(self) -> float:
        return self._line

    @pyqtProperty(float)
    def line_clock(self) -> float:
        return self._line_clock

    @line_clock.setter
    def line_clock(self, value: float) -> None:
        self._line_clock = value
        self._line, _ = self._line_spring.state(value)
        self.update()

    # Werden Reiter eingefügt, entfernt oder verschoben, zählt der Strich neu.
    def tabInserted(self, index: int) -> None:
        super().tabInserted(index)
        self._forget_hover()
        self._jump_line()

    def tabRemoved(self, index: int) -> None:
        super().tabRemoved(index)
        self._forget_hover()
        self._jump_line()

    def tabLayoutChange(self) -> None:
        super().tabLayoutChange()
        self.update()

    # ==============================
    # Maus
    # ==============================

    @pyqtProperty(float)
    def hot_level(self) -> float:
        return self._hot_level

    @hot_level.setter
    def hot_level(self, value: float) -> None:
        self._hot_level = value
        self.update()

    @pyqtProperty(float)
    def cold_level(self) -> float:
        return self._cold_level

    @cold_level.setter
    def cold_level(self, value: float) -> None:
        self._cold_level = value
        self.update()

    def _set_hot(self, index: int) -> None:
        if index == self._hot:
            return
        # Der bisherige Reiter blendet von dort aus, wo er gerade steht, aus.
        if self._hot >= 0:
            self._cold, level = self._hot, self._hot_level
            self._run(self._cold_anim, level, 0.0)
        self._hot = index
        if index >= 0:
            start = self._cold_level if index == self._cold else 0.0
            if index == self._cold:
                self._cold_anim.stop()
                self._cold, self._cold_level = -1, 0.0
            self._run(self._hot_anim, start, 1.0)
        else:
            self._hot_anim.stop()
            self._hot_level = 0.0

    def _forget_hover(self) -> None:
        self._hot_anim.stop()
        self._cold_anim.stop()
        self._hot = self._cold = -1
        self._hot_level = self._cold_level = 0.0

    def hover_level(self, index: int) -> float:
        if index == self._hot:
            return self._hot_level
        if index == self._cold:
            return self._cold_level
        return 0.0

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)
        index = self.tabAt(event.position().toPoint())
        self._set_hot(index if index >= 0 and self.isTabEnabled(index) else -1)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._set_hot(-1)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Eine gesperrte Leiste bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._set_hot(-1)

    # ==============================
    # Geometrie
    # ==============================

    def tabSizeHint(self, index: int) -> QSize:
        # Alle gleich breit — sonst verteilt Qt den freien Platz ungleich.
        metrics = self.fontMetrics()
        widest = max(
            (metrics.horizontalAdvance(self.tabText(i)) for i in range(self.count())),
            default=0,
        )
        return QSize(widest + 2 * self._tabs.PAD, self._tabs.HEIGHT)

    def minimumTabSizeHint(self, index: int) -> QSize:
        # Wird es eng, kürzt die Beschriftung mit „…".
        return QSize(self.fontMetrics().horizontalAdvance("M…") + 2 * self._tabs.PAD,
                     self._tabs.HEIGHT)

    def _line_rect(self) -> QRectF:
        """Der Strich, zwischen zwei Reitern gleitend."""
        count = self.count()
        if count == 0:
            return QRectF()
        position = max(0.0, min(float(count - 1), self._line))
        left = int(math.floor(position))
        right = min(count - 1, left + 1)
        share = position - left
        a, b = QRectF(self.tabRect(left)), QRectF(self.tabRect(right))
        x = a.left() + (b.left() - a.left()) * share
        width = a.width() + (b.width() - a.width()) * share
        thickness = self._tabs.LINE
        return QRectF(x, self.height() - thickness, width, thickness)

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        return self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)

    def label_alpha(self, index: int) -> float:
        """Wie deutlich eine Beschriftung steht: aktiv ganz, sonst gedimmt."""
        tabs = self._tabs
        if not self.isEnabled() or not self.isTabEnabled(index):
            return tabs.IDLE_ALPHA * 0.5
        # Die Beschriftung folgt dem Strich: je näher er ist, desto heller.
        active = _clamp(1.0 - abs(self._line - index))
        alpha = tabs.IDLE_ALPHA + (1.0 - tabs.IDLE_ALPHA) * active
        hover = tabs.IDLE_ALPHA + (tabs.HOVER_ALPHA - tabs.IDLE_ALPHA) * _clamp(self.hover_level(index))
        return max(alpha, hover)

    def paintEvent(self, event) -> None:
        tabs = self._tabs
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self._ink()

        # Grundlinie über die ganze Breite
        painter.fillRect(QRectF(0, self.height() - 1, self.width(), 1),
                         _faded(ink, tabs.BASE_ALPHA))

        # Strich unter dem aktiven Reiter
        if self.count():
            accent = QColor(tabs._accent)
            if not self.isEnabled():
                accent = _faded(accent, 0.4)
            painter.fillRect(self._line_rect(), accent)

        # Beschriftungen, mittig über dem Strich
        painter.setFont(self.font())
        metrics = self.fontMetrics()
        for index in range(self.count()):
            rect = QRectF(self.tabRect(index)).adjusted(tabs.PAD, 0, -tabs.PAD, -tabs.LINE)
            text = metrics.elidedText(
                self.tabText(index), Qt.TextElideMode.ElideRight, int(rect.width())
            )
            painter.setPen(_faded(ink, self.label_alpha(index)))
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        painter.end()
