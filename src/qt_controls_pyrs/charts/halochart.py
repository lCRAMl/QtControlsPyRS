# halochart.py
#
# Ein Liniendiagramm im Halo-Stil: Gitter und Achsen zurückhaltend, die Kurven
# als glühende Linien darüber. Gezeichnet wird wie bei Schieberegler und
# Bildlaufleiste in Schichten übereinander, die addiert werden
# (CompositionMode_Plus) - Qt kennt beim Zeichnen keinen Weichzeichner.
#
# Das Widget weiß nichts über den Gegenstand. Es nimmt Punktfolgen, Linien und
# Bänder entgegen und zeichnet sie; was eine Kurve bedeutet, bleibt Sache des
# Programms. Deshalb heißen die Achsen auch nur x und y und tragen eine
# Beschriftung, die hereingereicht wird.
#
# Drei Arten von Inhalt:
#
#   Kurve   eine Folge von (x, y) - add_series()
#   Linie   ein einzelner Wert quer durchs Bild - add_rule()
#   Band    ein Bereich zwischen zwei Werten     - add_band()
#
# Linie und Band gibt es waagerecht wie senkrecht. Ein Sollwert ist eine
# waagerechte Linie, ein Sättigungsbereich ein waagerechtes Band, ein
# Zeitpunkt eine senkrechte Linie.
#
# Unter der Maus erscheint ein senkrechtes Lineal und daneben die Werte aller
# Kurven an dieser Stelle. Zwischen zwei Punkten wird geradlinig gemittelt;
# außerhalb der Kurve steht nichts.

from __future__ import annotations

import math
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPalette, QPen
from PyQt6.QtWidgets import QWidget

from ..buttons.hoverbuttons import _faded


@dataclass
class _Series:
    """Eine Kurve: Name, Punkte, Farbe."""

    name: str
    points: tuple[tuple[float, float], ...] = ()
    color: QColor | None = None


@dataclass
class _Mark:
    """Eine Linie oder ein Band quer durchs Bild.

    `high is None` heißt Linie, sonst Band. `vertical` sagt, auf welcher Achse
    die Werte liegen: falsch bedeutet y (die Marke liegt waagerecht im Bild).
    """

    low: float
    high: float | None = None
    vertical: bool = False
    label: str = ""
    color: QColor | None = None


def _nice_step(span: float, wanted: int) -> float:
    """Eine runde Schrittweite, die etwa `wanted` Striche ergibt.

    Gerundet wird auf 1, 2 oder 5 mal eine Zehnerpotenz - die Zahlen, die am
    Gitter lesbar bleiben. Ohne das stehen dort Werte wie 0,3571.

    Gerundet wird zur NAECHSTEN dieser Zahlen, nicht nach oben. Der
    Unterschied ist nicht theoretisch: bei einer Spanne von 3 und fuenf
    gewuenschten Strichen ist der rohe Schritt 0,6. Nach oben gerundet wird
    daraus 1,0, und das Gitter hat nur noch drei Striche statt der
    gewuenschten fuenf. Zur naechsten Zahl gerundet sind es 0,5 und sechs
    Striche - einer mehr als gewuenscht, aber naeher dran.
    """
    if span <= 0.0 or wanted <= 0:
        return 1.0
    roh = span / wanted
    potenz = 10.0 ** math.floor(math.log10(roh))
    anteil = roh / potenz
    if anteil < 1.5:
        return potenz
    if anteil < 3.0:
        return 2.0 * potenz
    if anteil < 7.0:
        return 5.0 * potenz
    return 10.0 * potenz


def _format(value: float, step: float) -> str:
    """Eine Zahl so genau, wie die Schrittweite es verlangt - nicht genauer."""
    stellen = max(0, -int(math.floor(math.log10(step))) if step > 0 else 0)
    text = ("%." + str(min(stellen, 6)) + "f") % value
    return text.replace(".", ",")


class HaloChart(QWidget):
    """Liniendiagramm mit glühenden Kurven, Gitter und Lineal unter der Maus.

    Ein eigenständiges Widget ohne Qt-Vorbild. Kurven, Linien und Bänder
    kommen von außen; die Achsen stellen sich selbst ein, solange keine
    Spanne vorgegeben ist:

        bild = HaloChart()
        bild.set_labels("Zeit [s]", "Vakuum [mbar]")
        bild.add_series("Verlauf", [(0.0, 0.0), (1.0, 120.0), (2.0, 190.0)])
        bild.add_rule(180.0, label="Sollvakuum")
        bild.add_band(170.0, 200.0, label="Saettigung")

    Gerechnet wird nur beim Zeichnen; es läuft kein Bildtakt mit.
    """

    # --- Maße ---
    PAD_LEFT   = 64     # Platz für die Beschriftung der y-Achse
    PAD_RIGHT  = 14
    PAD_TOP    = 14
    PAD_BOTTOM = 40     # Platz für die Beschriftung der x-Achse
    TICKS_X    = 6      # angestrebte Zahl der Striche
    TICKS_Y    = 5

    # --- Deckkraft ---
    FRAME     = 0.22
    GRID      = 0.08
    TEXT      = 0.65
    BAND      = 0.10
    RULE      = 0.45
    READOUT   = 0.92

    # --- Kurve: (Breite, Deckkraft) von außen nach innen ---
    LAYERS = (
        (7.0, 0.05),
        (4.0, 0.10),
        (2.2, 0.28),
        (1.3, 0.95),
    )

    #: Farben der Kurven, wenn keine mitgegeben wird. Die erste ist die
    #: Signalfarbe der Palette; die übrigen stehen fest, damit zwei Kurven
    #: sich nicht zufällig gleichen.
    FALLBACK_COLORS = ("#e0a33c", "#46b57a", "#d9534f", "#9a7fd1", "#3cc5e0")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._series: list[_Series] = []
        self._marks: list[_Mark] = []
        self._x_label = ""
        self._y_label = ""
        self._x_range: tuple[float, float] | None = None
        self._y_range: tuple[float, float] | None = None
        self._cursor: QPointF | None = None

        self.setMouseTracking(True)
        self.setMinimumSize(220, 140)

    # ==============================
    # Inhalt
    # ==============================

    def add_series(self, name: str, points, color: QColor | str | None = None) -> None:
        """Eine Kurve aufnehmen oder eine gleichnamige ersetzen.

        Gleicher Name bedeutet dieselbe Kurve - ein zweiter Aufruf tauscht die
        Punkte aus und lässt die Farbe stehen. Damit kann ein Programm bei
        jeder Neuberechnung dieselbe Zeile aufrufen, ohne vorher aufzuräumen,
        und die Farben springen nicht.
        """
        farbe = QColor(color) if color is not None else None
        for eintrag in self._series:
            if eintrag.name == name:
                eintrag.points = tuple((float(x), float(y)) for x, y in points)
                if farbe is not None:
                    eintrag.color = farbe
                self.update()
                return
        self._series.append(
            _Series(name, tuple((float(x), float(y)) for x, y in points), farbe)
        )
        self.update()

    def remove_series(self, name: str) -> None:
        self._series = [s for s in self._series if s.name != name]
        self.update()

    def series_names(self) -> tuple[str, ...]:
        return tuple(s.name for s in self._series)

    def add_rule(
        self, value: float, *, vertical: bool = False,
        label: str = "", color: QColor | str | None = None,
    ) -> None:
        """Eine einzelne Linie quer durchs Bild - etwa ein Sollwert."""
        self._marks.append(
            _Mark(float(value), None, vertical, label,
                  QColor(color) if color is not None else None)
        )
        self.update()

    def add_band(
        self, low: float, high: float, *, vertical: bool = False,
        label: str = "", color: QColor | str | None = None,
    ) -> None:
        """Ein Bereich zwischen zwei Werten - etwa ein Saettigungsbereich."""
        a, b = (float(low), float(high))
        self._marks.append(
            _Mark(min(a, b), max(a, b), vertical, label,
                  QColor(color) if color is not None else None)
        )
        self.update()

    def clear_marks(self) -> None:
        self._marks.clear()
        self.update()

    def clear(self) -> None:
        """Kurven und Marken entfernen. Beschriftung und Spannen bleiben."""
        self._series.clear()
        self._marks.clear()
        self.update()

    # ==============================
    # Achsen
    # ==============================

    def set_labels(self, x: str = "", y: str = "") -> None:
        self._x_label, self._y_label = x, y
        self.update()

    def set_x_range(self, low: float | None, high: float | None = None) -> None:
        """Feste Spanne der x-Achse. `set_x_range(None)` stellt wieder um."""
        self._x_range = None if low is None or high is None else (float(low), float(high))
        self.update()

    def set_y_range(self, low: float | None, high: float | None = None) -> None:
        self._y_range = None if low is None or high is None else (float(low), float(high))
        self.update()

    def x_range(self) -> tuple[float, float]:
        return self._x_range or self._auto_range(0)

    def y_range(self) -> tuple[float, float]:
        return self._y_range or self._auto_range(1)

    def _auto_range(self, achse: int) -> tuple[float, float]:
        """Spanne aus Kurven UND Marken, mit etwas Luft.

        Die Marken gehoeren dazu: ein Sollwert ueber allen Messpunkten liefe
        sonst aus dem Bild, und gerade dort will man ihn sehen.
        """
        werte: list[float] = []
        for eintrag in self._series:
            werte.extend(punkt[achse] for punkt in eintrag.points)
        for marke in self._marks:
            if marke.vertical == (achse == 0):
                werte.append(marke.low)
                if marke.high is not None:
                    werte.append(marke.high)

        if not werte:
            return 0.0, 1.0
        tief, hoch = min(werte), max(werte)
        if hoch - tief < 1e-12:
            return tief - 1.0, hoch + 1.0
        luft = (hoch - tief) * 0.06
        return tief - luft, hoch + luft

    # ==============================
    # Umrechnung
    # ==============================

    def _plot_rect(self) -> QRectF:
        return QRectF(
            self.PAD_LEFT, self.PAD_TOP,
            max(1.0, self.width() - self.PAD_LEFT - self.PAD_RIGHT),
            max(1.0, self.height() - self.PAD_TOP - self.PAD_BOTTOM),
        )

    def _to_px(self, x: float, y: float) -> QPointF:
        rect = self._plot_rect()
        x0, x1 = self.x_range()
        y0, y1 = self.y_range()
        fx = 0.0 if x1 - x0 == 0 else (x - x0) / (x1 - x0)
        fy = 0.0 if y1 - y0 == 0 else (y - y0) / (y1 - y0)
        return QPointF(rect.left() + fx * rect.width(),
                       rect.bottom() - fy * rect.height())

    def _x_at(self, px: float) -> float:
        rect = self._plot_rect()
        x0, x1 = self.x_range()
        return x0 + (px - rect.left()) / rect.width() * (x1 - x0)

    def value_at(self, name: str, x: float) -> float | None:
        """Der Wert einer Kurve bei x, geradlinig zwischen den Punkten.

        None, wenn es die Kurve nicht gibt oder x ausserhalb ihrer Punkte
        liegt. Nicht fortgesetzt zu werden ist Absicht: eine Kurve, die bei
        zwei Sekunden endet, hat bei drei Sekunden keinen Wert, und ihn
        trotzdem zu zeigen waere erfunden.
        """
        eintrag = next((s for s in self._series if s.name == name), None)
        if eintrag is None or len(eintrag.points) == 0:
            return None
        punkte = eintrag.points
        if x < punkte[0][0] or x > punkte[-1][0]:
            return None
        for (ax, ay), (bx, by) in zip(punkte, punkte[1:]):
            if ax <= x <= bx:
                if bx - ax < 1e-12:
                    return ay
                anteil = (x - ax) / (bx - ax)
                return ay + anteil * (by - ay)
        return punkte[-1][1]

    # ==============================
    # Maus
    # ==============================

    def mouseMoveEvent(self, event) -> None:
        self._cursor = event.position()
        self.update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._cursor = None
        self.update()
        super().leaveEvent(event)

    # ==============================
    # Zeichnen
    # ==============================

    def sizeHint(self) -> QSize:
        return QSize(420, 260)

    def _ink(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.WindowText)

    def _color_of(self, index: int, eintrag: _Series) -> QColor:
        if eintrag.color is not None:
            return eintrag.color
        if index == 0:
            return self.palette().color(QPalette.ColorRole.Highlight)
        return QColor(self.FALLBACK_COLORS[index % len(self.FALLBACK_COLORS)])

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # JEDER Schritt gibt den Maler so zurueck, wie er ihn bekommen hat
        # (save/restore). Qt fuehrt Stift, Pinsel, Schrift und Mischart
        # weiter, bis jemand sie aendert - und ein liegengebliebener Pinsel
        # faellt erst im Bild auf. Gemessen beim ersten Anlauf: der Pinsel
        # eines Bandes blieb stehen, drawRect() fuellte damit die ganze
        # Zeichenflaeche und drawPath() jede Kurve, indem es sie
        # stillschweigend schloss. Mit dieser Regel braucht kein Schritt
        # mehr aufzuraeumen, was ein anderer hinterlassen hat.
        rect = self._plot_rect()
        self._paint_bands(painter, rect)
        self._paint_grid(painter, rect)
        self._paint_rules(painter, rect)
        self._paint_series(painter, rect)
        self._paint_cursor(painter, rect)
        painter.end()

    def _paint_grid(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        ink = self._ink()
        schrift = QFont(self.font())
        schrift.setPointSize(max(7, schrift.pointSize() - 1))
        painter.setFont(schrift)
        metrik = QFontMetricsF(schrift)

        x0, x1 = self.x_range()
        y0, y1 = self.y_range()
        schritt_x = _nice_step(x1 - x0, self.TICKS_X)
        schritt_y = _nice_step(y1 - y0, self.TICKS_Y)

        painter.setPen(QPen(_faded(ink, self.GRID), 1.0))
        wert = math.ceil(x0 / schritt_x) * schritt_x
        striche_x = []
        while wert <= x1 + 1e-9:
            px = self._to_px(wert, y0).x()
            painter.drawLine(QPointF(px, rect.top()), QPointF(px, rect.bottom()))
            striche_x.append((px, wert))
            wert += schritt_x

        wert = math.ceil(y0 / schritt_y) * schritt_y
        striche_y = []
        while wert <= y1 + 1e-9:
            py = self._to_px(x0, wert).y()
            painter.drawLine(QPointF(rect.left(), py), QPointF(rect.right(), py))
            striche_y.append((py, wert))
            wert += schritt_y

        painter.setPen(QPen(_faded(ink, self.FRAME), 1.2))
        painter.drawRect(rect)

        painter.setPen(QPen(_faded(ink, self.TEXT), 1.0))
        for px, wert in striche_x:
            text = _format(wert, schritt_x)
            breite = metrik.horizontalAdvance(text)
            painter.drawText(QPointF(px - breite / 2.0,
                                     rect.bottom() + metrik.height() + 2.0), text)
        for py, wert in striche_y:
            text = _format(wert, schritt_y)
            breite = metrik.horizontalAdvance(text)
            painter.drawText(QPointF(rect.left() - breite - 6.0,
                                     py + metrik.capHeight() / 2.0), text)

        if self._x_label:
            breite = metrik.horizontalAdvance(self._x_label)
            painter.drawText(
                QPointF(rect.center().x() - breite / 2.0, float(self.height() - 4)),
                self._x_label,
            )
        if self._y_label:
            painter.save()
            painter.translate(12.0, rect.center().y())
            painter.rotate(-90.0)
            breite = metrik.horizontalAdvance(self._y_label)
            painter.drawText(QPointF(-breite / 2.0, 0.0), self._y_label)
            painter.restore()
        painter.restore()

    def _paint_bands(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for marke in self._marks:
            if marke.high is None:
                continue
            farbe = marke.color or self.palette().color(QPalette.ColorRole.Highlight)
            painter.setBrush(_faded(farbe, self.BAND))
            if marke.vertical:
                a = self._to_px(marke.low, 0.0).x()
                b = self._to_px(marke.high, 0.0).x()
                painter.drawRect(QRectF(min(a, b), rect.top(), abs(b - a), rect.height()))
            else:
                a = self._to_px(0.0, marke.low).y()
                b = self._to_px(0.0, marke.high).y()
                painter.drawRect(QRectF(rect.left(), min(a, b), rect.width(), abs(b - a)))
        painter.restore()

    def _paint_rules(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        schrift = QFont(self.font())
        schrift.setPointSize(max(7, schrift.pointSize() - 1))
        painter.setFont(schrift)
        metrik = QFontMetricsF(schrift)

        for marke in self._marks:
            if marke.high is not None:
                continue
            farbe = marke.color or self.palette().color(QPalette.ColorRole.Highlight)
            stift = QPen(_faded(farbe, self.RULE), 1.2)
            stift.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(stift)
            if marke.vertical:
                px = self._to_px(marke.low, 0.0).x()
                painter.drawLine(QPointF(px, rect.top()), QPointF(px, rect.bottom()))
                stelle = QPointF(px + 4.0, rect.top() + metrik.height())
            else:
                py = self._to_px(0.0, marke.low).y()
                painter.drawLine(QPointF(rect.left(), py), QPointF(rect.right(), py))
                stelle = QPointF(rect.left() + 4.0, py - 3.0)
            if marke.label:
                painter.setPen(QPen(_faded(farbe, self.READOUT), 1.0))
                painter.drawText(stelle, marke.label)
        painter.restore()

    def _paint_series(self, painter: QPainter, rect: QRectF) -> None:
        painter.save()
        painter.setClipRect(rect)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
        for index, eintrag in enumerate(self._series):
            if len(eintrag.points) < 2:
                continue
            pfad = QPainterPath()
            erster = True
            for x, y in eintrag.points:
                punkt = self._to_px(x, y)
                if erster:
                    pfad.moveTo(punkt)
                    erster = False
                else:
                    pfad.lineTo(punkt)
            farbe = self._color_of(index, eintrag)
            for breite, deckkraft in self.LAYERS:
                stift = QPen(_faded(farbe, deckkraft), breite)
                stift.setCapStyle(Qt.PenCapStyle.RoundCap)
                stift.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.setPen(stift)
                painter.drawPath(pfad)
        painter.restore()

    def _paint_cursor(self, painter: QPainter, rect: QRectF) -> None:
        if self._cursor is None or not rect.contains(self._cursor):
            return

        painter.save()
        ink = self._ink()
        x = self._x_at(self._cursor.x())
        px = self._cursor.x()

        painter.setPen(QPen(_faded(ink, self.RULE), 1.0))
        painter.drawLine(QPointF(px, rect.top()), QPointF(px, rect.bottom()))

        schrift = QFont(self.font())
        schrift.setPointSize(max(7, schrift.pointSize() - 1))
        painter.setFont(schrift)
        metrik = QFontMetricsF(schrift)

        zeilen = []
        for index, eintrag in enumerate(self._series):
            wert = self.value_at(eintrag.name, x)
            if wert is None:
                continue
            zeilen.append((self._color_of(index, eintrag),
                           eintrag.name + "  " + _format(wert, abs(wert) / 100.0 or 0.01)))
        if not zeilen:
            painter.restore()
            return

        breite = max(metrik.horizontalAdvance(text) for _f, text in zeilen) + 12.0
        hoehe = len(zeilen) * metrik.height() + 8.0
        links = px + 10.0
        if links + breite > rect.right():
            links = px - 10.0 - breite
        oben = rect.top() + 6.0

        painter.setPen(QPen(_faded(ink, self.FRAME), 1.0))
        painter.setBrush(_faded(self.palette().color(QPalette.ColorRole.Window), 0.88))
        painter.drawRoundedRect(QRectF(links, oben, breite, hoehe), 4.0, 4.0)

        y = oben + metrik.height()
        for farbe, text in zeilen:
            painter.setPen(QPen(_faded(farbe, self.READOUT), 1.0))
            painter.drawText(QPointF(links + 6.0, y - 3.0), text)
            y += metrik.height()
        painter.restore()
