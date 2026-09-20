from PyQt6.QtCore import QEvent, QPointF, QRectF
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import QPushButton

from qt_controls_pyrs import FrameButton


def make(qtbot) -> FrameButton:
    button = FrameButton("Hover me")
    button.resize(200, 48)
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button


def enter(button: FrameButton) -> None:
    point = QPointF(button.rect().center())
    button.enterEvent(QEnterEvent(point, point, point))


def leave(button: FrameButton) -> None:
    button.leaveEvent(QEvent(QEvent.Type.Leave))


def test_ruhezustand(qtbot, paint):
    button = make(qtbot)

    assert button.hover == 0.0
    assert button.tint == 0.0
    paint(button)


def test_maus_darauf_faehrt_rahmen_herein(qtbot, paint):
    button = make(qtbot)
    enter(button)

    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=2000)
    # Die Aufhellung darunter braucht laenger als Schleier und Rahmen.
    qtbot.waitUntil(lambda: button.tint == 1.0, timeout=2000)
    paint(button)


def test_maus_weg_laeuft_rueckwaerts(qtbot, paint):
    button = make(qtbot)
    enter(button)
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=2000)

    leave(button)
    qtbot.waitUntil(lambda: button.hover == 0.0, timeout=2000)
    qtbot.waitUntil(lambda: button.tint == 0.0, timeout=2000)
    paint(button)


def test_halber_weg_zeichnet_beide_schichten(qtbot, paint):
    button = make(qtbot)

    # Mittendrin liegen Schleier und Rahmen gleichzeitig auf der Flaeche.
    button.hover = 0.5
    paint(button)


def test_sperren_nimmt_den_rahmen_zurueck(qtbot, paint):
    button = make(qtbot)
    enter(button)
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=2000)

    # Ein gesperrter Knopf bekommt kein leaveEvent mehr.
    button.setEnabled(False)
    qtbot.waitUntil(lambda: button.hover == 0.0, timeout=2000)
    paint(button)


def test_platz_fuer_den_rahmen_bleibt_frei(qtbot, paint):
    button = make(qtbot)

    surface = button._surface()
    assert surface.width() < button.width()
    assert surface.height() < button.height()

    # Der Rahmen bleibt auf seinem ganzen Weg im Widget — auch breite Knoepfe
    # schneiden ihn nicht an.
    for step in (0.0, 0.25, 0.5, 0.75, 1.0):
        button.hover = step
        paint(button)

    room_x, room_y = button._room()
    assert room_x <= button.RING_ROOM
    assert surface.adjusted(-room_x, -room_y, room_x, room_y) == QRectF(button.rect())

    # ... und die Groessenempfehlung haelt diesen Platz mit.
    plain = QPushButton("Hover me")
    assert button.sizeHint().height() > plain.sizeHint().height()
