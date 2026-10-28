# halogroupbox.py
#
# Rahmen um eine Gruppe im Stil der Halo-Knöpfe: ein feiner Strich, innen leer,
# unter der Maus glimmt es auf. Die Überschrift sitzt in einer Lücke im oberen
# Strich.
#
# Die Lücke entsteht durch Freistellen und nicht durch Übermalen: der Strich
# wird gezeichnet, während der Bereich der Überschrift aus der Zeichenfläche
# ausgenommen ist. Übermalen ginge nur mit einer Hintergrundfarbe, und die hat
# dieses Widget nicht — hinter ihm steht, was das Elternteil dort zeichnet.
#
# Ist die Gruppe abschaltbar (`setCheckable(True)`), steht links vor der
# Überschrift ein kleines Kästchen im Stil der HaloCheckBox. Gezeichnet wird
# es hier, weil Qt es sonst über den Stil täte und der abgeschaltet ist;
# geklickt wird weiterhin wie bei jeder QGroupBox, nämlich im ganzen
# Kopfbereich.

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPropertyAnimation, QRect, QRectF, QSize, Qt, pyqtProperty
)
from PyQt6.QtGui import (
    QBrush, QColor, QFontMetricsF, QPainter, QPainterPath, QPalette, QPen, QRegion
)
from PyQt6.QtWidgets import QGroupBox

from .buttons.hoverbuttons import _crisp, _faded, _glow, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class HaloGroupBox(QGroupBox):
    """Gruppenrahmen statt ``QGroupBox``, im Stil der Halo-Knöpfe.

    Nach außen bleibt es eine ``QGroupBox``: ``setTitle()``,
    ``setCheckable()``, ``isChecked()`` und das ``toggled``-Signal verhalten
    sich unverändert, und ein Layout wird wie gewohnt hineingesetzt.

    Die Ränder für den Inhalt setzt der Rahmen selbst, damit die Kinder nicht
    am Strich kleben und nicht unter der Überschrift liegen.
    """

    RADIUS        = 0         # Eckenradius
    OUTLINE_ALPHA = 0.4       # Deckkraft des Rahmens in Ruhe — etwas blasser
                              # als bei den Eingabefeldern: ein Rahmen umfasst,
                              # er fordert nicht auf.
    INNER_GLOW    = 24        # innerer Schein unter der Maus
    HOVER_MS      = 1250      # wie die Halo-Knöpfe: schnell hin, lang aus

    TITLE_PAD   = 8           # Luft links und rechts der Überschrift
    TITLE_LEFT  = 14          # Abstand der Überschrift zur linken Kante
    PAD_X       = 16          # Rand für den Inhalt, seitlich
    PAD_BOTTOM  = 16
    PAD_TOP     = 10          # zusätzlich zur Höhe der Überschrift

    BOX      = 14             # Kantenlänge des Kästchens bei abschaltbarer Gruppe
    BOX_GAP  = 7              # Abstand zwischen Kästchen und Überschrift
    FILL_PAD = 3              # Abstand des Kerns zum Kästchen
    ACCENT   = "#5a8cff"      # Farbe des Kerns
    SLIDE_MS = 200            # Füllen und Leeren des Kästchens

    def __init__(self, *args, **kwargs) -> None:
        self._hover = 0.0
        self._position = 0.0
        self._accent = QColor(self.ACCENT)
        super().__init__(*args, **kwargs)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFlat(True)    # Qts eigener Rahmen bleibt aus, hier wird selbst gezeichnet

        self._hover_anim = self._animation(b"hover", self.HOVER_MS, QEasingCurve.Type.OutExpo)
        self._slide = self._animation(b"position", self.SLIDE_MS, QEasingCurve.Type.InOutCubic)

        self.toggled.connect(self._on_toggled)
        self._position = 1.0 if self.isChecked() else 0.0
        self._apply_margins()

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
        """Die Farbe des gefüllten Kästchens, nur für diese Gruppe."""
        self._accent = QColor(color)
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
    def position(self) -> float:
        return self._position

    @position.setter
    def position(self, value: float) -> None:
        self._position = value
        self.update()

    def _on_toggled(self, checked: bool) -> None:
        target = 1.0 if checked else 0.0
        if not self.isVisible():
            # Noch nicht zu sehen — etwa beim Einlesen gespeicherter
            # Einstellungen: gleich richtig stehen, nichts animieren.
            self._slide.stop()
            self._position = target
            self.update()
            return
        self._run(self._slide, self._position, target)

    # ==============================
    # Maus
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._run(self._hover_anim, self._hover, 0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Eine gesperrte Gruppe bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._run(self._hover_anim, self._hover, 0.0)
        if event.type() == QEvent.Type.FontChange:
            self._apply_margins()

    # Wo geklickt wird, entscheidet QGroupBox selbst: der ganze Kopfbereich
    # schaltet um, nicht nur das Kästchen. Das sieht man dem Bild nicht an,
    # aber es ist das Verhalten, das jeder von einer QGroupBox kennt - und
    # dieses Widget soll sich nach außen wie sein Vorbild verhalten. Hier wird
    # deshalb nur gezeichnet.

    # ==============================
    # Geometrie
    # ==============================

    def _title_height(self) -> float:
        metrics = QFontMetricsF(self.font())
        return max(metrics.height(), float(self.BOX) if self.isCheckable() else 0.0)

    def _box_rect(self) -> QRectF:
        """Das Kästchen bei abschaltbarer Gruppe — sonst leer."""
        if not self.isCheckable():
            return QRectF()
        top = self._title_height() / 2 - self.BOX / 2
        return QRectF(self.TITLE_LEFT, top, self.BOX, self.BOX)

    def _title_rect(self) -> QRectF:
        """Wo die Überschrift steht — und damit, wo der Strich aussetzt."""
        metrics = QFontMetricsF(self.font())
        left = self.TITLE_LEFT
        if self.isCheckable():
            left += self.BOX + self.BOX_GAP
        width = metrics.horizontalAdvance(self.title())
        return QRectF(left, 0.0, width, self._title_height())

    def _frame_rect(self) -> QRectF:
        """Der Rahmen beginnt auf halber Höhe der Überschrift."""
        top = self._title_height() / 2
        return QRectF(self.rect()).adjusted(0.5, top, -0.5, -0.5)

    def _apply_margins(self) -> None:
        top = self._title_height() + self.PAD_TOP
        self.setContentsMargins(self.PAD_X, int(round(top)), self.PAD_X, self.PAD_BOTTOM)

    def setTitle(self, title: str) -> None:
        super().setTitle(title)
        self._apply_margins()

    def setCheckable(self, checkable: bool) -> None:
        super().setCheckable(checkable)
        self._position = 1.0 if self.isChecked() else 0.0
        self._apply_margins()

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        metrics = QFontMetricsF(self.font())
        needed = self._title_rect().right() + self.TITLE_PAD + self.PAD_X
        return QSize(max(hint.width(), int(round(needed))), hint.height())

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        # Auch im gesperrten Zustand lesbar bleiben — abgeblasst wird global.
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _paint_box(self, painter: QPainter, hover: float) -> None:
        """Das Kästchen der abschaltbaren Gruppe — die HaloCheckBox im Kleinen."""
        box = self._box_rect()
        on = _clamp(self._position)

        if on > 0.0:
            core = box.adjusted(self.FILL_PAD, self.FILL_PAD, -self.FILL_PAD, -self.FILL_PAD)
            _glow(painter, box, _faded(self._accent, 0.35 * on), self.FILL_PAD, inside=True)
            path = QPainterPath()
            path.addRect(core)
            painter.fillPath(path, QBrush(_faded(self._accent, on)))

        ink = self._ink()
        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * hover
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(box, 1.0))

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        ink = self._ink()
        hover = _clamp(self._hover)
        frame = self._frame_rect()
        radius = float(self.RADIUS)

        # Innen glimmen — nicht freigestellt: der Schein liegt innerhalb des
        # Rahmens, die Überschrift sitzt auf ihm.
        if hover > 0.0:
            _glow(painter, frame, _faded(ink, 0.4 * hover), self.INNER_GLOW,
                  inside=True, radius=radius)

        # Der Strich, mit einer Lücke für die Überschrift.
        painter.save()
        title = self._title_rect()
        if self.title():
            gap = title.adjusted(-self.TITLE_PAD, 0, self.TITLE_PAD, 0)
            painter.setClipRegion(
                QRegion(self.rect()) - QRegion(gap.toAlignedRect())
            )
        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * hover
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, frame, radius)
        painter.restore()

        # Die Überschrift, unter der Maus etwas heller.
        if self.title():
            painter.setFont(self.font())
            painter.setPen(QPen(_faded(ink, 0.75 + 0.25 * hover)))
            painter.drawText(
                title, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                self.title(),
            )

        if self.isCheckable():
            self._paint_box(painter, hover)
        painter.end()
