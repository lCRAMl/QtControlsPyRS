# hoverbuttons.py
#
# Fünf Knöpfe nach der CSS-Sammlung "Button Hover Effects" (.btn-1 … .btn-5).
# Alle teilen sich dieselbe Grundform: 45 Pixel hoch, Beschriftung in
# Großbuchstaben, und ein Weg von 0 nach 1, den die Maus vorwärts und beim
# Verlassen rückwärts laufen lässt.
#
# Farben kommen aus der Palette: die Fläche aus `Button`, alles Weiße der
# Vorlage aus `ButtonText`. Wo die Vorlage den Untergrund durchscheinen lässt,
# zeichnet der Knopf schlicht nichts — dort steht das Elternteil.

from __future__ import annotations

from PyQt6.QtCore import (
    QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, QSize, Qt,
    pyqtProperty
)
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QPushButton

# cubic-bezier(0.19, 1, 0.22, 1) der Vorlage: schnell los, weit ausschwingend.
_EXPO = QEasingCurve.Type.OutExpo
# `ease`, die Voreinstellung in CSS.
_EASE = QEasingCurve.Type.InOutQuad
_LINEAR = QEasingCurve.Type.Linear

_CENTER = int(Qt.AlignmentFlag.AlignCenter)


def _mix(first: QColor, second: QColor, amount: float) -> QColor:
    """Farbe zwischen zwei Farben, Deckkraft eingeschlossen."""
    amount = max(0.0, min(1.0, amount))
    return QColor(
        round(first.red() + (second.red() - first.red()) * amount),
        round(first.green() + (second.green() - first.green()) * amount),
        round(first.blue() + (second.blue() - first.blue()) * amount),
        round(first.alpha() + (second.alpha() - first.alpha()) * amount),
    )


def _faded(color: QColor, alpha: float) -> QColor:
    """Dieselbe Farbe mit anderer Deckkraft (0..1)."""
    out = QColor(color)
    out.setAlpha(max(0, min(255, round(alpha * 255))))
    return out


def _crisp(rect: QRectF, width: float) -> QRectF:
    """Rechteck für einen Strich, der ganz innerhalb liegen soll."""
    half = width / 2
    return rect.adjusted(half, half, -half, -half)


def _glow(
    painter: QPainter, rect: QRectF, color: QColor, spread: float,
    inside: bool = False,
) -> None:
    """Weicher Saum nach außen oder innen — der Ersatz für `box-shadow`.

    Qt kennt keinen Weichzeichner beim Zeichnen, deshalb liegen hier mehrere
    immer blassere Striche übereinander; von außen nach innen fällt die
    Deckkraft im Quadrat ab, wie bei einem Schlagschatten. Die Striche addieren
    sich, deshalb wird ihre Deckkraft durch ihre Anzahl geteilt — sonst wäre der
    Saum am Rand gleich deckend.
    """
    steps = max(int(spread), 1)
    base = color.alphaF() * 3.0 / steps
    for index in range(steps):
        part = 1.0 - (index + 0.5) / steps
        grow = (index + 1) * (-1 if inside else 1)
        box = rect.adjusted(-grow, -grow, grow, grow)
        if box.width() <= 1 or box.height() <= 1:
            break
        painter.setPen(QPen(_faded(color, base * part * part), 1.6))
        painter.drawRect(box)


class _HoverButton(QPushButton):
    """Grundform der fünf Knöpfe: zeichnet sich selbst und kennt einen Hover-Weg.

    `hover` läuft unter der Maus von 0 nach 1 und beim Verlassen zurück; Dauer
    und Kurve dürfen sich je Richtung unterscheiden, wie in der Vorlage. Wer
    eine zweite, anders getaktete Bewegung braucht, meldet sie mit `_track()`
    an — sie läuft dann mit.
    """

    HEIGHT    = 45      # line-height der Vorlage
    PAD       = 22      # seitlicher Rand um die Beschriftung
    ROOM      = 0       # Platz je Seite für alles außerhalb der Fläche
    IN_MS     = 600     # transition-duration der Vorlage
    OUT_MS    = 600
    IN_CURVE  = _EASE
    OUT_CURVE = _EASE
    UPPERCASE     = True   # text-transform: uppercase
    WEIGHT_REST   = 400
    WEIGHT_HOVER  = 400
    SPACING_REST  = 0.0    # letter-spacing in Pixeln
    SPACING_HOVER = 0.0

    def __init__(self, text: str = "", parent=None) -> None:
        self._hover = 0.0
        super().__init__(text, parent)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._tracks: list[tuple[QPropertyAnimation, str, int, int, object, object]] = []
        self._hover_anim = self._track(
            b"hover", self.IN_MS, self.OUT_MS, self.IN_CURVE, self.OUT_CURVE
        )

    def _track(
        self, name: bytes, in_ms: int, out_ms: int, in_curve, out_curve
    ) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        self._tracks.append((anim, name.decode(), in_ms, out_ms, in_curve, out_curve))
        return anim

    # ==============================
    # Mauszustand
    # ==============================

    @pyqtProperty(float)
    def hover(self) -> float:
        return self._hover

    @hover.setter
    def hover(self, value: float) -> None:
        self._hover = value
        self.update()

    def _animate(self, target: float) -> None:
        forward = target > 0.0
        for anim, name, in_ms, out_ms, in_curve, out_curve in self._tracks:
            anim.stop()
            anim.setDuration(in_ms if forward else out_ms)
            anim.setEasingCurve(in_curve if forward else out_curve)
            anim.setStartValue(float(self.property(name)))
            anim.setEndValue(target)
            anim.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._animate(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate(0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Ein gesperrter Knopf bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._animate(0.0)

    # ==============================
    # Geometrie und Beschriftung
    # ==============================

    def _room(self) -> float:
        return min(float(self.ROOM), self.height() / 4.0)

    def _surface(self) -> QRectF:
        room = self._room()
        return QRectF(self.rect()).adjusted(room, room, -room, -room)

    def _label_text(self) -> str:
        """Was auf dem Knopf steht — Unterklassen dürfen das austauschen."""
        return self.text()

    def _label(self) -> str:
        text = self._label_text()
        return text.upper() if self.UPPERCASE else text

    def _spacing(self, hover: float) -> float:
        return self.SPACING_REST + (self.SPACING_HOVER - self.SPACING_REST) * hover

    def _label_font(self, hover: float) -> QFont:
        font = QFont(self.font())
        weight = self.WEIGHT_REST + (self.WEIGHT_HOVER - self.WEIGHT_REST) * hover
        font.setWeight(int(round(weight)))
        spacing = self._spacing(hover)
        if spacing:
            font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
        return font

    def sizeHint(self) -> QSize:
        # Der breiteste Zustand ist der unter der Maus — danach richtet sich der
        # Platz, sonst würde die Beschriftung unterwegs anstoßen.
        metrics = QFontMetricsF(self._label_font(1.0))
        width = metrics.horizontalAdvance(self._label()) + 2 * self.PAD
        return QSize(
            int(round(width)) + 2 * self.ROOM,
            self.HEIGHT + 2 * self.ROOM,
        )

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    # ==============================
    # Darstellung
    # ==============================

    def _fill(self, hover: float) -> QColor:
        group = (
            QPalette.ColorGroup.Normal if self.isEnabled()
            else QPalette.ColorGroup.Disabled
        )
        color = self.palette().color(group, QPalette.ColorRole.Button)
        return color.darker(115) if self.isDown() else color

    def _ink(self, hover: float) -> QColor:
        # Auch im gesperrten Zustand lesbar bleiben.
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _text_shadow(self, hover: float) -> tuple[QPointF, QColor] | None:
        """Versatz und Farbe für `text-shadow`, oder nichts."""
        return None

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        """Alles unter der Beschriftung — hier tun die Unterklassen ihre Arbeit."""

    def _paint_label(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        self._draw_label(painter, rect, hover, self._label())

    def _draw_label(
        self, painter: QPainter, rect: QRectF, hover: float, text: str
    ) -> None:
        """Zeichnet eine Beschriftung. Getrennt, damit Unterklassen zwei davon
        übereinanderlegen und überblenden können."""
        painter.setFont(self._label_font(hover))
        # letter-spacing hängt auch hinter dem letzten Buchstaben — ohne diesen
        # Ausgleich säße die Beschriftung sichtbar zu weit links.
        box = rect.translated(self._spacing(hover) / 2, 0)

        shadow = self._text_shadow(hover)
        if shadow is not None:
            offset, color = shadow
            painter.setPen(QPen(color))
            painter.drawText(box.translated(offset), _CENTER, text)

        painter.setPen(QPen(self._ink(hover)))
        painter.drawText(box, _CENTER, text)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        hover = max(0.0, min(1.0, self._hover))
        surface = self._surface()
        self._paint_surface(painter, surface, hover)
        self._paint_label(painter, surface, hover)

        painter.end()


class DashBorderButton(_HoverButton):
    """`.btn-1` — der Rahmen schnurrt zu einem kurzen, dicken Strich zusammen.

    Im Ruhezustand eine gefüllte Fläche mit dünnem, geschlossenem Rahmen und
    hauchdünner Schrift. Unter der Maus verschwindet die Füllung, die Schrift
    wird fett und etwas gesperrt, und aus dem Rahmen bleibt ein kurzes Stück
    übrig, das ein Stück weit gewandert ist (`stroke-dasharray` der Vorlage).
    Der Hinweg dauert lang und schwingt aus, der Rückweg ist kurz und gerade.
    """

    ROOM      = 4
    IN_MS     = 1350
    OUT_MS    = 350
    IN_CURVE  = _EXPO
    OUT_CURVE = _LINEAR
    WEIGHT_REST   = 100
    WEIGHT_HOVER  = 900
    SPACING_HOVER = 1.0

    STROKE_REST  = 2.0
    STROKE_HOVER = 5.0
    DASH      = 15.0     # sichtbares Stück unter der Maus
    GAP       = 310.0    # Lücke dahinter
    OFFSET    = 48.0     # Verschiebung entlang des Rahmens
    PERIMETER = 422.0    # Umfang, auf den sich die Vorlage bezieht

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        fill = self._fill(hover)
        painter.fillRect(rect, _mix(fill, _faded(fill, 0.0), hover))

        width = self.STROKE_REST + (self.STROKE_HOVER - self.STROKE_REST) * hover
        pen = QPen(self._ink(hover), width)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)

        # Die Vorlage rechnet in Pixeln eines 160x45-Knopfes; hier zählt der
        # wirkliche Umfang, damit das Stück überall gleich lang aussieht.
        scale = 2 * (rect.width() + rect.height()) / self.PERIMETER
        gap = self.GAP * hover * scale
        if gap > 0.5:
            dash = (self.PERIMETER + (self.DASH - self.PERIMETER) * hover) * scale
            # Qt misst das Muster in Strichbreiten, die Vorlage in Pixeln.
            pen.setDashPattern([dash / width, gap / width])
            pen.setDashOffset(self.OFFSET * hover * scale / width)

        painter.setPen(pen)
        painter.drawRect(_crisp(rect, width))


class SpreadButton(_HoverButton):
    """`.btn-2` — die Schrift geht auseinander, zwei Striche wachsen mit.

    Im Ruhezustand nur die Beschriftung. Unter der Maus sperrt sie sich auf
    5 Pixel, und über und unter ihr wächst je ein feiner Strich aus der Mitte
    auf 70 Prozent der Breite. Die Striche sind schneller als die Schrift,
    deshalb laufen sie als eigene Bewegung.
    """

    SPACING_HOVER = 5.0
    LINE_MS    = 350
    LINE_WIDTH = 0.7     # Anteil der Fläche, den die Striche erreichen

    def __init__(self, text: str = "", parent=None) -> None:
        self._lines = 0.0
        super().__init__(text, parent)
        self._lines_anim = self._track(
            b"lines", self.LINE_MS, self.LINE_MS, _EASE, _EASE
        )

    @pyqtProperty(float)
    def lines(self) -> float:
        return self._lines

    @lines.setter
    def lines(self, value: float) -> None:
        self._lines = value
        self.update()

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        amount = max(0.0, min(1.0, self._lines))
        if amount <= 0.0:
            return

        width = rect.width() * self.LINE_WIDTH * amount
        left = rect.center().x() - width / 2
        painter.setPen(QPen(_faded(self._ink(hover), amount), 1.0))
        for y in (rect.top() + 0.5, rect.bottom() - 0.5):
            painter.drawLine(QPointF(left, y), QPointF(left + width, y))


class RaisedButton(_HoverButton):
    """`.btn-3` — steht erhaben da und legt sich unter der Maus flach.

    Im Ruhezustand eine aufgehellte Fläche mit dunklem Rand, einer harten Kante
    darunter und einem weichen Schatten — der Knopf steht hervor. Unter der
    Maus wird die Fläche dunkler, der Schatten verschwindet, ein heller Saum
    bleibt, und die Schrift nimmt die Farbe der Fläche an.
    """

    ROOM      = 8        # Platz für den Schlagschatten
    IN_MS     = 250
    OUT_MS    = 150
    IN_CURVE  = _LINEAR
    OUT_CURVE = _LINEAR
    WEIGHT_REST   = 900
    WEIGHT_HOVER  = 900
    SPACING_REST  = 1.0
    SPACING_HOVER = 1.0

    LIFT = 2             # wie weit die harte Kante unter der Fläche hervorsieht

    def _ink(self, hover: float) -> QColor:
        rest = super()._ink(hover)
        return _mix(rest, self._fill(hover).lighter(160), hover)

    def _text_shadow(self, hover: float) -> tuple[QPointF, QColor] | None:
        if hover <= 0.0:
            return None
        return QPointF(-1, -1), _faded(self._fill(hover).darker(140), hover)

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        base = self._fill(hover)

        if hover < 1.0:
            # box-shadow: 0 2px 0 dunkler, 2px 4px 6px dunkler
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_faded(base.darker(125), 1.0 - hover))
            painter.drawRect(rect.translated(0, self.LIFT))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            _glow(
                painter, rect.translated(2, 4),
                _faded(base.darker(115), 1.0 - hover), 6,
            )

        painter.fillRect(rect, _mix(base.lighter(108), base.darker(104), hover))

        if hover > 0.0:
            # box-shadow: 1px 1px 2px rgba(#fff, .2)
            _glow(painter, rect.translated(1, 1), _faded(super()._ink(hover), 0.2 * hover), 2)

        border = _mix(base.darker(112), _faded(QColor(0, 0, 0), 0.05), hover)
        painter.setPen(QPen(border, 1.0))
        painter.drawRect(_crisp(rect, 1.0))


class ShineButton(_HoverButton):
    """`.btn-4` — ein schräger Lichtstreifen wischt einmal über die Fläche.

    Der Streifen liegt links außerhalb und fährt unter der Maus quer über den
    Knopf hinaus; der Rand schneidet ihn ab (`overflow: hidden`). Er liegt
    hinter der Beschriftung, so wie in der Vorlage.
    """

    IN_MS     = 550
    OUT_MS    = 550
    IN_CURVE  = _EXPO
    OUT_CURVE = _EXPO

    BAR_W     = 50       # Maße des Streifens, bezogen auf 45 Pixel Höhe
    BAR_H     = 155
    BAR_TOP   = -50
    BAR_START = -75      # Startpunkt links außerhalb
    BAR_END   = 1.2      # Ziel: 120 Prozent der Breite
    ANGLE     = 35
    BAR_ALPHA = 0.2

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        ink = self._ink(hover)

        painter.save()
        painter.setClipRect(rect)
        unit = rect.height() / self.HEIGHT
        start = self.BAR_START * unit
        left = rect.left() + start + hover * (rect.width() * self.BAR_END - start)
        bar = QRectF(left, rect.top() + self.BAR_TOP * unit,
                     self.BAR_W * unit, self.BAR_H * unit)
        center = bar.center()
        painter.translate(center)
        painter.rotate(self.ANGLE)
        painter.translate(-center)
        painter.fillRect(bar, _faded(ink, self.BAR_ALPHA))
        painter.restore()

        painter.setPen(QPen(ink, 1.0))
        painter.drawRect(_crisp(rect, 1.0))


class HaloButton(_HoverButton):
    """`.btn-5` — der Rahmen löst sich nach außen auf, innen glimmt es auf.

    Im Ruhezustand liegt ein halbdurchsichtiger Strich dicht um die Fläche.
    Unter der Maus wandert er nach außen und verblasst, während der Knopf
    selbst einen Rand bekommt und von innen wie von außen zu leuchten anfängt.
    Der lange Weg schwingt weit aus.
    """

    ROOM      = 16       # Platz, in den der Strich hinauswandert
    IN_MS     = 1250
    OUT_MS    = 1250
    IN_CURVE  = _EXPO
    OUT_CURVE = _EXPO

    OUTLINE_ALPHA = 0.5
    INNER_GLOW = 20
    OUTER_GLOW = 20
    SHADOW_COLOR = "#427388"

    def _text_shadow(self, hover: float) -> tuple[QPointF, QColor] | None:
        if hover <= 0.0:
            return None
        return QPointF(1, 1), _faded(QColor(self.SHADOW_COLOR), hover)

    def _paint_surface(self, painter: QPainter, rect: QRectF, hover: float) -> None:
        ink = self._ink(hover)

        if hover < 1.0:
            # outline-offset wächst, outline-color verschwindet dabei
            out = self._room() * hover
            painter.setPen(QPen(_faded(ink, self.OUTLINE_ALPHA * (1.0 - hover)), 1.0))
            painter.drawRect(rect.adjusted(-out, -out, out, out))

        if hover > 0.0:
            _glow(painter, rect, _faded(ink, 0.5 * hover), self.INNER_GLOW, inside=True)
            _glow(painter, rect, _faded(ink, 0.2 * hover),
                  min(self.OUTER_GLOW, self._room()))
            painter.setPen(QPen(_faded(ink, hover), 1.0))
            painter.drawRect(_crisp(rect, 1.0))
