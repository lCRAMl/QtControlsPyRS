from PyQt6.QtCore import QAbstractAnimation, QEvent, QPointF
from PyQt6.QtGui import QColor, QEnterEvent

from qt_controls_pyrs import BusyHaloButton, HaloButton, PulseHaloButton


def make(qtbot, text: str = "Generate", busy_text: str = "Generating"):
    button = PulseHaloButton(text, busy_text=busy_text)
    button.resize(button.sizeHint())
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button


def test_ist_ein_halobutton_mit_arbeitszustand(qtbot, paint):
    button = make(qtbot)

    assert isinstance(button, BusyHaloButton)
    assert isinstance(button, HaloButton)
    assert not button.is_busy()
    assert button.busy_fade == 0.0
    paint(button)


def test_maus_bewegt_den_knopf_wie_vorher(qtbot, paint):
    button = make(qtbot)

    point = QPointF(button.rect().center())
    button.enterEvent(QEnterEvent(point, point, point))
    qtbot.waitUntil(lambda: button.hover == 1.0, timeout=3000)
    paint(button)

    button.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: button.hover == 0.0, timeout=3000)
    paint(button)


def test_start_busy_laesst_die_striche_wandern(qtbot, paint):
    button = make(qtbot)
    button.start_busy()

    assert button.is_busy()
    qtbot.waitUntil(lambda: button.busy_fade == 1.0, timeout=2000)
    assert button._cycle.state() == QAbstractAnimation.State.Running

    first = button.phase
    qtbot.waitUntil(lambda: button.phase != first, timeout=2000)
    paint(button)


def test_stop_busy_blendet_aus_und_haelt_dann_an(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    qtbot.waitUntil(lambda: button.busy_fade == 1.0, timeout=2000)

    button.stop_busy()
    assert not button.is_busy()
    qtbot.waitUntil(lambda: button.busy_fade == 0.0, timeout=2000)
    qtbot.waitUntil(
        lambda: button._cycle.state() != QAbstractAnimation.State.Running,
        timeout=2000,
    )
    paint(button)


def test_beschriftung_blendet_ueber(qtbot, paint):
    button = make(qtbot)
    assert button.label_fade == 0.0

    button.start_busy()
    # Unterwegs liegen beide Beschriftungen uebereinander.
    qtbot.waitUntil(lambda: 0.0 < button.label_fade < 1.0, timeout=1000)
    paint(button)
    qtbot.waitUntil(lambda: button.label_fade == 1.0, timeout=2000)
    paint(button)

    button.stop_busy()
    qtbot.waitUntil(lambda: button.label_fade == 0.0, timeout=2000)
    paint(button)


def test_striche_bleiben_im_widget(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    button.busy_fade = 1.0

    # Der aeusserste Strich sitzt am Ende genau auf dem Widget-Rand.
    surface = button._surface()
    room = button._room()
    assert surface.adjusted(-room, -room, room, room) == button.rect().toRectF()

    for phase in (0.0, 0.25, 0.5, 0.75, 0.99):
        button.phase = phase
        paint(button)


def test_gesperrter_knopf_zeigt_die_anzeige_trotzdem(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    button.busy_fade = 1.0

    # Die Anwendung sperrt den Knopf ueblicherweise, solange sie arbeitet.
    button.setEnabled(False)
    assert button.is_busy()
    paint(button)


def test_farbe_ist_austauschbar(qtbot, paint):
    button = make(qtbot)

    assert button.accent_color() == QColor(PulseHaloButton.ACCENT)
    button.setAccentColor("#ffb703")
    assert button.accent_color() == QColor("#ffb703")

    button.start_busy()
    button.busy_fade = 1.0
    button.phase = 0.5
    paint(button)
