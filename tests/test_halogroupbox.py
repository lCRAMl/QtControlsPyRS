from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QEnterEvent
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from qt_controls_pyrs import HaloGroupBox


def make(qtbot, titel: str = "Platte und Sauger") -> HaloGroupBox:
    gruppe = HaloGroupBox(titel)
    layout = QVBoxLayout(gruppe)
    layout.addWidget(QLabel("Inhalt"))
    gruppe.resize(320, 140)
    qtbot.addWidget(gruppe)
    gruppe.show()
    qtbot.waitExposed(gruppe)
    return gruppe


# ----------------------------------------------------------------------
# QGroupBox bleibt QGroupBox
# ----------------------------------------------------------------------

def test_ist_eine_qgroupbox(qtbot, paint):
    gruppe = make(qtbot)

    assert isinstance(gruppe, QGroupBox)
    assert gruppe.title() == "Platte und Sauger"

    gruppe.setTitle("Vakuum und Sicherheit")
    assert gruppe.title() == "Vakuum und Sicherheit"
    paint(gruppe)


def test_abschaltbar_wie_gewohnt(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)

    # QGroupBox ist nach setCheckable(True) angehakt - das ist Qts Vorgabe
    # und bleibt so.
    assert gruppe.isCheckable()
    assert gruppe.isChecked()

    with qtbot.waitSignal(gruppe.toggled, timeout=1000) as signal:
        gruppe.setChecked(False)
    assert signal.args == [False]
    paint(gruppe)


def test_ein_layout_laesst_sich_hineinsetzen(qtbot):
    gruppe = make(qtbot)

    assert gruppe.layout() is not None
    assert gruppe.layout().count() == 1


# ----------------------------------------------------------------------
# Rahmen, Ueberschrift und Inhalt
# ----------------------------------------------------------------------

def test_der_inhalt_liegt_im_rahmen_und_unter_der_ueberschrift(qtbot):
    gruppe = make(qtbot)
    raender = gruppe.contentsMargins()

    assert raender.left() == gruppe.PAD_X
    assert raender.right() == gruppe.PAD_X
    assert raender.bottom() == gruppe.PAD_BOTTOM
    assert raender.top() >= gruppe._title_height(), (
        "Der Inhalt muesste unterhalb der Ueberschrift beginnen"
    )


def test_eine_laengere_ueberschrift_macht_mehr_platz(qtbot):
    gruppe = make(qtbot, "Kurz")
    schmal = gruppe._title_rect().width()

    gruppe.setTitle("Eine deutlich laengere Ueberschrift")
    assert gruppe._title_rect().width() > schmal


def test_das_kaestchen_steht_links_vor_der_ueberschrift(qtbot, paint):
    gruppe = make(qtbot)
    ohne = gruppe._title_rect().left()

    gruppe.setCheckable(True)
    mit = gruppe._title_rect().left()
    assert mit > ohne, "Die Ueberschrift muesste dem Kaestchen Platz machen"
    assert gruppe._box_rect().right() <= mit
    paint(gruppe)


def test_ohne_kaestchen_gibt_es_kein_kaestchen(qtbot):
    gruppe = make(qtbot)

    assert not gruppe.isCheckable()
    assert gruppe._box_rect().isEmpty()


def test_der_kopfbereich_schaltet_um_wie_bei_jeder_qgroupbox(qtbot):
    """Gezeichnet wird eigens, geklickt nicht - sonst waere es kein Vorbild mehr."""
    gruppe = make(qtbot)
    gruppe.setCheckable(True)
    gruppe.setChecked(False)

    qtbot.mouseClick(gruppe, Qt.MouseButton.LeftButton,
                     pos=gruppe._box_rect().center().toPoint())
    assert gruppe.isChecked()

    qtbot.mouseClick(gruppe, Qt.MouseButton.LeftButton,
                     pos=gruppe._title_rect().center().toPoint())
    assert not gruppe.isChecked()


def test_unter_der_maus_glimmt_der_rahmen_auf(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.hover = 0.0

    point = QPointF(gruppe.rect().center())
    gruppe.enterEvent(QEnterEvent(point, point, point))
    qtbot.waitUntil(lambda: gruppe.hover == 1.0, timeout=3000)
    paint(gruppe)

    gruppe.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: gruppe.hover == 0.0, timeout=3000)


def test_das_kaestchen_fuellt_sich_statt_zu_springen(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)      # damit schon angehakt, siehe oben
    gruppe.setChecked(False)
    qtbot.waitUntil(lambda: gruppe.position == 0.0, timeout=2000)

    gruppe.setChecked(True)
    qtbot.wait(60)
    assert 0.0 < gruppe.position < 1.0
    paint(gruppe)
    qtbot.waitUntil(lambda: gruppe.position == 1.0, timeout=2000)


def test_die_signalfarbe_laesst_sich_setzen(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)
    gruppe.setChecked(True)

    gruppe.setAccentColor(QColor("#ff8c00"))
    assert gruppe.accent_color() == QColor("#ff8c00")
    paint(gruppe)


def test_ohne_ueberschrift_laeuft_der_strich_durch(qtbot, paint):
    gruppe = make(qtbot, "")

    assert gruppe.title() == ""
    assert gruppe._title_rect().width() == 0
    paint(gruppe)


def test_gesperrt_wird_blass_gezeichnet(qtbot, paint):
    gruppe = make(qtbot)

    gruppe.setEnabled(False)
    qtbot.waitUntil(lambda: gruppe.hover == 0.0, timeout=3000)
    paint(gruppe)
