import os

# Tests laufen ohne sichtbare Fenster (muss vor dem Erzeugen der QApplication gesetzt sein).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtGui import QPixmap  # noqa: E402
from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget  # noqa: E402


@pytest.fixture
def paint():
    """Zeichnet ein Widget einmal vollständig — deckt Fehler im paintEvent auf."""
    def _paint(widget: QWidget) -> QPixmap:
        pixmap = QPixmap(widget.size())
        widget.render(pixmap)
        return pixmap
    return _paint


@pytest.fixture
def host(qtbot):
    """Fenster mit Platzhalter unten, wie es die StatusBar erwartet."""
    window = QWidget()
    window.resize(400, 200)

    layout = QVBoxLayout(window)
    layout.addStretch(1)

    slot = QWidget()
    slot.setFixedHeight(20)
    slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    layout.addWidget(slot)

    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    return window, slot
