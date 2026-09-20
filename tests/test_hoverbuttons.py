import pytest
from PyQt6.QtCore import QEvent, QPointF, QRectF
from PyQt6.QtGui import QEnterEvent

from qt_controls_pyrs import (
    DashBorderButton, HaloButton, RaisedButton, ShineButton, SpreadButton
)

ALLE = [DashBorderButton, SpreadButton, RaisedButton, ShineButton, HaloButton]


def make(qtbot, cls, text: str = "Hover me"):
    button = cls(text)
    button.resize(button.sizeHint())
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button


def enter(button) -> None:
    point = QPointF(button.rect().center())
    button.enterEvent(QEnterEvent(point, point, point))


def leave(button) -> None:
    button.leaveEvent(QEvent(QEvent.Type.Leave))


@pytest.mark.parametrize("cls", ALLE)
def test_jeder_zustand_zeichnet(qtbot, paint, cls):
    button = make(qtbot, cls)

    assert button.hover == 0.0
    for step in (0.0, 0.2, 0.5, 0.8, 1.0):
        button.hover = step
        if hasattr(button, "lines"):
            button.lines = step
        paint(button)


@pytest.mark.parametrize("cls", ALLE)
def test_maus_hin_und_weg(qtbot, paint, cls):
    button = make(qtbot, cls)

    enter(button)
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=3000)
    paint(button)

    leave(button)
    qtbot.waitUntil(lambda: button.hover == 0.0, timeout=3000)
    paint(button)


@pytest.mark.parametrize("cls", ALLE)
def test_sperren_nimmt_die_bewegung_zurueck(qtbot, paint, cls):
    button = make(qtbot, cls)
    enter(button)
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=3000)

    # Ein gesperrter Knopf bekommt kein leaveEvent mehr.
    button.setEnabled(False)
    qtbot.waitUntil(lambda: button.hover == 0.0, timeout=3000)
    paint(button)


@pytest.mark.parametrize("cls", ALLE)
def test_platz_fuer_beschriftung_und_raender(qtbot, cls):
    kurz = make(qtbot, cls, "Los")
    lang = make(qtbot, cls, "Deutlich laengere Beschriftung")

    assert lang.sizeHint().width() > kurz.sizeHint().width()
    assert kurz.sizeHint().height() == cls.HEIGHT + 2 * cls.ROOM

    # Die Flaeche laesst den Rand frei, der ausserhalb gezeichnet wird.
    surface = kurz._surface()
    room = kurz._room()
    assert surface.adjusted(-room, -room, room, room) == QRectF(kurz.rect())


def test_beschriftung_wird_grossgeschrieben(qtbot, paint):
    button = make(qtbot, ShineButton, "Hover me")

    assert button.text() == "Hover me"
    assert button._label() == "HOVER ME"

    button.UPPERCASE = False
    assert button._label() == "Hover me"
    paint(button)


def test_striche_laufen_eigenstaendig_mit(qtbot):
    button = make(qtbot, SpreadButton)
    assert button.lines == 0.0

    enter(button)
    # Die Striche sind schneller fertig als die Sperrschrift.
    qtbot.waitUntil(lambda: button.lines == 1.0, timeout=2000)
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=2000)

    leave(button)
    qtbot.waitUntil(lambda: button.lines == 0.0 and button.hover == 0.0, timeout=2000)


def test_dash_bleibt_bei_jeder_groesse_ein_strich(qtbot, paint):
    button = make(qtbot, DashBorderButton)
    button.hover = 1.0

    # Das Muster rechnet mit dem wirklichen Umfang, nicht mit dem der Vorlage.
    for size in ((160, 45), (320, 45), (90, 60)):
        button.resize(*size)
        paint(button)


def test_erhabener_knopf_faerbt_die_schrift_um(qtbot):
    button = make(qtbot, RaisedButton)

    assert button._ink(0.0) != button._ink(1.0)
    assert button._text_shadow(0.0) is None
    assert button._text_shadow(1.0) is not None


def test_halo_haelt_platz_fuer_den_auswandernden_strich(qtbot):
    button = make(qtbot, HaloButton)

    assert HaloButton.ROOM > 0
    assert button.sizeHint().height() == HaloButton.HEIGHT + 2 * HaloButton.ROOM
    assert button._room() > 0
