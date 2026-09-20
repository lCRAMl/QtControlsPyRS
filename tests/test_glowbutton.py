from PyQt6.QtCore import QAbstractAnimation

from qt_controls_pyrs import GenerateButton, GlowButton


def make(qtbot) -> GlowButton:
    button = GlowButton("Generate AI", busy_text="Generating")
    button.resize(220, 50)
    qtbot.addWidget(button)
    button.show()
    qtbot.waitExposed(button)
    return button


def test_alias_zeigt_auf_dieselbe_klasse():
    assert GenerateButton is GlowButton


def test_ruhezustand(qtbot, paint):
    button = make(qtbot)

    assert not button.is_busy()
    assert button.morph == 0.0
    assert button._colors.state() != QAbstractAnimation.State.Running
    paint(button)


def test_start_busy_blendet_um_und_startet_farbband(qtbot, paint):
    button = make(qtbot)
    button.start_busy()

    assert button.is_busy()
    qtbot.waitUntil(lambda: button.morph == 1.0, timeout=2000)
    assert button._colors.state() == QAbstractAnimation.State.Running

    # Farbband wandert weiter
    first = button.phase
    qtbot.waitUntil(lambda: button.phase != first, timeout=2000)
    paint(button)


def test_stop_busy_blendet_zurueck_und_haelt_an(qtbot, paint):
    button = make(qtbot)
    button.start_busy()
    qtbot.waitUntil(lambda: button.morph == 1.0, timeout=2000)

    button.stop_busy()
    assert not button.is_busy()
    qtbot.waitUntil(lambda: button.morph == 0.0, timeout=2000)

    # Das Farbband laeuft erst aus, wenn es unsichtbar ist — dann aber wirklich.
    qtbot.waitUntil(
        lambda: button._colors.state() != QAbstractAnimation.State.Running,
        timeout=2000,
    )
    paint(button)


def test_beschriftungen_bleiben_aenderbar(qtbot):
    button = make(qtbot)

    button.setText("Los")
    button.setBusyText("Laeuft")
    assert button.text() == "Los"
    assert button.busy_text() == "Laeuft"

    button.start_busy("Anderer Text")
    assert button.busy_text() == "Anderer Text"


def test_gesperrter_knopf_zeichnet_weiter(qtbot, paint):
    button = make(qtbot)
    button.setEnabled(False)
    button.start_busy()
    qtbot.wait(100)
    paint(button)
