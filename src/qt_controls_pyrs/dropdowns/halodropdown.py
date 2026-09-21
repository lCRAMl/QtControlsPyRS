# halodropdown.py
#
# Auswahlfeld im Stil der Halo-Knöpfe. Beim Aufklappen rollt das Feld von der
# Leiste aus auf; jeder Eintrag blendet ein und gleitet ein paar Pixel nach,
# sobald die Kante ihn erreicht.
#
# Bewegt werden nur Lage, Deckkraft und die Kante. Skaliert wird nichts: Qt
# zeichnet Schrift bei jeder Zwischengröße neu, und die Buchstaben rasten dabei
# auf andere Pixel — skalierte Schrift wirkt unruhig, verschobene nicht.

from __future__ import annotations

import math
import re
import time
import unicodedata

from PyQt6.QtCore import (
    QAbstractAnimation, QEasingCurve, QEvent, QPointF, QPropertyAnimation, QRect,
    QRectF, QSize, Qt, pyqtProperty
)
from PyQt6.QtGui import (
    QBrush, QColor, QCursor, QFont, QFontMetricsF, QGuiApplication, QPainter,
    QPainterPath, QPalette, QPen, QPolygonF, QStandardItemModel
)
from PyQt6.QtWidgets import QApplication, QComboBox, QWidget

from ..buttons.hoverbuttons import _crisp, _faded, _glow, _mix, _outline

# Hier legt das Dropdown den Sortierschlüssel ab, wenn SORTED gesetzt ist.
_SORT_ROLE = Qt.ItemDataRole.UserRole + 101


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _out_cubic(t: float) -> float:
    """Schnell los, weich aus."""
    return 1.0 - (1.0 - _clamp(t)) ** 3


def _rounded(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    if radius > 0.0:
        path.addRoundedRect(rect, radius, radius)
    else:
        path.addRect(rect)
    return path


def _folded(text: str) -> str:
    """Zum Vergleichen: klein und ohne Akzente — aus „Äpfel" wird „apfel"."""
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _sort_key(text: str) -> str:
    """Deutsch sortiert: Ä bei A, ohne Groß/Klein, Zahlen nach ihrer Größe."""
    return re.sub(r"\d+", lambda m: m.group().zfill(12), _folded(text))


class HaloDropdown(QComboBox):
    """Auswahlfeld mit Halo-Rahmen, dessen Liste weich aufgeht.

    Nach außen bleibt es eine QComboBox: `addItem()`, `addItems()`, `clear()`,
    `currentText()`, `currentIndex()`, `setCurrentIndex()`,
    `setPlaceholderText()` und die Signale `currentIndexChanged`,
    `currentTextChanged`, `activated` funktionieren unverändert. Nur zeichnet
    es sich selbst und bringt seine eigene Liste mit.

    Die Leiste sieht aus wie ein `PulseHaloButton` in Ruhe: ein feiner,
    halbdurchsichtiger Rahmen, innen nichts. Unter der Maus wird der Rahmen weiß
    und innen glimmt es auf, ohne den Strich, der beim Halo nach außen wandert.
    Rechts zeigt ein Pfeil nach unten; ist die Liste offen, dreht er sich nach
    links. Wechselt die Auswahl, blendet der Text in der Leiste über.

    Beim Aufklappen rollt das dunkle Feld von der Leiste aus auf, und jeder
    Eintrag blendet ein und gleitet nach, sobald die Kante ihn erreicht. Die
    Markierung gleitet von Eintrag zu Eintrag, lange Listen rollen weich. Nach
    einem Klick leuchtet der gewählte Eintrag kurz auf, dann klappt die Liste
    als Ganzes schnell zu.

    Ein Buchstabe springt zum ersten passenden Eintrag, wiederholt durch alle
    mit diesem Buchstaben; schnell getippt sucht er nach dem ganzen Anfang —
    offen wie geschlossen. `SORTED` sortiert die Einträge dazu deutsch.
    `flash()` lässt den Rahmen kurz rot blinken.

    Nicht unterstützt: `setEditable(True)` — dafür bräuchte es ein Eingabefeld
    in der Leiste, das dieses Widget nicht zeichnet.
    """

    # --- Leiste: wie der PulseHaloButton ---
    HEIGHT        = 45        # Höhe der Fläche
    ROOM          = 16        # Rand links und rechts — bündig mit den Halo-Knöpfen
    ROOM_Y        = 4         # Rand oben und unten
    PAD           = 16        # Abstand der Schrift zum Rahmen
    RADIUS        = 0         # Eckenradius von Leiste und Liste
    ALIGN         = Qt.AlignmentFlag.AlignLeft   # Lage der Schrift in der Leiste
    UPPERCASE     = False
    OUTLINE_ALPHA = 0.5       # Deckkraft des Rahmens in Ruhe
    INNER_GLOW    = 20        # innerer Schein unter der Maus
    HOVER_MS      = 1250
    SHADOW_COLOR  = "#427388"
    SWAP_MS       = 200       # Text in der Leiste blendet über

    # --- Pfeil ---
    ARROW    = 5              # halbe Breite des Pfeils
    ARROW_MS = 200            # Drehung von ↓ nach ←

    # --- Liste ---
    ITEM_HEIGHT = 32
    LIST_PAD    = 4           # Rand innen, oben und unten
    GAP         = 6           # Abstand zwischen Leiste und Liste
    HIGHLIGHT   = "#5a8cff"   # Markierung des Eintrags unter der Maus
    SORTED      = False       # Einträge deutsch sortieren (Ä bei A, 2 vor 10)
    GLIDE_MS    = 120         # Markierung gleitet zum nächsten Eintrag
    SCROLL_MS   = 160         # weiches Rollen

    # --- Aufklappen: das Feld rollt auf, die Einträge gleiten nach ---
    UNFOLD_MS   = 200         # so lange rollt das Feld auf
    ITEM_MS     = 160         # so lange gleitet ein Eintrag an seinen Platz
    SLIDE       = 8           # so weit gleitet er dabei, in Pixeln

    # --- Zuklappen: als Ganzes ---
    CONFIRM_MS  = 120         # gewählter Eintrag leuchtet auf
    CLOSE_MS    = 150         # dann blendet die Liste aus
    CLOSE_SLIDE = 6           # und gleitet dabei so weit zur Leiste zurück

    # --- flash() ---
    FLASH_COLOR = "#ff4d4d"
    FLASH_MS    = 600         # Dauer insgesamt
    FLASH_COUNT = 3           # so oft blinkt der Rahmen

    def __init__(self, parent: QWidget | None = None) -> None:
        self._hover = 0.0         # 0 = Ruhe, 1 = unter der Maus oder offen
        self._arrow = 0.0         # 0 = zeigt nach unten, 1 = nach links
        self._swap = 1.0          # 1 = neuer Text ganz da
        self._flash = 0.0         # 0 = kein Rot, 1 = ganz rot
        self._old_text = ""       # was vor dem Wechsel in der Leiste stand
        self._old_dim = False     # ... und ob es der Platzhalter war
        self._shown = ("", False)
        self._typed = ""          # Buchstabensuche: bisher Getipptes
        self._typed_at = 0.0
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._hover_anim = self._animation(b"hover", self.HOVER_MS, QEasingCurve.Type.OutExpo)
        self._arrow_anim = self._animation(b"arrow", self.ARROW_MS, QEasingCurve.Type.InOutCubic)
        self._swap_anim = self._animation(b"swap", self.SWAP_MS, QEasingCurve.Type.InOutCubic)
        self._flash_anim = self._animation(b"flash_level", self.FLASH_MS, QEasingCurve.Type.Linear)

        self._popup = _DropdownPopup(self)
        self.currentIndexChanged.connect(self._on_index_changed)

    def _animation(self, name: bytes, duration: int, curve) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setDuration(duration)
        anim.setEasingCurve(curve)
        return anim

    # ==============================
    # QComboBox: Liste auf und zu
    # ==============================

    def showPopup(self) -> None:
        if self.count() == 0 or not self.isEnabled() or self._popup.is_open():
            return
        self._popup.open_for(self)
        self._run(self._arrow_anim, self._arrow, 1.0)
        self._run(self._hover_anim, self._hover, 1.0)

    def hidePopup(self) -> None:
        if self._popup.is_open():
            self._popup.close_animated()
            self._run(self._arrow_anim, self._arrow, 0.0)

    def is_open(self) -> bool:
        """Ist die Liste gerade aufgeklappt (oder klappt noch auf)?"""
        return self._popup.is_open()

    def popup(self) -> QWidget:
        """Die Liste selbst — für Tests und Bildschirmfotos."""
        return self._popup

    def _choose(self, index: int) -> None:
        """Ein Eintrag wurde in der Liste gewählt — wie bei einer QComboBox."""
        self.setCurrentIndex(index)
        self.activated.emit(index)
        self.textActivated.emit(self.itemText(index))
        self._popup.confirm_then_close(index)
        self._run(self._arrow_anim, self._arrow, 0.0)

    def _popup_closed(self) -> None:
        """Die Liste ist ganz weg — Pfeil und Leiste nachziehen."""
        self._run(self._arrow_anim, self._arrow, 0.0)
        # Während die Liste offen war, hat die Leiste keine Maus-Ereignisse
        # bekommen. Wo der Zeiger jetzt steht, muss sie selbst nachsehen.
        over = self.underMouse() and self.rect().contains(
            self.mapFromGlobal(QCursor.pos())
        )
        self._run(self._hover_anim, self._hover, 1.0 if over else 0.0)

    # ==============================
    # flash()
    # ==============================

    def flash(self, count: int | None = None) -> None:
        """Lässt den Rahmen kurz rot aufblinken — etwa, wenn noch eine Wahl fehlt.

        Auch ein gesperrtes Feld blinkt kräftig: gerade dann soll man es sehen.
        """
        times = max(int(count or self.FLASH_COUNT), 1)
        self._flash_anim.stop()
        self._flash_anim.setDuration(self.FLASH_MS)
        self._flash_anim.setKeyValues([])
        steps = 2 * times
        for step in range(steps + 1):
            self._flash_anim.setKeyValueAt(step / steps, 1.0 if step % 2 else 0.0)
        self._flash_anim.start()

    # ==============================
    # Sortieren
    # ==============================

    def addItem(self, *args, **kwargs) -> None:
        super().addItem(*args, **kwargs)
        self._resort()

    def addItems(self, texts) -> None:
        super().addItems(texts)
        self._resort()

    def insertItem(self, *args, **kwargs) -> None:
        super().insertItem(*args, **kwargs)
        self._resort()

    def insertItems(self, index: int, texts) -> None:
        super().insertItems(index, texts)
        self._resort()

    def _resort(self) -> None:
        """Mit SORTED: deutsch sortieren. Die Auswahl bleibt am selben Eintrag."""
        if not self.SORTED or self.count() < 2:
            return
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            return
        for row in range(model.rowCount()):
            item = model.item(row)
            if item is not None:
                item.setData(_sort_key(item.text()), _SORT_ROLE)
        model.setSortRole(_SORT_ROLE)
        model.sort(0, Qt.SortOrder.AscendingOrder)

    # ==============================
    # Buchstabensuche
    # ==============================

    def find_typed(self, char: str, current: int) -> int:
        """Buchstabensuche wie in Qt-Listen.

        Ein Buchstabe springt zum nächsten Eintrag, der damit beginnt — wieder-
        holt also durch alle mit diesem Buchstaben. Schnell hintereinander
        getippt, zählt der ganze Anfang: „sc" springt zu „Schatten", nicht zum
        nächsten „S…". Groß/Klein und Akzente zählen nicht: „a" findet „Äpfel".
        """
        now = time.monotonic()
        if now - self._typed_at > QApplication.keyboardInputInterval() / 1000.0:
            self._typed = ""
        self._typed_at = now
        self._typed += _folded(char)

        typed = self._typed
        repeated = len(typed) > 1 and typed == typed[0] * len(typed)
        needle = typed[0] if repeated else typed
        # Ein einzelner Buchstabe sucht ab dem nächsten Eintrag, ein längerer
        # Anfang ab dem aktuellen — sonst spränge „sc" über den Treffer hinweg.
        start = current + 1 if len(needle) == 1 else max(current, 0)
        count = self.count()
        for step in range(count):
            index = (start + step) % count
            if _folded(self.itemText(index)).startswith(needle):
                return index
        return -1

    @staticmethod
    def _is_typed(event) -> bool:
        text = event.text()
        plain = not (event.modifiers() & (
            Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier
        ))
        return bool(text) and plain and text.isprintable() and not text.isspace()

    def keyPressEvent(self, event) -> None:
        # Geschlossen wählt ein Buchstabe direkt aus — mit derselben Suche wie
        # in der offenen Liste, damit sich beides gleich anfühlt.
        if self._is_typed(event) and self.count():
            index = self.find_typed(event.text(), self.currentIndex())
            if index >= 0 and index != self.currentIndex():
                self.setCurrentIndex(index)
                self.activated.emit(index)
                self.textActivated.emit(self.itemText(index))
            event.accept()
            return
        super().keyPressEvent(event)

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
    def arrow(self) -> float:
        return self._arrow

    @arrow.setter
    def arrow(self, value: float) -> None:
        self._arrow = value
        self.update()

    @pyqtProperty(float)
    def swap(self) -> float:
        return self._swap

    @swap.setter
    def swap(self, value: float) -> None:
        self._swap = value
        self.update()

    @pyqtProperty(float)
    def flash_level(self) -> float:
        return self._flash

    @flash_level.setter
    def flash_level(self, value: float) -> None:
        self._flash = value
        self.update()

    @staticmethod
    def _run(anim: QPropertyAnimation, current: float, target: float) -> None:
        anim.stop()
        anim.setStartValue(current)
        anim.setEndValue(target)
        anim.start()

    # ==============================
    # Leistentext
    # ==============================

    def _display(self) -> tuple[str, bool]:
        """Was in der Leiste steht — und ob es der gedimmte Platzhalter ist."""
        if self.currentIndex() < 0:
            return self.placeholderText(), True
        return self.currentText(), False

    def _on_index_changed(self, index: int) -> None:
        shown = self._display()
        if shown == self._shown:
            # Nur umsortiert: derselbe Eintrag an anderer Stelle.
            return
        self._old_text, self._old_dim = self._shown
        self._shown = shown
        if not self.isVisible():
            # Noch nicht zu sehen (etwa beim ersten Befüllen): nichts überblenden,
            # sonst stünde die Leiste beim Erscheinen kurz leer da.
            self._swap_anim.stop()
            self._swap = 1.0
            return
        self._run(self._swap_anim, 0.0, 1.0)

    # ==============================
    # Mauszustand
    # ==============================

    def enterEvent(self, event) -> None:
        super().enterEvent(event)
        self._run(self._hover_anim, self._hover, 1.0)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)
        # Offen bleibt die Leiste hell, sie gehört ja zur Liste.
        if not self.is_open():
            self._run(self._hover_anim, self._hover, 0.0)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if event.type() == QEvent.Type.EnabledChange and not self.isEnabled():
            self.hidePopup()
            self._run(self._hover_anim, self._hover, 0.0)

    def wheelEvent(self, event) -> None:
        # Offen gehört das Rad der Liste, nicht der Auswahl.
        if self.is_open():
            event.ignore()
            return
        super().wheelEvent(event)

    # ==============================
    # Geometrie
    # ==============================

    def _cased(self, text: str) -> str:
        return text.upper() if self.UPPERCASE else text

    def _surface(self) -> QRectF:
        room_x = min(float(self.ROOM), self.width() / 4.0)
        room_y = min(float(self.ROOM_Y), self.height() / 4.0)
        return QRectF(self.rect()).adjusted(room_x, room_y, -room_x, -room_y)

    def _arrow_space(self) -> float:
        return 2 * self.ARROW + self.PAD

    def sizeHint(self) -> QSize:
        metrics = QFontMetricsF(self.font())
        texts = [self._cased(self.itemText(i)) for i in range(self.count())]
        texts.append(self.placeholderText())
        widest = max((metrics.horizontalAdvance(t) for t in texts), default=0.0)
        width = widest + 2 * self.PAD + self._arrow_space() + 2 * self.ROOM
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    def minimumSizeHint(self) -> QSize:
        width = 2 * self.PAD + self._arrow_space() + 2 * self.ROOM + 40
        return QSize(int(math.ceil(width)), self.HEIGHT + 2 * self.ROOM_Y)

    # ==============================
    # Darstellung: die Leiste
    # ==============================

    def _ink(self) -> QColor:
        # Auch im gesperrten Zustand lesbar bleiben — abgeblasst wird global.
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            painter.setOpacity(0.4)

        rect = self._surface()
        ink = self._ink()
        hover = _clamp(self._hover)
        radius = float(self.RADIUS)

        # Unter der Maus glimmt es innen auf — wie beim Halo, aber ohne den
        # Strich, der dort nach außen wandert.
        if hover > 0.0:
            _glow(painter, rect, _faded(ink, 0.5 * hover), self.INNER_GLOW,
                  inside=True, radius=radius)

        # Der Rahmen: halbdurchsichtig in Ruhe, weiß unter der Maus.
        alpha = self.OUTLINE_ALPHA + (1.0 - self.OUTLINE_ALPHA) * hover
        painter.setPen(QPen(_faded(ink, alpha), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(rect, 1.0), max(radius - 0.5, 0.0))

        self._paint_text(painter, rect, ink, hover)
        self._paint_arrow(painter, rect, ink, hover)
        self._paint_flash(painter, rect)
        painter.end()

    def _paint_flash(self, painter: QPainter, rect: QRectF) -> None:
        level = _clamp(self._flash)
        if level <= 0.0:
            return
        painter.save()
        # Kräftig, auch wenn das Feld gesperrt ist.
        painter.setOpacity(1.0)
        red = QColor(self.FLASH_COLOR)
        radius = float(self.RADIUS)
        _glow(painter, rect, _faded(red, 0.35 * level), self.INNER_GLOW,
              inside=True, radius=radius)
        width = 1.0 + 0.6 * level
        painter.setPen(QPen(_faded(red, level), width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(rect, width), max(radius - width / 2, 0.0))
        painter.restore()

    def _paint_text(self, painter: QPainter, rect: QRectF, ink: QColor, hover: float) -> None:
        box = rect.adjusted(self.PAD, 0, -(self.PAD + self._arrow_space()), 0)
        if box.width() <= 0:
            return
        painter.setFont(self.font())
        swap = _clamp(self._swap)
        text, dim = self._display()

        if swap < 1.0 and (self._old_text, self._old_dim) != (text, dim):
            self._draw_line(painter, box, ink, hover, self._old_text, self._old_dim, 1.0 - swap)
            self._draw_line(painter, box, ink, hover, text, dim, swap)
        else:
            self._draw_line(painter, box, ink, hover, text, dim, 1.0)

    def _draw_line(
        self, painter: QPainter, box: QRectF, ink: QColor, hover: float,
        text: str, dim: bool, opacity: float,
    ) -> None:
        if opacity <= 0.0 or not text:
            return
        shown = QFontMetricsF(self.font()).elidedText(
            self._cased(text), Qt.TextElideMode.ElideRight, box.width()
        )
        flags = int(self.ALIGN | Qt.AlignmentFlag.AlignVCenter)

        painter.save()
        painter.setOpacity(painter.opacity() * opacity)
        if hover > 0.0 and not dim:
            painter.setPen(QPen(_faded(QColor(self.SHADOW_COLOR), hover)))
            painter.drawText(box.translated(1, 1), flags, shown)
        # Der Platzhalter steht gedimmt da — er ist keine Wahl.
        painter.setPen(QPen(_faded(ink, 0.5) if dim else ink))
        painter.drawText(box, flags, shown)
        painter.restore()

    def _paint_arrow(self, painter: QPainter, rect: QRectF, ink: QColor, hover: float) -> None:
        size = float(self.ARROW)
        center = QPointF(rect.right() - self.PAD - size, rect.center().y())

        painter.save()
        painter.translate(center)
        # Rechtsherum um 90 Grad: aus ↓ wird ←.
        painter.rotate(90.0 * _clamp(self._arrow))
        pen = QPen(_faded(ink, 0.7 + 0.3 * hover), 1.6)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPolyline(QPolygonF([
            QPointF(-size, -size / 2),
            QPointF(0.0, size / 2),
            QPointF(size, -size / 2),
        ]))
        painter.restore()


class _DropdownPopup(QWidget):
    """Die aufgeklappte Liste — ein eigenes, durchsichtiges Fenster.

    Das Fenster ist ein paar Pixel größer als die Liste, damit sie beim
    Zuklappen zur Leiste hin gleiten kann. Der Rest bleibt durchsichtig.
    """

    def __init__(self, combo: HaloDropdown) -> None:
        super().__init__(
            combo,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Der Klick, der die Liste schließt, soll nicht auch noch unten
        # ankommen — sonst klappte ein Klick auf die Leiste sie gleich wieder auf.
        self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)
        self.setMouseTracking(True)

        self._combo = combo
        self._open = False         # Fenster ist da
        self._leaving = False      # Wahl bestätigt oder Zuklappen läuft

        self._list = QRectF()      # Lage der Liste im Fenster
        self._total = 0.0          # Dauer des Aufklappens, in Millisekunden
        self._direction = 1        # 1 = nach unten aufgeklappt, −1 = nach oben
        self._rows = 0             # sichtbare Einträge
        self._open_first = 0       # erster sichtbarer Eintrag beim Aufklappen
        self._hot = -1             # Eintrag unter der Maus oder Tastatur

        self._clock = 0.0          # Millisekunden seit dem Aufklappen
        self._close = 1.0          # 1 = ganz da, 0 = weg
        self._glide = 0.0          # Lage der Markierung, als Eintragsnummer
        self._scroll = 0.0         # erster sichtbarer Eintrag, fließend
        self._scroll_target = 0.0
        self._confirm = 0.0        # Aufleuchten des gewählten Eintrags

        self._open_anim = self._animation(b"clock", QEasingCurve.Type.Linear)
        # Schnell los, weich aus — nach einer Wahl soll die Liste sofort reagieren.
        self._close_anim = self._animation(b"close_level", QEasingCurve.Type.OutCubic)
        self._close_anim.finished.connect(self._on_closed)
        self._glide_anim = self._animation(b"glide", QEasingCurve.Type.OutCubic)
        self._scroll_anim = self._animation(b"scroll", QEasingCurve.Type.OutCubic)
        self._confirm_anim = self._animation(b"confirm", QEasingCurve.Type.Linear)
        self._confirm_anim.finished.connect(self.close_animated)

    def _animation(self, name: bytes, curve) -> QPropertyAnimation:
        anim = QPropertyAnimation(self, name, self)
        anim.setEasingCurve(curve)
        return anim

    # ------------------------------------------------------------------
    # Auf- und Zuklappen
    # ------------------------------------------------------------------

    def is_open(self) -> bool:
        return self._open and not self._leaving

    def settled(self) -> bool:
        """Sind alle Einträge an ihrem Platz?"""
        return self._open and self._open_anim.state() != QAbstractAnimation.State.Running

    def open_for(self, combo: HaloDropdown) -> None:
        """Legt die Liste unter (oder über) die Leiste und lässt sie hereinfliegen."""
        surface = combo._surface()
        top_left = combo.mapToGlobal(surface.topLeft().toPoint())
        bar = QRectF(QPointF(top_left), surface.size())

        screen = QGuiApplication.screenAt(bar.center().toPoint()) or QGuiApplication.primaryScreen()
        area = QRectF(screen.availableGeometry())

        row_h = combo.ITEM_HEIGHT
        chrome = 2 * combo.LIST_PAD + combo.GAP
        below = area.bottom() - bar.bottom() - chrome
        above = bar.top() - area.top() - chrome
        wanted = min(combo.count(), max(combo.maxVisibleItems(), 1))

        self._direction = 1
        room = below
        if wanted * row_h > below and above > below:
            self._direction, room = -1, above
        self._rows = max(1, min(wanted, int(room // row_h)))

        height = self._rows * row_h + 2 * combo.LIST_PAD
        if self._direction > 0:
            top = bar.bottom() + combo.GAP
        else:
            top = bar.top() - combo.GAP - height
        listed = QRectF(bar.left(), top, bar.width(), height)

        # Ein paar Pixel Luft rundum, damit die Liste beim Zuklappen zur
        # Leiste gleiten kann, ohne am Fensterrand anzustoßen.
        margin = int(math.ceil(combo.CLOSE_SLIDE)) + 4
        window = QRect(
            int(listed.left()) - margin, int(listed.top()) - margin,
            int(listed.width()) + 2 * margin, int(height) + 2 * margin,
        )
        self.setGeometry(window)
        self._list = QRectF(listed.translated(-window.left(), -window.top()))

        # Die aktuelle Auswahl steht in der Liste, und die Tastatur beginnt dort.
        current = combo.currentIndex()
        anchor = max(current, 0)
        first = max(0, min(anchor - self._rows + 1, combo.count() - self._rows))
        self._open_first = first
        self._scroll = self._scroll_target = float(first)
        self._hot = current
        self._glide = float(max(current, 0))

        self._open, self._leaving = True, False
        self._close = 1.0
        self._clock = 0.0
        self._confirm = 0.0
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

        self._total = self._start_time(self._rows - 1) + combo.ITEM_MS
        self._run(self._open_anim, 0.0, self._total, int(math.ceil(self._total)))

    def close_animated(self) -> None:
        """Die ganze Liste blendet aus und weicht dabei ein wenig zurück."""
        if not self._open or self._close_anim.state() == QAbstractAnimation.State.Running:
            return
        self._leaving = True
        self._confirm_anim.stop()
        self._run(self._close_anim, self._close, 0.0, self._combo.CLOSE_MS)

    def confirm_then_close(self, index: int) -> None:
        """Der gewählte Eintrag leuchtet einmal auf, dann klappt die Liste zu."""
        if not self._open or self._leaving:
            return
        self._leaving = True
        self._hot = index
        self._open_anim.stop()
        self._clock = self._total
        self._run(self._glide_anim, self._glide, float(index), self._combo.GLIDE_MS)

        self._confirm_anim.stop()
        self._confirm_anim.setDuration(max(self._combo.CONFIRM_MS, 1))
        self._confirm_anim.setKeyValues([])
        self._confirm_anim.setKeyValueAt(0.0, 0.0)
        self._confirm_anim.setKeyValueAt(0.5, 1.0)
        self._confirm_anim.setKeyValueAt(1.0, 0.0)
        self._confirm_anim.start()

    def _on_closed(self) -> None:
        if self._leaving and self._close <= 0.0:
            self.hide()

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        # Auch wenn Qt das Fenster selbst schließt (etwa beim Wechsel in ein
        # anderes Programm), muss die Leiste davon erfahren.
        if self._open:
            self._open, self._leaving = False, False
            for anim in (self._open_anim, self._close_anim, self._glide_anim,
                         self._scroll_anim, self._confirm_anim):
                anim.stop()
            self._combo._popup_closed()

    @staticmethod
    def _run(anim: QPropertyAnimation, start: float, end: float, duration: int) -> None:
        anim.stop()
        anim.setDuration(max(int(duration), 1))
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.start()

    # ------------------------------------------------------------------
    # Animierte Eigenschaften
    # ------------------------------------------------------------------

    @pyqtProperty(float)
    def clock(self) -> float:
        return self._clock

    @clock.setter
    def clock(self, value: float) -> None:
        self._clock = value
        self.update()

    @pyqtProperty(float)
    def close_level(self) -> float:
        return self._close

    @close_level.setter
    def close_level(self, value: float) -> None:
        self._close = value
        self.update()

    @pyqtProperty(float)
    def glide(self) -> float:
        return self._glide

    @glide.setter
    def glide(self, value: float) -> None:
        self._glide = value
        self.update()

    @pyqtProperty(float)
    def scroll(self) -> float:
        return self._scroll

    @scroll.setter
    def scroll(self, value: float) -> None:
        self._scroll = value
        self.update()

    @pyqtProperty(float)
    def confirm(self) -> float:
        return self._confirm

    @confirm.setter
    def confirm(self, value: float) -> None:
        self._confirm = value
        self.update()

    def _slot(self, index: int) -> int:
        """Platz eines Eintrags, von der Leiste aus gezählt."""
        slot = min(max(index - self._open_first, 0), self._rows - 1)
        return self._rows - 1 - slot if self._direction < 0 else slot

    def _start_time(self, slot: int) -> float:
        """Wann ein Eintrag zu gleiten beginnt, in Millisekunden."""
        combo = self._combo
        # Wenn die Kante den Eintrag erreicht. Die Kante läuft schnell los und
        # weich aus; hier steht ihr Weg zurückgerechnet in Zeit. Deshalb dauert
        # das Aufklappen bei 3 wie bei 10 Einträgen fast gleich lang.
        height = self._list.height() or 1.0
        reached = _clamp((combo.LIST_PAD + slot * combo.ITEM_HEIGHT) / height)
        return combo.UNFOLD_MS * (1.0 - (1.0 - reached) ** (1.0 / 3.0))

    def edge(self) -> float:
        """Wie weit das Feld schon aufgerollt ist, 0..1."""
        if self._leaving or not self._open:
            return 1.0
        return _out_cubic(self._clock / max(self._combo.UNFOLD_MS, 1))

    def item_progress(self, index: int) -> float:
        """Wie weit ein Eintrag schon an seinem Platz ist, 0..1.

        Der Eintrag an der Leiste kommt zuerst — klappt die Liste nach oben
        auf, also von unten nach oben.
        """
        if self._leaving or not self._open:
            return 1.0
        start = self._start_time(self._slot(index))
        return _clamp((self._clock - start) / max(self._combo.ITEM_MS, 1))

    def field_rect(self) -> QRectF:
        """Der sichtbare Teil des Feldes — beim Aufrollen wächst er von der Leiste aus."""
        grown = self._list.height() * self.edge()
        if self._direction > 0:
            return QRectF(self._list.left(), self._list.top(), self._list.width(), grown)
        return QRectF(self._list.left(), self._list.bottom() - grown, self._list.width(), grown)

    # ------------------------------------------------------------------
    # Einträge
    # ------------------------------------------------------------------

    def _row_top(self, index: float) -> float:
        return self._list.top() + self._combo.LIST_PAD + (index - self._scroll) * self._combo.ITEM_HEIGHT

    def _inner(self) -> QRectF:
        pad = self._combo.LIST_PAD
        return self._list.adjusted(0, pad, 0, -pad)

    def index_at(self, pos: QPointF) -> int:
        """Der Eintrag an dieser Stelle der ruhenden Liste, oder −1."""
        if not self._inner().contains(pos):
            return -1
        combo = self._combo
        index = int(math.floor((pos.y() - self._list.top() - combo.LIST_PAD) / combo.ITEM_HEIGHT + self._scroll))
        return index if 0 <= index < combo.count() else -1

    def _max_scroll(self) -> float:
        return float(max(self._combo.count() - self._rows, 0))

    def _scroll_to(self, target: float) -> None:
        self._scroll_target = max(0.0, min(target, self._max_scroll()))
        self._run(self._scroll_anim, self._scroll, self._scroll_target, self._combo.SCROLL_MS)

    def _ensure_visible(self, index: int) -> None:
        if index < self._scroll_target:
            self._scroll_to(float(index))
        elif index > self._scroll_target + self._rows - 1:
            self._scroll_to(float(index - self._rows + 1))

    def _set_hot(self, index: int) -> None:
        if index == self._hot or index < 0:
            return
        self._hot = index
        self._run(self._glide_anim, self._glide, float(index), self._combo.GLIDE_MS)
        self._ensure_visible(index)

    def _move_hot(self, step: int) -> None:
        count = self._combo.count()
        if count == 0:
            return
        start = self._hot if self._hot >= 0 else max(self._combo.currentIndex(), 0) - (1 if step > 0 else 0)
        self._set_hot(max(0, min(start + step, count - 1)))

    # ------------------------------------------------------------------
    # Maus und Tastatur
    # ------------------------------------------------------------------

    def mouseMoveEvent(self, event) -> None:
        if not self._leaving:
            self._set_hot(self.index_at(event.position()))

    def mousePressEvent(self, event) -> None:
        # Daneben — auch außerhalb des Fensters, das die Maus festhält —
        # heißt: zuklappen. Die Animation übernimmt, nicht Qt.
        if not self._list.contains(event.position()):
            if not self._leaving:
                self._combo.hidePopup()
            return
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if self._leaving:
            return
        index = self.index_at(event.position())
        if index >= 0:
            self._combo._choose(index)

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps and self._combo.count() > self._rows:
            self._scroll_to(self._scroll_target - steps)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if self._leaving:
            return
        combo = self._combo
        key = event.key()
        if key == Qt.Key.Key_Escape:
            combo.hidePopup()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            if self._hot >= 0:
                combo._choose(self._hot)
            else:
                combo.hidePopup()
        elif key == Qt.Key.Key_Up:
            self._move_hot(-1)
        elif key == Qt.Key.Key_Down:
            self._move_hot(1)
        elif key == Qt.Key.Key_PageUp:
            self._move_hot(-self._rows)
        elif key == Qt.Key.Key_PageDown:
            self._move_hot(self._rows)
        elif key == Qt.Key.Key_Home:
            self._move_hot(-combo.count())
        elif key == Qt.Key.Key_End:
            self._move_hot(combo.count())
        elif combo._is_typed(event):
            index = combo.find_typed(event.text(), self._hot)
            if index >= 0:
                self._set_hot(index)
        else:
            super().keyPressEvent(event)

    # ------------------------------------------------------------------
    # Darstellung
    # ------------------------------------------------------------------

    def paintEvent(self, event) -> None:
        if self._list.isEmpty():
            return

        combo = self._combo
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._leaving and self._close < 1.0:
            # Beim Zuklappen blendet die Liste aus und gleitet zur Leiste zurück.
            level = _clamp(self._close)
            painter.setOpacity(level)
            painter.translate(0.0, -self._direction * combo.CLOSE_SLIDE * (1.0 - level))

        field = self.field_rect()
        if field.height() < 1.0:
            painter.end()
            return

        palette = combo.palette()
        ink = palette.color(QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText)
        radius = float(combo.RADIUS)
        shape = _rounded(field, radius)

        painter.fillPath(shape, QBrush(palette.color(QPalette.ColorRole.Base)))

        # Alles Weitere bleibt im Feld — nichts ragt über seinen Rand.
        painter.save()
        painter.setClipRect(self._inner().intersected(field))
        painter.setClipPath(shape, Qt.ClipOperation.IntersectClip)

        first = int(math.floor(self._scroll))
        last = min(first + self._rows + 1, combo.count())
        self._paint_highlight(painter)
        for index in range(first, last):
            self._paint_row(painter, index, ink)
        self._paint_scrollbar(painter, ink)
        painter.restore()

        # Derselbe feine Rahmen wie an der Leiste, um den sichtbaren Teil.
        painter.setPen(QPen(_faded(ink, combo.OUTLINE_ALPHA), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(field, 1.0), max(radius - 0.5, 0.0))
        painter.end()

    def _arrive(self, painter: QPainter, index: int) -> bool:
        """Deckkraft und Lage für einen Eintrag, der noch gleitet.

        False heißt: noch nicht zu sehen.
        """
        progress = self.item_progress(index)
        if progress <= 0.0:
            return False
        if progress < 1.0:
            eased = _out_cubic(progress)
            painter.setOpacity(painter.opacity() * eased)
            # Von der Leiste weg gleitet er heran: aufgeklappt nach unten also
            # von oben, nach oben aufgeklappt von unten.
            painter.translate(0.0, -self._direction * self._combo.SLIDE * (1.0 - eased))
        return True

    def _paint_highlight(self, painter: QPainter) -> None:
        if self._hot < 0:
            return
        combo = self._combo
        painter.save()
        if self._arrive(painter, self._hot):
            box = QRectF(self._list.left(), self._row_top(self._glide), self._list.width(), combo.ITEM_HEIGHT)
            # Nach der Wahl leuchtet die Markierung einmal hell auf.
            color = _mix(QColor(combo.HIGHLIGHT), QColor(Qt.GlobalColor.white), 0.55 * _clamp(self._confirm))
            painter.fillRect(box, _faded(color, 0.9))
        painter.restore()

    def _paint_row(self, painter: QPainter, index: int, ink: QColor) -> None:
        combo = self._combo
        painter.save()
        if not self._arrive(painter, index):
            painter.restore()
            return

        box = QRectF(self._list.left(), self._row_top(index), self._list.width(), combo.ITEM_HEIGHT)
        font = QFont(combo.font())
        font.setBold(index == combo.currentIndex())
        painter.setFont(font)

        # Weiß, so weit die gleitende Markierung den Eintrag gerade bedeckt.
        cover = _clamp(1.0 - abs(self._glide - index)) if self._hot >= 0 else 0.0
        painter.setPen(QPen(_mix(ink, QColor(Qt.GlobalColor.white), cover)))

        text_box = box.adjusted(combo.PAD, 0, -combo.PAD, 0)
        text = QFontMetricsF(font).elidedText(
            combo._cased(combo.itemText(index)), Qt.TextElideMode.ElideRight, text_box.width()
        )
        painter.drawText(text_box, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter), text)
        painter.restore()

    def _paint_scrollbar(self, painter: QPainter, ink: QColor) -> None:
        count = self._combo.count()
        if count <= self._rows:
            return
        inner = self._inner()
        length = inner.height() * self._rows / count
        offset = inner.height() * self._scroll / count
        bar = QRectF(inner.right() - 5, inner.top() + offset, 3, length)
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(_faded(ink, 0.35)))
        painter.drawRoundedRect(bar, 1.5, 1.5)
        painter.restore()
