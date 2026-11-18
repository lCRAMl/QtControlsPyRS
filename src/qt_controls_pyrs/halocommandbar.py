# halocommandbar.py
#
# Befehlsleiste im Stil eines Menübands (Ribbon), passend zu den Halo-Widgets.
#
# Die Leiste besteht aus Gruppen mit Überschrift; in jeder Gruppe stehen große
# Knöpfe (Symbol über der Schrift) und kleine (Symbol links, Schrift rechts),
# die sich zu zweit übereinander stapeln. Jeder Knopf hängt an einer QAction:
# Text, Symbol, Kurzbefehl, gesperrt, angehakt und ein angehängtes Menü kommen
# von dort. Die Anwendung schaltet also nur Aktionen, nie Knöpfe — dieselbe
# Aktion kann zugleich im Kontextmenü stehen und per Kurzbefehl auslösen.
#
# In Ruhe ist ein Knopf flach, nur Symbol und Schrift. Unter der Maus glimmt er
# innen auf und bekommt einen feinen Rahmen, wie die Leiste des HaloDropdown.
# Ein angehakter Knopf (Werkzeugmodus) leuchtet in der Signalfarbe und trägt
# unten denselben Strich wie der aktive Reiter des HaloTabWidget.
#
# Wird das Fenster schmal, gibt die Leiste in zwei Stufen nach, statt das
# Fenster breit zu halten oder Knöpfe abzuschneiden: zuerst verlieren die
# kleinen Knöpfe ihre Schrift, dann auch die großen, und die Überschriften
# werden gekürzt. Die Höhe bleibt dabei gleich, nichts darunter springt.

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer, pyqtProperty
from PyQt6.QtGui import (
    QAction, QColor, QFont, QFontMetricsF, QIcon, QKeySequence, QPainter, QPalette, QPen,
    QPixmap, QPolygonF
)
from PyQt6.QtWidgets import QHBoxLayout, QLayout, QSizePolicy, QToolButton, QVBoxLayout, QWidget

from .buttons.hoverbuttons import _crisp, _faded, _glow, _outline

LARGE = "large"
SMALL = "small"

# Dichte der Leiste: 0 = alles beschriftet, 1 = kleine Knöpfe nur mit Symbol,
# 2 = auch große Knöpfe nur mit Symbol, Überschriften gekürzt.
_DENSITIES = (0, 1, 2)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


# Eingefärbte Symbole werden zwischengespeichert: beim Überfahren der Leiste
# zeichnen viele Knöpfe in schneller Folge, und jedes Mal ein SVG neu zu
# rastern und einzufärben wäre verschenkte Zeit.
_TINT_CACHE: dict[tuple, QPixmap] = {}
_TINT_CACHE_MAX = 512


def tinted_pixmap(icon: QIcon, size: int, color: QColor, ratio: float) -> QPixmap:
    """Das Symbol in einer einzigen Farbe — die Form bleibt, die Farbe nicht.

    Gedacht für einfarbige Symbole (schwarz gezeichnete SVGs): sie nehmen so
    die Schriftfarbe der Palette an und passen zu Hell wie Dunkel, ohne dass
    die Anwendung zwei Sätze Symbole pflegt.
    """
    key = (icon.cacheKey(), size, color.rgba(), round(ratio * 100))
    cached = _TINT_CACHE.get(key)
    if cached is not None:
        return cached

    source = icon.pixmap(QSize(size, size), ratio)
    result = QPixmap(source.size())
    result.setDevicePixelRatio(source.devicePixelRatio())
    result.fill(Qt.GlobalColor.transparent)
    painter = QPainter(result)
    painter.drawPixmap(0, 0, source)
    # SourceIn behält die Deckkraft des Symbols und ersetzt nur die Farbe.
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(result.rect(), color)
    painter.end()

    if len(_TINT_CACHE) >= _TINT_CACHE_MAX:
        _TINT_CACHE.clear()
    _TINT_CACHE[key] = result
    return result


class HaloToolButton(QToolButton):
    """Knopf der Befehlsleiste, gesteuert von einer QAction.

    `size` ist ``"large"`` (Symbol über der Schrift) oder ``"small"`` (Symbol
    links, Schrift rechts). Hat die Aktion ein Menü, öffnet ein Klick es sofort
    und rechts steht ein kleiner Pfeil.

    Der Knopf nimmt nie den Tastaturfokus: Kurzbefehle sollen dort wirken, wo
    gerade gearbeitet wird, nicht in der Leiste.
    """

    ICON_LARGE    = 24
    ICON_SMALL    = 16
    LARGE_H       = 54       # Höhe eines großen Knopfs
    SMALL_H       = 25       # zwei kleine übereinander plus Abstand ergeben LARGE_H
    LARGE_MIN_W   = 46       # ein großer Knopf mit kurzer Schrift wirkt sonst gequetscht
    PAD           = 7        # Innenrand links und rechts
    GAP           = 4        # Abstand zwischen Symbol und Schrift
    ARROW         = 3.0      # halbe Breite des Menüpfeils
    RADIUS        = 4
    INNER_GLOW    = 10
    HOVER_ALPHA   = 0.6      # Deckkraft des Rahmens unter der Maus
    HOVER_MS      = 1250
    ACCENT        = "#5a8cff"
    CHECKED_FILL  = 0.08     # Deckkraft der Fläche eines angehakten Knopfs
    CHECKED_GLOW  = 0.10     # ... und seines inneren Scheins
    CHECKED_SPREAD = 6
    TINT_ICONS    = True     # einfarbige Symbole in Schrift- bzw. Signalfarbe

    def __init__(self, action: QAction, size: str = LARGE, parent: QWidget | None = None) -> None:
        if size not in (LARGE, SMALL):
            raise ValueError(f"size muss {LARGE!r} oder {SMALL!r} sein, nicht {size!r}")
        self._size = size
        self._hover = 0.0
        self._text_visible = True
        self._accent = QColor(self.ACCENT)
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self._hover_anim = QPropertyAnimation(self, b"hover", self)
        self._hover_anim.setDuration(self.HOVER_MS)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutExpo)

        self.setDefaultAction(action)
        self._sync()

    # ==============================
    # Aktion
    # ==============================

    def size_kind(self) -> str:
        return self._size

    def actionEvent(self, event) -> None:
        # QToolButton übernimmt Text, Symbol und Zustand von selbst; hier kommt
        # nur dazu, was er nicht kennt: der Tooltip mit Kurzbefehl, das
        # Sofort-Menü und die Größe für eine geänderte Beschriftung.
        super().actionEvent(event)
        if event.action() is self.defaultAction():
            self._sync()

    def _sync(self) -> None:
        action = self.defaultAction()
        if action is None:
            return
        self.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup if action.menu()
            else QToolButton.ToolButtonPopupMode.DelayedPopup
        )
        self.setToolTip(self.tooltip_for(action))
        self.updateGeometry()
        self.update()

    @staticmethod
    def tooltip_for(action: QAction) -> str:
        """„Speichern (Ctrl+S)“, darunter der Statustext, falls es einen gibt."""
        tip = action.toolTip() or action.iconText()
        shortcut = action.shortcut().toString(QKeySequence.SequenceFormat.NativeText)
        if shortcut:
            tip = f"{tip} ({shortcut})"
        status = action.statusTip()
        if status and status != action.toolTip():
            tip = f"{tip}\n{status}"
        return tip

    def _label(self) -> str:
        action = self.defaultAction()
        # iconText() lässt „&“ und ein „…“ am Ende weg — beides gehört ins
        # Menü, nicht auf einen Knopf.
        return action.iconText() if action is not None else self.text()

    def _has_icon(self) -> bool:
        action = self.defaultAction()
        return action is not None and not action.icon().isNull()

    def _has_menu(self) -> bool:
        action = self.defaultAction()
        return action is not None and action.menu() is not None

    def _arrow_width(self) -> float:
        """Platz für den Menüpfeil samt Abstand davor; 0 ohne Menü."""
        return (2 * self.ARROW + self.GAP) if self._has_menu() else 0.0

    # ==============================
    # Beschriftung und Größe
    # ==============================

    def text_visible(self) -> bool:
        return self._text_visible

    def set_text_visible(self, visible: bool) -> None:
        """Schrift zeigen oder nur das Symbol. Ohne Symbol bleibt die Schrift."""
        visible = visible or not self._has_icon()
        if visible != self._text_visible:
            self._text_visible = visible
            self.updateGeometry()
            self.update()

    def hint_for(self, text_visible: bool) -> QSize:
        """Größe mit oder ohne Schrift — die Leiste rechnet damit ihre Dichte aus."""
        text_visible = text_visible or not self._has_icon()
        # Ein Pixel Reserve: die Laufweite ist gebrochen, die Breite ganzzahlig.
        text_w = (QFontMetricsF(self.font()).horizontalAdvance(self._label()) + 1.0
                  if text_visible else 0.0)
        arrow = self._arrow_width()
        if self._size == LARGE:
            if text_visible:
                content = max(self.ICON_LARGE if self._has_icon() else 0.0, text_w + arrow)
            else:
                content = self.ICON_LARGE + arrow
            width = max(content + 2 * self.PAD, self.LARGE_MIN_W if text_visible else 0.0)
            return QSize(int(round(width + 0.49)), self.LARGE_H)
        width = 2 * self.PAD + arrow
        if self._has_icon():
            width += self.ICON_SMALL
        if text_visible and text_w:
            width += text_w + (self.GAP if self._has_icon() else 0.0)
        return QSize(int(round(width + 0.49)), self.SMALL_H)

    def sizeHint(self) -> QSize:
        return self.hint_for(self._text_visible)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

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
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._hover)
        self._hover_anim.setEndValue(target)
        self._hover_anim.start()

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        if self.isEnabled():
            self._animate(1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        self._animate(0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Ein gesperrter Knopf bekommt kein leaveEvent mehr.
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self._hover_anim.stop()
            self.hover = 0.0
        elif event.type() == QEvent.Type.FontChange:
            self.updateGeometry()

    def setAccentColor(self, color) -> None:  # noqa: N802 - Qt-Namensschema
        self._accent = QColor(color)
        self.update()

    # ==============================
    # Zeichnen
    # ==============================

    def _ink(self) -> QColor:
        # Gesperrt wird global abgeblasst, die Farbe selbst bleibt kräftig.
        return self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.35)

        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        ink = self._ink()
        hover = _clamp(self._hover)
        checked = self.isChecked()
        radius = float(self.RADIUS)

        if checked:
            # Zurückhaltend: ein angehakter Werkzeugmodus steht oft lange an und
            # darf das Auge nicht ständig auf sich ziehen. Der Strich unten und
            # die Signalfarbe von Symbol und Schrift sagen genug.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_faded(self._accent, self.CHECKED_FILL))
            painter.drawRoundedRect(rect, radius, radius)
            _glow(painter, rect, _faded(self._accent, self.CHECKED_GLOW), self.CHECKED_SPREAD,
                  inside=True, radius=radius)
        if self.isDown():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_faded(ink, 0.10))
            painter.drawRoundedRect(rect, radius, radius)
        if hover > 0.0:
            _glow(painter, rect, _faded(ink, 0.35 * hover), self.INNER_GLOW,
                  inside=True, radius=radius)
            painter.setPen(QPen(_faded(ink, self.HOVER_ALPHA * hover), 1.0))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            _outline(painter, _crisp(rect, 1.0), max(radius - 0.5, 0.0))

        # Symbol und Schrift bekommen die volle Fläche; die halben Pixel oben
        # gelten nur für die Striche. Sonst fehlt der Schrift genau ein Pixel,
        # und Qt kürzt „Save“ zu „S…“.
        content = QRectF(self.rect())
        color = self._accent if checked else ink
        if self._size == LARGE:
            self._paint_large(painter, content, color, hover)
        else:
            self._paint_small(painter, content, color, hover)

        if checked:
            # Derselbe Strich wie unter dem aktiven Reiter.
            line = QRectF(rect.left() + self.PAD, rect.bottom() - 2.0,
                          rect.width() - 2 * self.PAD, 2.0)
            painter.fillRect(line, self._accent)
        painter.end()

    def _icon_pixmap(self, size: int, color: QColor) -> QPixmap:
        icon = self.defaultAction().icon()
        ratio = self.devicePixelRatioF()
        if self.TINT_ICONS:
            return tinted_pixmap(icon, size, color, ratio)
        return icon.pixmap(QSize(size, size), ratio)

    def _text_pen(self, color: QColor, hover: float) -> QPen:
        return QPen(_faded(color, 0.82 + 0.18 * hover))

    def _paint_large(self, painter: QPainter, rect: QRectF, color: QColor, hover: float) -> None:
        metrics = QFontMetricsF(self.font())
        show_text = self._text_visible and bool(self._label())
        icon_h = self.ICON_LARGE if self._has_icon() else 0
        text_h = metrics.height() if show_text else 0.0
        block = icon_h + text_h + (self.GAP if icon_h and show_text else 0.0)
        top = rect.top() + (rect.height() - block) / 2.0
        arrow_w = self._arrow_width()
        center_x = rect.center().x()

        if show_text:
            # Schrift und Pfeil bilden zusammen eine mittige Zeile unter dem Symbol.
            text_top = top + icon_h + (self.GAP if icon_h else 0.0)
            room = rect.width() - 2 * self.PAD - arrow_w
            shown = metrics.elidedText(self._label(), Qt.TextElideMode.ElideRight, room)
            text_w = metrics.horizontalAdvance(shown)
            left = center_x - (text_w + arrow_w) / 2.0
            painter.setPen(self._text_pen(color, hover))
            painter.drawText(QRectF(left, text_top, text_w + 1.0, text_h),
                             int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), shown)
            if arrow_w:
                self._paint_arrow(painter, QPointF(left + text_w + self.GAP + self.ARROW,
                                                   text_top + text_h / 2.0), color, hover)
            icon_x = center_x - self.ICON_LARGE / 2.0
        else:
            # Ohne Schrift steht der Pfeil rechts neben dem Symbol.
            icon_x = center_x - (self.ICON_LARGE + arrow_w) / 2.0
            if arrow_w:
                self._paint_arrow(painter, QPointF(icon_x + self.ICON_LARGE + self.GAP + self.ARROW,
                                                   top + icon_h / 2.0), color, hover)

        if icon_h:
            pixmap = self._icon_pixmap(self.ICON_LARGE, color)
            painter.drawPixmap(QPointF(round(icon_x), round(top)), pixmap)

    def _paint_small(self, painter: QPainter, rect: QRectF, color: QColor, hover: float) -> None:
        x = rect.left() + self.PAD
        mid = rect.center().y()
        if self._has_icon():
            pixmap = self._icon_pixmap(self.ICON_SMALL, color)
            painter.drawPixmap(QPointF(round(x), round(mid - self.ICON_SMALL / 2.0)), pixmap)
            x += self.ICON_SMALL + self.GAP
        arrow_w = self._arrow_width()
        if self._text_visible and self._label():
            box = QRectF(x, rect.top(), rect.right() - self.PAD - arrow_w - x, rect.height())
            metrics = QFontMetricsF(self.font())
            shown = metrics.elidedText(self._label(), Qt.TextElideMode.ElideRight, box.width())
            painter.setPen(self._text_pen(color, hover))
            painter.drawText(box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), shown)
        if arrow_w:
            self._paint_arrow(painter, QPointF(rect.right() - self.PAD - self.ARROW, mid), color, hover)

    def _paint_arrow(self, painter: QPainter, center: QPointF, color: QColor, hover: float) -> None:
        size = self.ARROW
        pen = QPen(_faded(color, 0.7 + 0.3 * hover), 1.4)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolyline(QPolygonF([
            QPointF(center.x() - size, center.y() - size / 2),
            QPointF(center.x(), center.y() + size / 2),
            QPointF(center.x() + size, center.y() - size / 2),
        ]))


class HaloCommandGroup(QWidget):
    """Eine Gruppe der Befehlsleiste: Knöpfe nebeneinander, darunter die Überschrift.

    Große Knöpfe bilden je eine eigene Spalte; aufeinanderfolgende kleine
    Knöpfe füllen eine Spalte mit `SMALL_ROWS` Plätzen, bevor die nächste
    beginnt. `add_widget()` stellt ein beliebiges Widget als eigene Spalte
    dazu, etwa ein Auswahlfeld oder einen Schalter.

    Ausblenden mit `setVisible(False)` — die Leiste rückt nach und nimmt den
    Trennstrich mit.
    """

    SMALL_ROWS    = 2
    COLUMN_GAP    = 2        # Abstand zwischen zwei Spalten
    ROW_GAP       = 4        # Abstand zwischen zwei kleinen Knöpfen übereinander
    CAPTION_H     = 15
    CAPTION_PAD   = 6        # Luft links und rechts der Überschrift
    CAPTION_ALPHA = 0.5
    CAPTION_SCALE = 0.85     # Schriftgröße der Überschrift relativ zur Grundschrift

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._title = title
        self._elide_caption = False
        self._columns: list[list[QWidget]] = []   # je Spalte ihre Widgets
        self._small_column: QVBoxLayout | None = None

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, self.CAPTION_H)
        outer.setSpacing(0)
        self._row = QHBoxLayout()
        self._row.setContentsMargins(0, 0, 0, 0)
        self._row.setSpacing(self.COLUMN_GAP)
        # Ist die Überschrift breiter als die Knöpfe, stehen sie mittig darüber.
        self._row.addStretch(1)
        self._row.addStretch(1)
        outer.addLayout(self._row)

    def title(self) -> str:
        return self._title

    def setTitle(self, title: str) -> None:  # noqa: N802 - Qt-Namensschema
        self._title = title
        self.updateGeometry()
        self.update()

    def buttons(self) -> list[HaloToolButton]:
        return [w for column in self._columns for w in column if isinstance(w, HaloToolButton)]

    def add_action(self, action: QAction, size: str = LARGE) -> HaloToolButton:
        button = HaloToolButton(action, size, self)
        if size == SMALL:
            if self._small_column is None or self._small_column.count() >= self.SMALL_ROWS:
                self._small_column = self._new_column()
            self._small_column.addWidget(button)
            self._columns[-1].append(button)
        else:
            self._small_column = None
            self._insert_column(button)
        self.updateGeometry()
        return button

    def add_widget(self, widget: QWidget) -> QWidget:
        self._small_column = None
        self._insert_column(widget, Qt.AlignmentFlag.AlignVCenter)
        self.updateGeometry()
        return widget

    def _insert_column(self, widget: QWidget, align=Qt.AlignmentFlag.AlignTop) -> None:
        widget.setParent(self)
        self._row.insertWidget(self._row.count() - 1, widget, 0, align)
        self._columns.append([widget])

    def _new_column(self) -> QVBoxLayout:
        holder = QWidget(self)
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(self.ROW_GAP)
        column.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._row.insertWidget(self._row.count() - 1, holder, 0, Qt.AlignmentFlag.AlignTop)
        self._columns.append([])
        return column

    # ==============================
    # Dichte
    # ==============================

    def apply_density(self, density: int) -> None:
        for button in self.buttons():
            button.set_text_visible(self._text_at(button, density))
        self._elide_caption = density >= 2
        self.updateGeometry()
        self.update()

    @staticmethod
    def _text_at(button: HaloToolButton, density: int) -> bool:
        limit = 1 if button.size_kind() == SMALL else 2
        return density < limit

    def width_for(self, density: int) -> int:
        """Breite der Gruppe bei dieser Dichte, ohne sie anzuwenden."""
        widths = []
        for column in self._columns:
            if not column:
                continue
            widths.append(max(
                (w.hint_for(self._text_at(w, density)).width() if isinstance(w, HaloToolButton)
                 else w.sizeHint().width())
                for w in column
            ))
        content = sum(widths) + self.COLUMN_GAP * max(len(widths) - 1, 0)
        if density < 2:
            content = max(content, self._caption_width())
        return int(content)

    def _caption_font(self) -> QFont:
        font = QFont(self.font())
        font.setPointSizeF(max(font.pointSizeF() * self.CAPTION_SCALE, 6.0))
        return font

    def _caption_width(self) -> float:
        if not self._title:
            return 0.0
        return QFontMetricsF(self._caption_font()).horizontalAdvance(self._title) + 2 * self.CAPTION_PAD

    def sizeHint(self) -> QSize:
        height = HaloToolButton.LARGE_H + self.CAPTION_H
        caption = 0.0 if self._elide_caption else self._caption_width()
        return QSize(int(max(self.layout().sizeHint().width(), caption)), height)

    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event) -> None:
        if not self._title:
            return
        painter = QPainter(self)
        ink = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        painter.setPen(_faded(ink, self.CAPTION_ALPHA))
        font = self._caption_font()
        painter.setFont(font)
        box = QRectF(self.CAPTION_PAD, self.height() - self.CAPTION_H,
                     self.width() - 2 * self.CAPTION_PAD, self.CAPTION_H)
        shown = QFontMetricsF(font).elidedText(self._title, Qt.TextElideMode.ElideRight, box.width())
        painter.drawText(box, int(Qt.AlignmentFlag.AlignCenter), shown)
        painter.end()


class HaloCommandBar(QWidget):
    """Befehlsleiste aus Gruppen mit Überschrift — das Menüband der Halo-Sammlung.

    ```python
    bar = HaloCommandBar()
    file = bar.add_group("File")
    file.add_action(open_action)                  # groß
    file.add_action(save_action, "small")         # klein, stapeln sich zu zweit
    bar.add_stretch()                             # alles danach steht rechts
    bar.add_group("Help").add_action(help_action)
    ```

    Zwischen sichtbaren Gruppen steht ein feiner Trennstrich, unten eine blasse
    Grundlinie über die ganze Breite. Wird die Leiste zu schmal, sinkt die
    Dichte (`density()`): erst verlieren die kleinen Knöpfe die Schrift, dann
    die großen, und die Überschriften werden gekürzt. Die Höhe bleibt gleich.
    """

    PAD_X           = 6
    PAD_Y           = 4
    GROUP_SPACING   = 13     # der Trennstrich steht in der Mitte
    SEPARATOR_ALPHA = 0.15
    BASE_ALPHA      = 0.15

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._items: list[HaloCommandGroup | None] = []   # None = Stretch
        self._density = 0
        self._pending = False

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(self.PAD_X, self.PAD_Y, self.PAD_X, self.PAD_Y + 1)
        self._layout.setSpacing(self.GROUP_SPACING)
        # Ohne das setzt Qt die Mindestbreite der Leiste auf die Summe der
        # Gruppen bei VOLLER Beschriftung — das Fenster könnte dann nie so
        # schmal werden, dass die Leiste ihre Dichte erhöht.
        self._layout.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)

    def add_group(self, title: str = "") -> HaloCommandGroup:
        group = HaloCommandGroup(title, self)
        # Ein- und Ausblenden einer Gruppe ändert die nötige Breite.
        group.installEventFilter(self)
        self._layout.addWidget(group, 0, Qt.AlignmentFlag.AlignTop)
        self._items.append(group)
        self._schedule_density()
        return group

    def add_stretch(self) -> None:
        self._layout.addStretch(1)
        self._items.append(None)

    def groups(self) -> list[HaloCommandGroup]:
        return [item for item in self._items if item is not None]

    def density(self) -> int:
        return self._density

    # ==============================
    # Dichte
    # ==============================

    def width_for(self, density: int) -> int:
        visible = [g for g in self.groups() if not g.isHidden()]
        content = sum(g.width_for(density) for g in visible)
        content += self.GROUP_SPACING * max(len(visible) - 1, 0)
        return content + 2 * self.PAD_X

    def _height(self) -> int:
        return HaloToolButton.LARGE_H + HaloCommandGroup.CAPTION_H + 2 * self.PAD_Y + 1

    def sizeHint(self) -> QSize:
        return QSize(self.width_for(0), self._height())

    def minimumSizeHint(self) -> QSize:
        return QSize(self.width_for(_DENSITIES[-1]), self._height())

    def _schedule_density(self) -> None:
        # Gesammelt und nach dem laufenden Ereignis: sonst würde jede
        # Größenänderung mitten im Layoutlauf eine weitere auslösen.
        if not self._pending:
            self._pending = True
            QTimer.singleShot(0, self._update_density)

    def _update_density(self) -> None:
        self._pending = False
        available = self.width()
        density = next((d for d in _DENSITIES if self.width_for(d) <= available), _DENSITIES[-1])
        self._density = density
        for group in self.groups():
            group.apply_density(density)
        self.updateGeometry()
        self.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._schedule_density()

    def eventFilter(self, obj, event) -> bool:
        if event.type() in (QEvent.Type.Show, QEvent.Type.Hide) and obj in self._items:
            self._schedule_density()
            self.update()
        return super().eventFilter(obj, event)

    # ==============================
    # Zeichnen
    # ==============================

    def separator_positions(self) -> list[float]:
        """x-Lage der Trennstriche: zwischen zwei sichtbaren Gruppen, nie über den Stretch hinweg."""
        positions = []
        previous: HaloCommandGroup | None = None
        for item in self._items:
            if item is None:
                previous = None
                continue
            if item.isHidden():
                continue
            if previous is not None:
                gap_left = previous.geometry().right() + 1
                positions.append((gap_left + item.geometry().left()) / 2.0)
            previous = item
        return positions

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        ink = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        top = self.PAD_Y + 6.0
        bottom = self.height() - self.PAD_Y - 6.0
        painter.setPen(QPen(_faded(ink, self.SEPARATOR_ALPHA), 1.0))
        for x in self.separator_positions():
            x = round(x) + 0.5
            painter.drawLine(QPointF(x, top), QPointF(x, bottom))
        painter.setPen(QPen(_faded(ink, self.BASE_ALPHA), 1.0))
        y = self.height() - 0.5
        painter.drawLine(QPointF(0.0, y), QPointF(float(self.width()), y))
        painter.end()
