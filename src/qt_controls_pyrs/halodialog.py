# halodialog.py
#
# Dialoge im Halo-Stil statt im Fensterrahmen des Betriebssystems.
#
# HaloDialog ist ein QDialog ohne Windows-Rahmen: eine eigene schmale
# Titelleiste mit Überschrift und Schließknopf, darunter die Fläche für den
# Inhalt, ringsum ein feiner Rahmen mit weichem Schein - derselbe Strich wie
# bei den Halo-Knöpfen. Verschoben wird an der Titelleiste, Escape schließt,
# Enter löst den Standardknopf aus; exec(), accept() und reject() bleiben die
# von QDialog.
#
# HaloMessageBox baut darauf die Rückfrage auf, die sonst QMessageBox wäre:
# ein Symbol für die Art der Meldung, Text, Zusatztext, aufklappbare
# Einzelheiten und Knöpfe mit eigener Beschriftung.

from __future__ import annotations

from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PyQt6.QtWidgets import (
    QAbstractButton, QDialog, QHBoxLayout, QLabel, QPlainTextEdit, QSizePolicy, QVBoxLayout,
    QWidget
)

from .buttons.hoverbuttons import _crisp, _faded, _glow
from .compact import CompactButton
from .formfields import mono_font
from .haloscrollbar import HaloScrollBar


class _CloseButton(QAbstractButton):
    """Kleines X in der Titelleiste; unter der Maus rot hinterlegt."""

    SIZE = 24
    DANGER = "#ff4d4d"

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setToolTip("Schließen (Esc)")

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        hot = self.underMouse()
        if hot:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(_faded(QColor(self.DANGER), 0.85))
            painter.drawRoundedRect(QRectF(self.rect()).adjusted(2, 2, -2, -2), 4, 4)
        pen = QPen(QColor("white") if hot else _faded(ink, 0.75), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        c, r = QPointF(self.width() / 2, self.height() / 2), 4.5
        painter.drawLine(c + QPointF(-r, -r), c + QPointF(r, r))
        painter.drawLine(c + QPointF(-r, r), c + QPointF(r, -r))
        painter.end()


class _TitleBar(QWidget):
    """Überschrift und Schließknopf; wer hier zieht, verschiebt den Dialog."""

    HEIGHT = 34

    def __init__(self, dialog: HaloDialog) -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self._grab: QPoint | None = None
        self.setFixedHeight(self.HEIGHT)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 6, 0)
        self.label = QLabel()
        font = QFont(self.label.font())
        font.setBold(True)
        self.label.setFont(font)
        row.addWidget(self.label, 1)
        self.close_button = _CloseButton(self)
        self.close_button.clicked.connect(dialog.reject)
        row.addWidget(self.close_button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._grab = event.globalPosition().toPoint() - self._dialog.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._grab is not None:
            self._dialog.move(event.globalPosition().toPoint() - self._grab)

    def mouseReleaseEvent(self, event) -> None:
        self._grab = None


class HaloDialog(QDialog):
    """QDialog ohne Betriebssystem-Rahmen, im Stil der Halo-Widgets.

    ```python
    dialog = HaloDialog("Optionen", parent)
    form = QFormLayout(dialog.body)       # Inhalt gehört auf dialog.body
    ...
    if dialog.exec() == QDialog.DialogCode.Accepted:
        ...
    ```

    Der Inhalt gehört auf `body`, nicht direkt auf den Dialog: um die Fläche
    liegen Titelleiste, Rahmen und der Rand für den Schein. Escape schließt
    (reject), Enter löst den Standardknopf aus (`setDefault(True)`).
    """

    SHADOW = 12          # Rand außen, in den der Schein fällt
    RADIUS = 6
    OUTLINE_ALPHA = 0.35
    GLOW_ALPHA = 0.18
    BASE_ALPHA = 0.12    # Linie unter der Titelleiste
    PAD = 14             # Innenrand der Inhaltsfläche

    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        # Durchsichtig außerhalb der Fläche, damit Ecken rund und der Schein weich sind.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(self.SHADOW, self.SHADOW, self.SHADOW, self.SHADOW)
        outer.setSpacing(0)
        self.title_bar = _TitleBar(self)
        outer.addWidget(self.title_bar)
        self.body = QWidget(self)
        self.body.setContentsMargins(self.PAD, self.PAD - 4, self.PAD, self.PAD)
        outer.addWidget(self.body, 1)
        self.setTitle(title)

    def title(self) -> str:
        return self.title_bar.label.text()

    def setTitle(self, title: str) -> None:  # noqa: N802 - Qt-Namensschema
        self.title_bar.label.setText(title)
        self.setWindowTitle(title)       # für Taskleiste und Barrierefreiheit

    def panel_rect(self) -> QRectF:
        return QRectF(self.rect()).adjusted(self.SHADOW, self.SHADOW, -self.SHADOW, -self.SHADOW)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().color(QPalette.ColorGroup.Normal, QPalette.ColorRole.WindowText)
        panel = self.panel_rect()
        radius = float(self.RADIUS)
        _glow(painter, panel, _faded(ink, self.GLOW_ALPHA), self.SHADOW, radius=radius)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.palette().color(QPalette.ColorRole.Window))
        painter.drawRoundedRect(panel, radius, radius)
        painter.setPen(QPen(_faded(ink, self.OUTLINE_ALPHA), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(_crisp(panel, 1.0), radius - 0.5, radius - 0.5)
        y = panel.top() + _TitleBar.HEIGHT + 0.5
        painter.setPen(QPen(_faded(ink, self.BASE_ALPHA), 1.0))
        painter.drawLine(QPointF(panel.left() + 1, y), QPointF(panel.right() - 1, y))
        painter.end()


class _KindIcon(QWidget):
    """Kreis mit ?, ! oder i in der Farbe der Meldungsart."""

    SIZE = 34

    def __init__(self, glyph: str, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._glyph, self._color = glyph, QColor(color)
        self.setFixedSize(self.SIZE, self.SIZE)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        _glow(painter, rect.adjusted(3, 3, -3, -3), _faded(self._color, 0.35), 3,
              inside=True, radius=rect.width() / 2 - 3)
        painter.setPen(QPen(self._color, 1.6))
        painter.setBrush(_faded(self._color, 0.12))
        painter.drawEllipse(rect)
        font = QFont(self.font())
        font.setBold(True)
        font.setPointSizeF(font.pointSizeF() * 1.3)
        painter.setFont(font)
        painter.drawText(rect, int(Qt.AlignmentFlag.AlignCenter), self._glyph)
        painter.end()


class HaloMessageBox(HaloDialog):
    """Rückfrage oder Meldung im Halo-Stil - der Ersatz für QMessageBox.

    ```python
    answer = HaloMessageBox.ask(
        parent, "Ungespeicherte Änderungen", "Projekt hat ungespeicherte Änderungen.",
        "Sollen sie gespeichert werden?", kind="warning",
        buttons=(("save", "Speichern"), ("discard", "Verwerfen"), ("cancel", "Abbrechen")),
        default="save")
    if answer == "save":
        ...
    ```

    `buttons` sind Paare aus Schlüssel und Beschriftung; `ask()` gibt den
    Schlüssel des gedrückten Knopfs zurück, oder None, wenn der Dialog mit
    Escape oder dem X geschlossen wurde - das zählt wie Abbrechen.
    `details` (etwa ein Traceback) stehen hinter einem Knopf zum Aufklappen.
    """

    KINDS = {
        "info": ("i", "#5a8cff"),
        "question": ("?", "#5a8cff"),
        "warning": ("!", "#f0b429"),
        "error": ("!", "#ff4d4d"),
    }
    TEXT_WIDTH = 420
    DETAILS_TEXT = "Details"

    def __init__(self, title: str, text: str, informative: str = "", kind: str = "question",
                 buttons=(("ok", "OK"),), default: str | None = None, details: str = "",
                 parent: QWidget | None = None) -> None:
        if kind not in self.KINDS:
            raise ValueError(f"unbekannte Art {kind!r}, erlaubt: {tuple(self.KINDS)}")
        super().__init__(title, parent)
        self._clicked: str | None = None
        self.buttons: dict[str, CompactButton] = {}

        column = QVBoxLayout(self.body)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(12)
        row = QHBoxLayout()
        row.setSpacing(14)
        glyph, color = self.KINDS[kind]
        row.addWidget(_KindIcon(glyph, color, self), 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setFixedWidth(self.TEXT_WIDTH)
        bold = QFont(self.text_label.font())
        bold.setBold(True)
        self.text_label.setFont(bold)
        texts.addWidget(self.text_label)
        self.informative_label = QLabel(informative)
        self.informative_label.setWordWrap(True)
        self.informative_label.setFixedWidth(self.TEXT_WIDTH)
        self.informative_label.setVisible(bool(informative))
        texts.addWidget(self.informative_label)
        row.addLayout(texts, 1)
        column.addLayout(row)

        self.details = QPlainTextEdit(details)
        self.details.setReadOnly(True)
        self.details.setFont(mono_font())
        self.details.setVerticalScrollBar(HaloScrollBar(self.details))
        self.details.setMinimumHeight(160)
        self.details.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.details.hide()
        column.addWidget(self.details, 1)

        bar = QHBoxLayout()
        bar.setSpacing(8)
        if details:
            toggle = CompactButton(self.DETAILS_TEXT)
            toggle.setCheckable(True)
            toggle.setAutoDefault(False)
            toggle.toggled.connect(self._show_details)
            bar.addWidget(toggle)
            self.details_button = toggle
        bar.addStretch(1)
        for key, label in buttons:
            button = CompactButton(label)
            button.setAutoDefault(False)
            button.clicked.connect(lambda _c=False, k=key: self._finish(k))
            bar.addWidget(button)
            self.buttons[key] = button
        chosen = default if default in self.buttons else next(iter(self.buttons), None)
        if chosen is not None:
            self.buttons[chosen].setDefault(True)
            self.buttons[chosen].setFocus()
        column.addLayout(bar)

    def _show_details(self, shown: bool) -> None:
        self.details.setVisible(shown)
        self.adjustSize()

    def _finish(self, key: str) -> None:
        self._clicked = key
        self.accept()

    def clicked(self) -> str | None:
        """Schlüssel des gedrückten Knopfs; None nach Escape oder X."""
        return self._clicked

    @classmethod
    def ask(cls, parent: QWidget | None, title: str, text: str, informative: str = "",
            kind: str = "question", buttons=(("ok", "OK"),), default: str | None = None,
            details: str = "") -> str | None:
        box = cls(title, text, informative, kind, buttons, default, details, parent)
        box.exec()
        return box.clicked()
