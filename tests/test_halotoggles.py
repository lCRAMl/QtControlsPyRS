import pytest
from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QEnterEvent
from PyQt6.QtWidgets import QCheckBox

from qt_controls_pyrs import FrameToggle, HaloCheckBox, LineToggle

ALLE = [FrameToggle, LineToggle, HaloCheckBox]


def make(qtbot, cls, text: str = "Autoretry"):
    toggle = cls(text)
    toggle.resize(toggle.sizeHint())
    qtbot.addWidget(toggle)
    toggle.show()
    qtbot.waitExposed(toggle)
    return toggle


@pytest.mark.parametrize("cls", ALLE)
def test_ist_eine_qcheckbox(qtbot, cls):
    toggle = make(qtbot, cls)

    assert isinstance(toggle, QCheckBox)
    assert not toggle.isChecked()
    assert toggle.position == 0.0

    with qtbot.waitSignal(toggle.toggled, timeout=1000) as signal:
        toggle.setChecked(True)
    assert signal.args == [True]


@pytest.mark.parametrize("cls", ALLE)
def test_gleitet_statt_zu_springen(qtbot, paint, cls):
    toggle = make(qtbot, cls)

    toggle.setChecked(True)
    qtbot.wait(60)
    assert 0.0 < toggle.position < 1.0      # unterwegs
    paint(toggle)
    qtbot.waitUntil(lambda: toggle.position == 1.0, timeout=2000)
    paint(toggle)

    toggle.setChecked(False)
    qtbot.waitUntil(lambda: toggle.position == 0.0, timeout=2000)


@pytest.mark.parametrize("cls", ALLE)
def test_klick_auf_die_beschriftung_schaltet_um(qtbot, cls):
    toggle = make(qtbot, cls)

    auf_dem_text = QPoint(toggle.width() - 5, toggle.height() // 2)
    assert toggle.hitButton(auf_dem_text)
    qtbot.mouseClick(toggle, Qt.MouseButton.LeftButton, pos=auf_dem_text)
    assert toggle.isChecked()


@pytest.mark.parametrize("cls", ALLE)
def test_unter_der_maus_wird_der_rahmen_weiss(qtbot, paint, cls):
    toggle = make(qtbot, cls)
    ruhe = toggle._line_color().alphaF()

    point = QPointF(toggle.rect().center())
    toggle.enterEvent(QEnterEvent(point, point, point))
    qtbot.waitUntil(lambda: toggle.hover == 1.0, timeout=3000)
    assert toggle._line_color().alphaF() > ruhe
    paint(toggle)

    toggle.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: toggle.hover == 0.0, timeout=3000)


@pytest.mark.parametrize("cls", ALLE)
def test_platz_fuer_die_beschriftung(qtbot, cls):
    ohne = make(qtbot, cls, "")
    mit = make(qtbot, cls, "Autoretry")

    assert ohne.sizeHint().width() == int(round(ohne._indicator_size().width()))
    assert mit.sizeHint().width() > ohne.sizeHint().width()


@pytest.mark.parametrize("cls", ALLE)
def test_gespeicherter_zustand_steht_ohne_animation(qtbot, paint, cls):
    """Wie beim Programmstart: erst erzeugen, dann die Einstellung setzen."""
    toggle = cls("An")
    qtbot.addWidget(toggle)
    toggle.setChecked(True)

    # Sofort richtig — ohne Gleiten und beim Kästchen ohne Strich nach außen.
    assert toggle.position == 1.0
    assert toggle._slide.state() != toggle._slide.State.Running
    if isinstance(toggle, HaloCheckBox):
        assert toggle.burst == 1.0

    toggle.show()
    qtbot.waitExposed(toggle)
    paint(toggle)


@pytest.mark.parametrize("cls", ALLE)
def test_farbe_rundung_und_gesperrt(qtbot, paint, cls):
    class Rund(cls):
        RADIUS = 6

    toggle = make(qtbot, Rund)
    toggle.setAccentColor("#ff7a18")
    assert toggle.accent_color() == QColor("#ff7a18")

    toggle.setChecked(True)
    toggle._slide.stop()
    toggle.position = 1.0
    paint(toggle)

    toggle.setEnabled(False)
    paint(toggle)


def test_kaestchen_schickt_nur_beim_anhaken_einen_strich_hinaus(qtbot, paint):
    box = make(qtbot, HaloCheckBox)
    assert box.burst == 1.0

    box.setChecked(True)
    qtbot.waitUntil(lambda: 0.0 < box.burst < 1.0, timeout=1000)
    paint(box)
    qtbot.waitUntil(lambda: box.burst == 1.0, timeout=2000)

    box.setChecked(False)
    qtbot.wait(100)
    assert box.burst == 1.0, "beim Abhaken läuft nichts nach außen"


def test_kaestchen_mit_text_steht_mittig(qtbot):
    ohne = make(qtbot, HaloCheckBox, "")
    mit = make(qtbot, HaloCheckBox, "Autoretry")

    text = mit.fontMetrics().horizontalAdvance("Autoretry")
    rand = HaloCheckBox.ROOM
    # Links der Rand für den Strich, rechts nach dem Text derselbe.
    assert mit.sizeHint().width() == ohne.sizeHint().width() + HaloCheckBox.GAP + text + rand


def test_der_strich_bleibt_im_widget(qtbot):
    box = make(qtbot, HaloCheckBox, "")
    size = box._indicator_size()

    # Der Rand um das Kästchen ist genau so weit, wie der Strich wandert.
    assert size.width() == HaloCheckBox.BOX + 2 * HaloCheckBox.ROOM
    assert box.width() >= size.width()
