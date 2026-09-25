from PyQt6.QtCore import QEvent, QPoint, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QPushButton, QSizePolicy, QVBoxLayout, QWidget

from qt_controls_pyrs import HaloPromptBox


class Host(QWidget):
    """Fenster wie im APIImageGenerator: Platzhalter oben, darunter Inhalt und ein Knopf."""

    def __init__(self) -> None:
        super().__init__()
        self.resize(400, 360)

        column = QVBoxLayout(self)
        column.setContentsMargins(10, 10, 10, 10)

        self.slot = QWidget()
        self.slot.setMinimumHeight(120)
        self.slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        column.addWidget(self.slot, 1)

        self.covered = QPushButton("Einstellungen")
        column.addWidget(self.covered)

        self.stop = QPushButton("Generate")
        column.addWidget(self.stop)

        self.prompt = HaloPromptBox(self.slot, self)
        self.prompt.set_expand_stop(self.stop)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.prompt.sync_geometry()


def make(qtbot) -> Host:
    host = Host()
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host


def settle(qtbot, host: Host) -> None:
    """Wartet, bis die Bewegung steht."""
    prompt = host.prompt
    qtbot.waitUntil(
        lambda: prompt._grow_anim.state() != prompt._grow_anim.State.Running, timeout=3000
    )


def slot_rect(host: Host):
    return host.prompt._collapsed_rect()


def test_text_wie_ein_qplaintextedit(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    prompt.setPlaceholderText("Prompt eingeben ...")
    assert prompt.text.placeholderText() == "Prompt eingeben ..."

    with qtbot.waitSignal(prompt.textChanged, timeout=1000):
        prompt.setPlainText("Ein Leuchtturm im Nebel")
    assert prompt.toPlainText() == "Ein Leuchtturm im Nebel"

    prompt.clear()
    assert prompt.toPlainText() == ""


def test_schwebt_ueber_dem_platzhalter(qtbot, paint):
    host = make(qtbot)
    prompt = host.prompt

    assert prompt.geometry() == slot_rect(host)
    paint(prompt)

    # Wird das Fenster größer, wächst der Platzhalter — das Feld zieht nach.
    host.resize(520, 420)
    qtbot.waitUntil(lambda: prompt.geometry() == slot_rect(host), timeout=2000)


def test_ausfahren_deckt_zu_und_laesst_den_knopf_frei(qtbot, paint):
    host = make(qtbot)
    prompt = host.prompt
    eingefahren = prompt.geometry()

    with qtbot.waitSignal(prompt.expanded_changed, timeout=1000) as signal:
        prompt.expand()
    assert signal.args == [True]
    assert prompt.is_expanded()

    # Unterwegs: schon größer, aber noch nicht am Ziel.
    qtbot.waitUntil(lambda: prompt.height() > eingefahren.height(), timeout=1000)
    paint(prompt)

    settle(qtbot, host)
    knopf_oben = host.stop.mapTo(host, QPoint(0, 0)).y()
    # Die Unterkante liegt genau auf der Oberkante des Knopfes.
    assert prompt.y() + prompt.height() == knopf_oben
    assert prompt.geometry().contains(host.covered.geometry()), "die Einstellungen sind zugedeckt"
    assert host.childAt(host.covered.geometry().center()) is not host.covered
    paint(prompt)


def test_einfahren_stellt_alles_zurueck(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    prompt.expand()
    settle(qtbot, host)

    with qtbot.waitSignal(prompt.expanded_changed, timeout=1000) as signal:
        prompt.collapse()
    assert signal.args == [False]
    settle(qtbot, host)

    assert not prompt.is_expanded()
    assert prompt.geometry() == slot_rect(host)
    assert host.childAt(host.covered.geometry().center()) is host.covered


def test_klick_auf_den_doppelpfeil_schaltet_um(qtbot, paint):
    host = make(qtbot)
    prompt = host.prompt
    assert prompt.expand_button._pointing_out, "eingefahren zeigen die Pfeile nach außen"

    qtbot.mouseClick(prompt.expand_button, Qt.MouseButton.LeftButton)
    assert prompt.is_expanded()
    assert not prompt.expand_button._pointing_out
    paint(prompt.expand_button)
    settle(qtbot, host)

    qtbot.mouseClick(prompt.expand_button, Qt.MouseButton.LeftButton)
    assert not prompt.is_expanded()
    assert prompt.expand_button._pointing_out
    paint(prompt.expand_button)


def escape() -> QKeyEvent:
    return QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )


def test_escape_faehrt_ein(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    # Eingefahren geht Escape das Feld nichts an.
    assert not prompt.eventFilter(prompt.text, escape())

    prompt.expand()
    settle(qtbot, host)
    assert prompt.eventFilter(prompt.text, escape()), "Escape wird hier verbraucht"
    assert not prompt.is_expanded()


def test_rahmen_wird_hell_unter_der_maus_und_beim_tippen(qtbot, paint):
    host = make(qtbot)
    prompt = host.prompt
    assert prompt.bright == 0.0

    prompt.text.setFocus()
    prompt._update_bright()
    qtbot.waitUntil(lambda: prompt.bright == 1.0, timeout=3000)
    paint(prompt)

    prompt.text.clearFocus()
    prompt._update_bright()
    qtbot.waitUntil(lambda: prompt.bright == 0.0, timeout=3000)


def test_text_laesst_platz_fuer_den_doppelpfeil(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    rahmen = prompt._frame_rect()
    knopf = prompt.expand_button.geometry()
    text = prompt.text.geometry()

    assert rahmen.contains(knopf), "der Doppelpfeil sitzt im Rahmen"
    assert text.right() < knopf.left(), "der Text läuft nicht unter den Doppelpfeil"
    assert text.top() == knopf.top()


def test_ohne_stopp_widget_bis_zum_fensterboden(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    prompt.set_expand_stop(None)
    prompt.expand()
    settle(qtbot, host)

    assert prompt.y() + prompt.height() == host.height()


def test_ohne_bewegung_sitzt_es_sofort(qtbot):
    class Sofort(HaloPromptBox):
        GROW_MS = 0

    host = Host()
    host.prompt.deleteLater()
    host.prompt = Sofort(host.slot, host)
    host.prompt.set_expand_stop(host.stop)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)

    host.prompt.expand()
    knopf_oben = host.stop.mapTo(host, QPoint(0, 0)).y()
    assert host.prompt.y() + host.prompt.height() == knopf_oben
