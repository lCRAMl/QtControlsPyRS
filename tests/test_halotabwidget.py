import pytest
from PyQt6 import sip
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from qt_controls_pyrs import HaloTabWidget
from qt_controls_pyrs.tabs.halotabwidget import _LINE_DAMPING, _SLIDE_DAMPING, _Spring


def page(text: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.addWidget(QLabel(text))
    layout.addWidget(QPushButton(f"Knopf {text}"))
    layout.addStretch(1)
    return widget


def make(qtbot, names=("Einstellungen", "Prompt"), cls=HaloTabWidget) -> HaloTabWidget:
    tabs = cls()
    for name in names:
        tabs.addTab(page(name), name)
    tabs.resize(420, 260)
    qtbot.addWidget(tabs)
    tabs.show()
    qtbot.waitExposed(tabs)
    return tabs


def settle(qtbot, tabs: HaloTabWidget) -> None:
    qtbot.waitUntil(lambda: not tabs.is_sliding(), timeout=3000)
    qtbot.waitUntil(
        lambda: tabs.tabBar().line_position() == float(tabs.currentIndex()), timeout=3000
    )


def test_ist_ein_qtabwidget(qtbot):
    tabs = make(qtbot)

    assert isinstance(tabs, QTabWidget)
    assert tabs.count() == 2
    assert tabs.tabText(1) == "Prompt"

    with qtbot.waitSignal(tabs.currentChanged, timeout=1000) as signal:
        tabs.setCurrentIndex(1)
    assert signal.args == [1]
    # Die neue Seite ist sofort die aktuelle — das Gleiten ist nur die Anzeige.
    assert tabs.currentIndex() == 1
    assert tabs.currentWidget() is tabs.widget(1)


def test_reiter_teilen_sich_die_ganze_breite(qtbot):
    tabs = make(qtbot, ("Einstellungen", "Prompt", "Verlauf"))
    bar = tabs.tabBar()

    assert bar.width() == tabs.width()
    widths = [bar.tabRect(i).width() for i in range(bar.count())]
    assert max(widths) - min(widths) <= 1
    assert sum(widths) == bar.width()
    assert bar.height() == HaloTabWidget.HEIGHT


def test_inhalt_gleitet_und_wird_dabei_unscharf(qtbot, paint):
    tabs = make(qtbot)

    tabs.setCurrentIndex(1)
    assert tabs.is_sliding()
    curtain = tabs._curtain
    assert curtain.geometry() == tabs._page_rect(tabs.currentWidget())
    assert not curtain._from_blur.isNull() and curtain._from_blur is not curtain._from

    qtbot.waitUntil(lambda: 0.1 < curtain.value() < 0.9, timeout=1000)
    paint(tabs)
    settle(qtbot, tabs)
    assert not curtain.isVisible()
    assert curtain._to.isNull(), "die Aufnahmen werden danach freigegeben"
    paint(tabs)


def test_die_decke_laesst_keinen_klick_durch(qtbot):
    tabs = make(qtbot)
    clicks = []
    button = tabs.widget(1).findChild(QPushButton)
    button.clicked.connect(lambda: clicks.append(True))

    tabs.setCurrentIndex(1)
    center = button.mapTo(tabs, button.rect().center())
    assert tabs.childAt(center) is tabs._curtain
    qtbot.mouseClick(tabs._curtain, Qt.MouseButton.LeftButton, pos=center - tabs._curtain.pos())
    assert clicks == []

    settle(qtbot, tabs)
    qtbot.mouseClick(button, Qt.MouseButton.LeftButton)
    assert clicks == [True]


def test_der_strich_gleitet_zum_neuen_reiter(qtbot, paint):
    tabs = make(qtbot)
    bar = tabs.tabBar()
    assert bar.line_position() == 0.0
    assert bar.label_alpha(0) == 1.0
    assert bar.label_alpha(1) == pytest.approx(HaloTabWidget.IDLE_ALPHA)

    tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: 0.2 < bar.line_position() < 0.8, timeout=1000)
    # Die Beschriftungen blenden mit dem Strich um.
    assert HaloTabWidget.IDLE_ALPHA < bar.label_alpha(1) < 1.0
    rect = bar._line_rect()
    assert bar.tabRect(0).left() < rect.left() < bar.tabRect(1).left()
    assert rect.height() == HaloTabWidget.LINE
    paint(bar)

    settle(qtbot, tabs)
    assert bar._line_rect().left() == bar.tabRect(1).left()
    assert bar.label_alpha(1) == 1.0


def test_klick_auf_einen_reiter_wechselt(qtbot):
    tabs = make(qtbot)
    bar = tabs.tabBar()

    qtbot.mouseClick(bar, Qt.MouseButton.LeftButton, pos=bar.tabRect(1).center())
    assert tabs.currentIndex() == 1
    assert tabs.is_sliding()


def test_richtung_folgt_der_lage_des_reiters(qtbot):
    tabs = make(qtbot, ("A", "B", "C"))

    tabs.setCurrentIndex(2)
    assert tabs._curtain._forward, "neuer Reiter rechts: alles wandert nach links"
    settle(qtbot, tabs)

    tabs.setCurrentIndex(0)
    assert not tabs._curtain._forward
    settle(qtbot, tabs)


def test_zurueck_mitten_im_gleiten_kehrt_die_bewegung_um(qtbot, paint):
    tabs = make(qtbot)
    curtain = tabs._curtain

    tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: 0.3 < curtain.value() < 0.7, timeout=1000)
    before = curtain.value()
    pages = (curtain._from_page, curtain._to_page)

    tabs.setCurrentIndex(0)
    # Keine neuen Aufnahmen, kein Sprung: dieselben Seiten, dieselbe Lage.
    assert (curtain._from_page, curtain._to_page) == pages
    assert curtain.value() == pytest.approx(before, abs=0.05)
    qtbot.waitUntil(lambda: curtain.value() < before - 0.1, timeout=1000)
    paint(tabs)

    settle(qtbot, tabs)
    assert tabs.currentIndex() == 0
    assert tabs.tabBar().line_position() == 0.0


def test_dritter_reiter_mitten_im_gleiten(qtbot, paint):
    tabs = make(qtbot, ("A", "B", "C"))
    curtain = tabs._curtain

    tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda: 0.3 < curtain.value() < 0.7, timeout=1000)
    tabs.setCurrentIndex(2)
    # Der Zwischenstand gleitet als Ganzes hinaus, die dritte Seite herein.
    assert curtain._from_page is None
    assert curtain._to_page is tabs.widget(2)
    assert curtain.value() == 0.0
    paint(tabs)

    settle(qtbot, tabs)
    assert tabs.currentIndex() == 2


def test_verborgen_wird_nicht_geglitten(qtbot):
    """Wie beim Programmstart: erst den gespeicherten Reiter setzen, dann zeigen."""
    tabs = HaloTabWidget()
    tabs.addTab(page("A"), "A")
    tabs.addTab(page("B"), "B")
    qtbot.addWidget(tabs)

    tabs.setCurrentIndex(1)
    assert not tabs.is_sliding()
    assert tabs.tabBar().line_position() == 1.0

    tabs.show()
    qtbot.waitExposed(tabs)
    assert not tabs.is_sliding()


def test_entfernen_und_einfuegen(qtbot, paint):
    tabs = make(qtbot, ("A", "B", "C"))
    bar = tabs.tabBar()

    tabs.setCurrentIndex(2)
    settle(qtbot, tabs)

    # Die aktive Seite verschwindet — es gibt nichts, was hinausgleiten könnte.
    removed = tabs.widget(2)
    tabs.removeTab(2)
    assert not tabs.is_sliding()
    assert bar.line_position() == float(tabs.currentIndex())
    removed.deleteLater()

    # Ein Reiter davor verschiebt den aktiven; der Strich zählt mit.
    tabs.insertTab(0, page("Neu"), "Neu")
    assert bar.line_position() == float(tabs.currentIndex())
    paint(tabs)

    # Die aktive Seite wird ohne removeTab gelöscht — auch dann gleitet
    # nichts ins Leere, und der nächste Wechsel geht glatt.
    settle(qtbot, tabs)
    sip.delete(tabs.currentWidget())
    assert tabs.count() == 2
    assert not tabs.is_sliding()
    tabs.setCurrentIndex(1 - tabs.currentIndex())
    assert tabs.is_sliding()
    settle(qtbot, tabs)


def test_groesse_aendern_beendet_das_gleiten(qtbot):
    tabs = make(qtbot)

    tabs.setCurrentIndex(1)
    assert tabs.is_sliding()
    tabs.resize(500, 300)
    assert not tabs.is_sliding()


def test_ohne_unschaerfe_und_ohne_gleiten(qtbot, paint):
    class Scharf(HaloTabWidget):
        BLUR = 0

    tabs = make(qtbot, cls=Scharf)
    tabs.setCurrentIndex(1)
    assert tabs._curtain._from_blur is tabs._curtain._from
    paint(tabs)
    settle(qtbot, tabs)

    class Sofort(HaloTabWidget):
        SLIDE_MS = 0
        LINE_MS = 0

    tabs = make(qtbot, cls=Sofort)
    tabs.setCurrentIndex(1)
    assert not tabs.is_sliding()
    assert tabs.tabBar().line_position() == 1.0


def test_maus_hellt_einen_inaktiven_reiter_auf(qtbot, paint):
    tabs = make(qtbot)
    bar = tabs.tabBar()

    bar._set_hot(1)
    qtbot.waitUntil(lambda: bar.hover_level(1) == 1.0, timeout=3000)
    assert bar.label_alpha(1) == pytest.approx(HaloTabWidget.HOVER_ALPHA)
    paint(bar)

    # Weiter zum anderen Reiter: der erste blendet von dort aus aus, wo er steht.
    bar._set_hot(0)
    assert bar.hover_level(1) == 1.0
    qtbot.waitUntil(lambda: bar.hover_level(1) == 0.0, timeout=3000)

    # Maus raus: auch der zweite blendet langsam aus, statt zu springen.
    bar.leaveEvent(QEvent(QEvent.Type.Leave))
    assert bar.hover_level(0) > 0.5
    qtbot.waitUntil(lambda: bar.hover_level(0) == 0.0, timeout=3000)


def test_gesperrte_reiter_und_farbe(qtbot, paint):
    tabs = make(qtbot)
    bar = tabs.tabBar()

    tabs.setTabEnabled(1, False)
    assert bar.label_alpha(1) < HaloTabWidget.IDLE_ALPHA
    bar._set_hot(-1)
    paint(tabs)

    tabs.setAccentColor("#ff7a18")
    assert tabs.accent_color() == QColor("#ff7a18")
    tabs.setEnabled(False)
    paint(tabs)


def test_lange_namen_werden_gekuerzt(qtbot, paint):
    tabs = make(qtbot, ("Einstellungen für das Modell und alles darunter", "Prompt"))
    tabs.resize(200, 200)

    assert tabs.tabBar().width() == 200
    paint(tabs)


@pytest.mark.parametrize("damping", [_SLIDE_DAMPING, _LINE_DAMPING])
def test_feder(damping):
    spring = _Spring(damping)
    spring.aim(0.0, 1.0, 0.0, 400)

    assert spring.state(0) == pytest.approx((0.0, 0.0))
    assert spring.state(400)[0] == pytest.approx(1.0, abs=0.002)
    # Sie schwingt kaum merklich über — wie im Vorbild um wenige Tausendstel.
    assert max(spring.state(t)[0] for t in range(0, 401, 5)) < 1.005

    # Umlenken übernimmt Lage und Tempo.
    position, velocity = spring.state(100)
    spring.aim(position, 0.0, velocity, 400)
    assert spring.state(0) == pytest.approx((position, velocity))
    assert spring.state(400)[0] == pytest.approx(0.0, abs=0.01)


def test_rand_wie_die_halo_knoepfe(qtbot, paint):
    class Eingerueckt(HaloTabWidget):
        ROOM = 16

    tabs = make(qtbot, cls=Eingerueckt)
    bar = tabs.tabBar()

    def inset() -> bool:
        return bar.x() == 16 and bar.width() == tabs.width() - 32

    # Qt legt die Leiste bei vielen Gelegenheiten neu an — sie bleibt eingerückt.
    assert inset()
    tabs.resize(500, 300)
    assert inset()
    tabs.addTab(page("Verlauf"), "Verlauf")
    qtbot.waitUntil(inset, timeout=1000)
    tabs.setTabText(2, "Ein deutlich längerer Name")
    qtbot.wait(20)
    qtbot.waitUntil(inset, timeout=1000)
    tabs.removeTab(2)
    qtbot.waitUntil(inset, timeout=1000)
    widths = [bar.tabRect(i).width() for i in range(bar.count())]
    assert sum(widths) == bar.width()

    # Die Seiten behalten die ganze Breite.
    assert tabs.currentWidget().width() == tabs.width()

    # Beim Gleiten bleibt der Rand leer: dort steht nur der Hintergrund.
    tabs.setCurrentIndex(1)
    curtain = tabs._curtain
    qtbot.waitUntil(lambda: 0.3 < curtain.value() < 0.7, timeout=1000)
    image = paint(curtain).toImage()
    background = tabs.palette().color(tabs.backgroundRole())
    width, height = curtain.width(), curtain.height()

    def colors(columns) -> set:
        return {image.pixelColor(x, y).rgb() for x in columns for y in range(height)}

    assert colors(list(range(16)) + list(range(width - 16, width))) == {background.rgb()}
    # Gleich daneben gleitet wirklich etwas — sonst wäre „leer" nichts wert.
    assert len(colors(range(16, 40))) > 1
    settle(qtbot, tabs)
