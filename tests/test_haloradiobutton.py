from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QColor, QEnterEvent
from PyQt6.QtWidgets import QButtonGroup, QRadioButton, QVBoxLayout, QWidget

from qt_controls_pyrs import HaloRadioButton


def make(qtbot, text: str = "Von oben") -> HaloRadioButton:
    knopf = HaloRadioButton(text)
    knopf.resize(knopf.sizeHint())
    qtbot.addWidget(knopf)
    knopf.show()
    qtbot.waitExposed(knopf)
    return knopf


def make_gruppe(qtbot, anzahl: int = 3):
    fenster = QWidget()
    layout = QVBoxLayout(fenster)
    knoepfe = [HaloRadioButton(f"Wahl {i + 1}") for i in range(anzahl)]
    for knopf in knoepfe:
        layout.addWidget(knopf)
    fenster.resize(240, 40 * anzahl)
    qtbot.addWidget(fenster)
    fenster.show()
    qtbot.waitExposed(fenster)
    return fenster, knoepfe


# ----------------------------------------------------------------------
# QRadioButton bleibt QRadioButton
# ----------------------------------------------------------------------

def test_ist_ein_qradiobutton(qtbot, paint):
    knopf = make(qtbot)

    assert isinstance(knopf, QRadioButton)
    assert not knopf.isChecked()
    assert knopf.position == 0.0

    with qtbot.waitSignal(knopf.toggled, timeout=1000) as signal:
        knopf.setChecked(True)
    assert signal.args == [True]
    paint(knopf)


def test_in_einer_gruppe_bleibt_genau_einer_gewaehlt(qtbot, paint):
    """Die Ausschliesslichkeit kommt von Qt - sie darf dabei nicht verlorengehen."""
    fenster, knoepfe = make_gruppe(qtbot)
    erster, zweiter, dritter = knoepfe

    erster.setChecked(True)
    assert [k.isChecked() for k in knoepfe] == [True, False, False]

    dritter.setChecked(True)
    assert [k.isChecked() for k in knoepfe] == [False, False, True]
    paint(fenster)


def test_auch_in_einer_qbuttongroup(qtbot):
    knoepfe = [HaloRadioButton(f"Wahl {i}") for i in range(3)]
    gruppe = QButtonGroup()
    for nummer, knopf in enumerate(knoepfe):
        gruppe.addButton(knopf, nummer)
        qtbot.addWidget(knopf)

    knoepfe[1].setChecked(True)
    assert gruppe.checkedId() == 1
    knoepfe[2].setChecked(True)
    assert gruppe.checkedId() == 2


def test_klick_auf_die_beschriftung_waehlt_aus(qtbot):
    knopf = make(qtbot)

    auf_dem_text = QPoint(knopf.width() - 5, knopf.height() // 2)
    assert knopf.hitButton(auf_dem_text)
    qtbot.mouseClick(knopf, Qt.MouseButton.LeftButton, pos=auf_dem_text)
    assert knopf.isChecked()


# ----------------------------------------------------------------------
# Das Aussehen
# ----------------------------------------------------------------------

def test_der_kern_waechst_statt_zu_springen(qtbot, paint):
    knopf = make(qtbot)

    knopf.setChecked(True)
    qtbot.wait(60)
    assert 0.0 < knopf.position < 1.0      # unterwegs
    paint(knopf)
    qtbot.waitUntil(lambda: knopf.position == 1.0, timeout=2000)
    paint(knopf)


def test_der_ring_laeuft_nur_beim_waehlen_hinaus(qtbot, paint):
    """Sonst blitzte bei jedem Wechsel die halbe Gruppe auf."""
    knopf = make(qtbot)

    knopf.setChecked(True)
    assert knopf.burst < 1.0, "Beim Waehlen muesste ein Ring unterwegs sein"
    paint(knopf)
    qtbot.waitUntil(lambda: knopf.burst == 1.0, timeout=2000)

    knopf.setChecked(False)
    assert knopf.burst == 1.0, "Beim Abwaehlen darf nichts hinauslaufen"


def test_unsichtbar_gesetzt_wird_nicht_animiert(qtbot):
    """Gespeicherte Einstellungen sollen stehen, nicht hereinfliegen."""
    knopf = HaloRadioButton("Von oben")
    qtbot.addWidget(knopf)

    knopf.setChecked(True)
    assert knopf.position == 1.0
    assert knopf.burst == 1.0


def test_unter_der_maus_wird_der_ring_weiss(qtbot, paint):
    knopf = make(qtbot)
    knopf.hover = 0.0
    ruhe = knopf._line_color().alphaF()

    point = QPointF(knopf.rect().center())
    knopf.enterEvent(QEnterEvent(point, point, point))
    qtbot.waitUntil(lambda: knopf.hover == 1.0, timeout=3000)
    assert knopf._line_color().alphaF() > ruhe
    paint(knopf)

    knopf.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: knopf.hover == 0.0, timeout=3000)


def test_die_signalfarbe_laesst_sich_setzen(qtbot, paint):
    knopf = make(qtbot)

    knopf.setAccentColor(QColor("#ff8c00"))
    assert knopf.accent_color() == QColor("#ff8c00")
    knopf.setChecked(True)
    paint(knopf)


def test_haelt_platz_fuer_den_auslaufenden_ring_frei(qtbot):
    ohne_text = HaloRadioButton()
    qtbot.addWidget(ohne_text)

    hint = ohne_text.sizeHint()
    assert hint.width() >= ohne_text.RING + 2 * ohne_text.ROOM
    assert hint.height() >= ohne_text.RING


def test_gesperrt_wird_blass_gezeichnet(qtbot, paint):
    knopf = make(qtbot)
    knopf.setChecked(True)
    qtbot.waitUntil(lambda: knopf.position == 1.0, timeout=2000)

    knopf.setEnabled(False)
    qtbot.waitUntil(lambda: knopf.hover == 0.0, timeout=3000)
    paint(knopf)
