from qt_controls_pyrs import AnimatedToggle


def make(qtbot, text: str = "Autoretry") -> AnimatedToggle:
    toggle = AnimatedToggle(text)
    toggle.resize(toggle.sizeHint())
    qtbot.addWidget(toggle)
    toggle.show()
    qtbot.waitExposed(toggle)
    return toggle


def test_platz_fuer_die_beschriftung(qtbot):
    ohne = make(qtbot, "")
    mit = make(qtbot, "Autoretry")

    assert ohne.sizeHint().width() == AnimatedToggle.TRACK_W
    assert mit.sizeHint().width() > ohne.sizeHint().width()


def test_knopf_gleitet_statt_zu_springen(qtbot, paint):
    toggle = make(qtbot)
    assert toggle.handle_position == 0.0

    with qtbot.waitSignal(toggle.toggled, timeout=1000) as signal:
        toggle.setChecked(True)
    assert signal.args == [True]

    # Zwischenzustand: unterwegs, aber noch nicht angekommen
    qtbot.wait(60)
    assert 0.0 <= toggle.handle_position < 1.0

    qtbot.waitUntil(lambda: toggle.handle_position == 1.0, timeout=2000)
    paint(toggle)


def test_zurueckschalten(qtbot, paint):
    toggle = make(qtbot)
    toggle.setChecked(True)
    qtbot.waitUntil(lambda: toggle.handle_position == 1.0, timeout=2000)

    toggle.setChecked(False)
    qtbot.waitUntil(lambda: toggle.handle_position == 0.0, timeout=2000)
    assert not toggle.isChecked()
    paint(toggle)


def test_verhaelt_sich_wie_eine_checkbox(qtbot):
    toggle = make(qtbot)

    assert not toggle.isChecked()
    toggle.setChecked(True)
    assert toggle.isChecked()
    toggle.setChecked(False)
    assert not toggle.isChecked()


def test_klick_auf_die_beschriftung_schaltet_um(qtbot):
    toggle = make(qtbot)

    # Punkt weit rechts im Textbereich
    assert toggle.hitButton(toggle.rect().center())
    assert toggle.hitButton(toggle.rect().topRight())
