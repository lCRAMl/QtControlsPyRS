from PyQt6.QtCore import QRectF
from PyQt6.QtGui import QColor

from qt_controls_pyrs import HeartCheckBox


def make(qtbot, text: str = "") -> HeartCheckBox:
    box = HeartCheckBox(text)
    box.resize(box.sizeHint())
    qtbot.addWidget(box)
    box.show()
    qtbot.waitExposed(box)
    return box


def test_ruhezustand_zeigt_nur_den_umriss(qtbot, paint):
    box = make(qtbot)

    assert not box.isChecked()
    assert box.pop == 0.0
    assert box.spark == 0.0
    paint(box)


def test_anhaken_laesst_das_herz_springen(qtbot, paint):
    box = make(qtbot)

    with qtbot.waitSignal(box.toggled, timeout=1000) as signal:
        box.setChecked(True)
    assert signal.args == [True]

    # Unterwegs waechst das Herz ueber seine Endgroesse hinaus.
    qtbot.waitUntil(lambda: box.pop > 1.0, timeout=2000)
    paint(box)

    qtbot.waitUntil(lambda: box.pop == 1.0 and box.glow == 0.0, timeout=3000)
    paint(box)


def test_funken_laufen_einmal_und_sind_dann_weg(qtbot, paint):
    box = make(qtbot)
    box.setChecked(True)

    qtbot.waitUntil(lambda: 0.0 < box.spark < 1.0, timeout=2000)
    paint(box)

    qtbot.waitUntil(lambda: box.spark == 1.0, timeout=2000)
    paint(box)


def test_abhaken_nimmt_das_volle_herz_sofort_weg(qtbot, paint):
    box = make(qtbot)
    box.setChecked(True)
    qtbot.waitUntil(lambda: box.pop == 1.0, timeout=3000)

    box.setChecked(False)
    # Die Vorlage blendet nicht aus, sie schaltet hart um.
    assert box.pop == 0.0
    assert box.spark == 0.0
    paint(box)


def test_platz_fuer_beschriftung_und_funken(qtbot):
    ohne = make(qtbot)
    mit = make(qtbot, "Gefaellt mir")

    side = HeartCheckBox.HEART + 2 * HeartCheckBox.SPARK_ROOM
    assert ohne.sizeHint().width() == side
    assert ohne.sizeHint().height() == side
    assert mit.sizeHint().width() > ohne.sizeHint().width()

    # Der Rand um das Herz ist genau der Platz, in den die Funken stieben.
    heart = ohne._heart_rect()
    room = ohne._room()
    assert heart.adjusted(-room, -room, room, room) == QRectF(ohne.rect())


def test_herz_geht_mit_der_groesse_mit(qtbot, paint):
    box = make(qtbot)
    box.spark = 0.5

    for side in (120, 90, 60, 30, 12):
        box.resize(side, side)
        heart = box._heart_rect()
        assert heart.width() > 0
        assert box.rect().contains(heart.toRect())
        paint(box)


def test_herzfarbe_ist_austauschbar(qtbot, paint):
    box = make(qtbot)

    assert box.heart_color() == QColor(HeartCheckBox.COLOR)
    box.setHeartColor("#44cc88")
    assert box.heart_color() == QColor("#44cc88")

    box.setChecked(True)
    box.spark = 0.4
    paint(box)
