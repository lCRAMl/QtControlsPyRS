from PyQt6.QtCore import QAbstractAnimation, QEvent, QPointF
from PyQt6.QtGui import QColor, QEnterEvent

from qt_controls_pyrs import FiberHaloButton, HaloButton


def make(qtbot, text: str = "Generate", busy_text: str = "Generating"):
    button = FiberHaloButton(text, busy_text=busy_text)
    button.resize(button.sizeHint())
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button


def test_ist_ein_halobutton_mit_allem_drum_und_dran(qtbot, paint):
    button = make(qtbot)

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


def test_start_busy_blendet_die_leitung_auf(qtbot, paint):
    button = make(qtbot)
    button.start_busy()

    assert button.is_busy()
    qtbot.waitUntil(lambda: button.busy_fade == 1.0, timeout=2000)
    assert button._cycle.state() == QAbstractAnimation.State.Running

    # Die Fasern schwingen weiter.
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

    # Die Schwingung laeuft erst aus, wenn nichts mehr zu sehen ist.
    qtbot.waitUntil(
        lambda: button._cycle.state() != QAbstractAnimation.State.Running,
        timeout=2000,
    )
    paint(button)


def test_klick_startet_die_anzeige(qtbot):
    button = make(qtbot)
    assert FiberHaloButton.AUTO_BUSY

    button.click()
    assert button.is_busy()

    # Ein zweiter Klick setzt die laufende Anzeige nicht zurueck.
    qtbot.waitUntil(lambda: button.busy_fade == 1.0, timeout=2000)
    button.click()
    assert button.busy_fade == 1.0


def test_beschriftung_wechselt_waehrend_der_arbeit(qtbot, paint):
    button = make(qtbot)
    assert button._label() == "GENERATE"

    button.start_busy()
    assert button._label() == "GENERATING"
    paint(button)

    button.stop_busy()
    assert button._label() == "GENERATE"

    button.start_busy("Laeuft")
    assert button.busy_text() == "Laeuft"
    assert button._label() == "LAEUFT"


def test_platz_fuer_beide_beschriftungen(qtbot):
    kurz = FiberHaloButton("Los", busy_text="")
    lang = FiberHaloButton("Los", busy_text="Sehr lange Arbeitsbeschriftung")
    qtbot.addWidget(kurz)
    qtbot.addWidget(lang)

    assert lang.sizeHint().width() > kurz.sizeHint().width()

    # Der Knopf darf nicht wachsen, sobald die Aufgabe losläuft.
    vorher = lang.sizeHint().width()
    lang.start_busy()
    assert lang.sizeHint().width() == vorher


def test_animation_fuellt_jede_groesse(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    button.busy_fade = 1.0

    for width, height in ((220, 45), (400, 45), (120, 70), (60, 30)):
        button.resize(width + 2 * FiberHaloButton.ROOM, height + 2 * FiberHaloButton.ROOM)
        for phase in (0.0, 0.25, 0.5, 0.75):
            button.phase = phase
            paint(button)


def test_nuancen_kommen_aus_der_grundfarbe(qtbot):
    button = make(qtbot)

    # Derselbe Farbton wie die Grundfarbe, nur tiefer.
    grund = button._nuance(0.0, 1.0, 1.0)
    assert grund.hue() == QColor(FiberHaloButton.ACCENT).hue()

    tief = button._nuance(*FiberHaloButton.GROUND)
    assert tief.value() < grund.value()

    # Eine andere Grundfarbe faerbt alle Nuancen mit um.
    button.setAccentColor("#ff7a18")
    assert button._nuance(0.0, 1.0, 1.0).hue() == QColor("#ff7a18").hue()


def test_grauer_grundton_bringt_die_nuancen_nicht_durcheinander(qtbot, paint):
    button = make(qtbot)
    button.setAccentColor("#808080")     # ohne Farbton

    button.start_busy()
    button.busy_fade = 1.0
    paint(button)


def test_signalfarbe_ist_austauschbar(qtbot, paint):
    button = make(qtbot)

    assert button.accent_color() == QColor(FiberHaloButton.ACCENT)
    button.setAccentColor("#ffb703")
    assert button.accent_color() == QColor("#ffb703")

    button.start_busy()
    button.busy_fade = 1.0
    paint(button)


def test_gesperrter_knopf_zeigt_die_leitung_trotzdem(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    button.busy_fade = 1.0

    # Die Anwendung sperrt den Knopf ueblicherweise, solange sie arbeitet.
    button.setEnabled(False)
    assert button.is_busy()
    paint(button)
