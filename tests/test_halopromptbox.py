from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QEnterEvent, QKeyEvent
from PyQt6.QtWidgets import QPushButton, QScrollBar, QSizePolicy, QVBoxLayout, QWidget

from qt_controls_pyrs import HaloPromptBox, HaloScrollBar


class Host(QWidget):
    """Fenster wie im APIImageGenerator: Platzhalter oben, darunter Inhalt und ein Knopf."""

    def __init__(self, cls=HaloPromptBox) -> None:
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

        self.prompt = cls(self.slot, self)
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


def test_klick_auf_eine_leiste_schaltet_um(qtbot, paint):
    host = make(qtbot)
    prompt = host.prompt

    # Eingefahren zeigen beide Pfeile nach außen: oben hinauf, unten hinab.
    assert (prompt.top_bar.base_angle, prompt.bottom_bar.base_angle) == (0.0, 180.0)
    assert prompt.top_bar.turn == 0.0 and prompt.bottom_bar.turn == 0.0

    qtbot.mouseClick(prompt.top_bar, Qt.MouseButton.LeftButton)
    assert prompt.is_expanded()
    # Ausgefahren drehen sich beide um 180 Grad, zeigen also nach innen.
    qtbot.waitUntil(lambda: prompt.top_bar.turn == 1.0, timeout=2000)
    qtbot.waitUntil(lambda: prompt.bottom_bar.turn == 1.0, timeout=2000)
    paint(prompt.top_bar)
    paint(prompt.bottom_bar)
    settle(qtbot, host)

    # Die untere Leiste tut dasselbe.
    qtbot.mouseClick(prompt.bottom_bar, Qt.MouseButton.LeftButton)
    assert not prompt.is_expanded()
    qtbot.waitUntil(lambda: prompt.top_bar.turn == 0.0, timeout=2000)


def test_untere_leiste_laesst_sich_abschalten(qtbot, paint):
    class NurOben(HaloPromptBox):
        BOTTOM_BAR = False

    host = Host(cls=NurOben)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)

    assert not host.prompt.bottom_bar.isVisible()
    # Der Text reicht dann bis unten an den Rand.
    rahmen = host.prompt._frame_rect()
    text = host.prompt.text.geometry()
    assert text.y() + text.height() == rahmen.y() + rahmen.height() - HaloPromptBox.PAD
    paint(host.prompt)


def test_maus_hellt_eine_leiste_auf(qtbot, paint):
    host = make(qtbot)
    bar = host.prompt.top_bar
    assert bar.hover == 0.0

    bar.enterEvent(QEnterEvent(QPointF(1.0, 1.0), QPointF(1.0, 1.0), QPointF(1.0, 1.0)))
    qtbot.waitUntil(lambda: bar.hover == 1.0, timeout=2000)
    paint(bar)

    bar.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: bar.hover == 0.0, timeout=2000)


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


def test_leisten_sitzen_ueber_und_unter_dem_text(qtbot):
    host = make(qtbot)
    prompt = host.prompt

    rahmen = prompt._frame_rect()
    oben = prompt.top_bar.geometry()
    unten = prompt.bottom_bar.geometry()
    text = prompt.text.geometry()

    assert rahmen.contains(oben) and rahmen.contains(unten)
    assert oben.width() == text.width() == unten.width(), "alle drei gleich breit"
    assert oben.y() + oben.height() <= text.y(), "die obere Leiste liegt über dem Text"
    assert text.y() + text.height() <= unten.y(), "die untere darunter"


def test_scrollbar_ist_das_gluehende_band(qtbot):
    host = make(qtbot)
    balken = host.prompt.text.verticalScrollBar()

    assert isinstance(balken, HaloScrollBar)
    assert isinstance(balken, QScrollBar)
    assert balken.sizeHint().width() == HaloScrollBar.THICKNESS


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

    host = Host(cls=Sofort)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)

    host.prompt.expand()
    knopf_oben = host.stop.mapTo(host, QPoint(0, 0)).y()
    assert host.prompt.y() + host.prompt.height() == knopf_oben
