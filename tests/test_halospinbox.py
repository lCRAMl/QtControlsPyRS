import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import QDoubleSpinBox, QSpinBox

from qt_controls_pyrs import HaloDoubleSpinBox, HaloSpinBox

BEIDE = [HaloSpinBox, HaloDoubleSpinBox]


def make(qtbot, cls=HaloSpinBox):
    feld = cls()
    feld.setRange(0, 100)
    feld.setValue(10)
    feld.resize(feld.sizeHint())
    qtbot.addWidget(feld)
    feld.show()
    qtbot.waitExposed(feld)
    return feld


def enter(feld) -> None:
    point = QPointF(feld.rect().center())
    feld.enterEvent(QEnterEvent(point, point, point))


# ----------------------------------------------------------------------
# Die Qt-Vorbilder bleiben erhalten
# ----------------------------------------------------------------------

def test_ist_eine_qspinbox(qtbot, paint):
    feld = make(qtbot, HaloSpinBox)

    assert isinstance(feld, QSpinBox)
    with qtbot.waitSignal(feld.valueChanged, timeout=1000) as signal:
        feld.setValue(42)
    assert signal.args == [42]
    paint(feld)


def test_ist_eine_qdoublespinbox(qtbot, paint):
    feld = make(qtbot, HaloDoubleSpinBox)

    assert isinstance(feld, QDoubleSpinBox)
    feld.setDecimals(2)
    feld.setValue(1.25)
    assert feld.value() == pytest.approx(1.25)
    paint(feld)


@pytest.mark.parametrize("cls", BEIDE)
def test_grenzen_praefix_und_suffix_wirken(qtbot, paint, cls):
    feld = make(qtbot, cls)
    feld.setSuffix(" mm")
    feld.setRange(5, 20)

    feld.setValue(99)
    assert feld.value() == 20        # oben gekappt
    feld.setValue(-5)
    assert feld.value() == 5         # unten gekappt
    assert feld.text().endswith(" mm")
    paint(feld)


# ----------------------------------------------------------------------
# Schrittschalten
# ----------------------------------------------------------------------

@pytest.mark.parametrize("cls", BEIDE)
def test_tastatur_und_rad_schalten_weiter(qtbot, cls):
    """Qts eigene Pfeile sind aus - Tastatur und Rad duerfen das nicht merken."""
    feld = make(qtbot, cls)
    vorher = feld.value()

    qtbot.keyClick(feld, Qt.Key.Key_Up)
    assert feld.value() > vorher

    qtbot.keyClick(feld, Qt.Key.Key_Down)
    assert feld.value() == vorher


@pytest.mark.parametrize("cls", BEIDE)
def test_klick_auf_den_pfeil_schaltet(qtbot, cls):
    feld = make(qtbot, cls)
    oben, unten = feld._arrow_rects()
    vorher = feld.value()

    qtbot.mouseClick(feld, Qt.MouseButton.LeftButton, pos=oben.center().toPoint())
    assert feld.value() > vorher

    qtbot.mouseClick(feld, Qt.MouseButton.LeftButton, pos=unten.center().toPoint())
    assert feld.value() == vorher


@pytest.mark.parametrize("cls", BEIDE)
def test_ein_klick_in_die_zahl_schaltet_nicht(qtbot, cls):
    """Nur die Pfeilspalte schaltet - sonst springt der Wert beim Hineinklicken."""
    feld = make(qtbot, cls)
    vorher = feld.value()

    links = QPointF(feld.ROOM + feld.PAD + 5, feld.height() / 2)
    assert feld._zone_at(links) == 0
    qtbot.mouseClick(feld, Qt.MouseButton.LeftButton, pos=links.toPoint())
    assert feld.value() == vorher


@pytest.mark.parametrize("cls", BEIDE)
def test_halten_schaltet_weiter(qtbot, cls):
    feld = make(qtbot, cls)
    oben, _ = feld._arrow_rects()

    qtbot.mousePress(feld, Qt.MouseButton.LeftButton, pos=oben.center().toPoint())
    nach_dem_ersten = feld.value()
    assert feld._held == 1

    # Die Wartezeit ist eingebaut, damit ein Klick nicht versehentlich
    # weiterschaltet; geprueft wird der Schritt danach.
    feld._begin_repeat()
    feld._repeat_step()
    feld._repeat_step()
    assert feld.value() > nach_dem_ersten

    qtbot.mouseRelease(feld, Qt.MouseButton.LeftButton, pos=oben.center().toPoint())
    assert feld._held == 0
    stand = feld.value()
    feld._repeat_step()
    assert feld.value() == stand, "Nach dem Loslassen darf nichts mehr laufen"


# ----------------------------------------------------------------------
# Die Leiste und die Pfeile
# ----------------------------------------------------------------------

@pytest.mark.parametrize("cls", BEIDE)
def test_unter_der_maus_wird_der_rahmen_hell(qtbot, paint, cls):
    feld = make(qtbot, cls)
    assert feld.hover == 0.0

    enter(feld)
    qtbot.waitUntil(lambda: feld.hover == 1.0, timeout=3000)
    paint(feld)

    feld.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: feld.hover == 0.0, timeout=3000)


@pytest.mark.parametrize("cls", BEIDE)
def test_nur_der_pfeil_unter_der_maus_leuchtet(qtbot, paint, cls):
    feld = make(qtbot, cls)
    oben, unten = feld._arrow_rects()

    feld._light_arrows(feld._zone_at(oben.center()))
    qtbot.waitUntil(lambda: feld.up == 1.0, timeout=2000)
    assert feld.down == 0.0
    paint(feld)

    feld._light_arrows(feld._zone_at(unten.center()))
    qtbot.waitUntil(lambda: feld.down == 1.0, timeout=2000)
    qtbot.waitUntil(lambda: feld.up == 0.0, timeout=2000)
    paint(feld)


@pytest.mark.parametrize("cls", BEIDE)
def test_der_benutzte_pfeil_blitzt_auf(qtbot, paint, cls):
    feld = make(qtbot, cls)
    assert feld.flashUp == 0.0

    feld.stepBy(1)
    assert feld.flashUp > 0.0, "Auch Tastatur und Rad sollen den Pfeil zeigen"
    paint(feld)
    qtbot.waitUntil(lambda: feld.flashUp == 0.0, timeout=2000)

    feld.stepBy(-1)
    assert feld.flashDown > 0.0
    qtbot.waitUntil(lambda: feld.flashDown == 0.0, timeout=2000)


@pytest.mark.parametrize("cls", BEIDE)
def test_die_zahl_laeuft_nicht_unter_die_pfeile(qtbot, cls):
    feld = make(qtbot, cls)

    rechts = feld.lineEdit().textMargins().right()
    assert rechts >= feld.ARROW_ZONE, (
        "Rechts muesste mindestens die Pfeilspalte frei bleiben"
    )


@pytest.mark.parametrize("cls", BEIDE)
def test_gesperrt_wird_blass_gezeichnet(qtbot, paint, cls):
    feld = make(qtbot, cls)
    enter(feld)
    qtbot.waitUntil(lambda: feld.hover == 1.0, timeout=3000)

    feld.setEnabled(False)
    qtbot.waitUntil(lambda: feld.hover == 0.0, timeout=3000)
    paint(feld)
