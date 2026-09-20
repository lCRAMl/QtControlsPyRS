from PyQt6.QtWidgets import QLabel

from qt_controls_pyrs import StatusBar

LONG = (
    "Fehler: Unbekanntes Status-Antwortformat. Beispiel-Antwort: "
    "{'code': 200, 'msg': 'success', 'data': {'taskId': 'abc123', 'state': 'waiting', "
    "'failMsg': 'Eine absichtlich sehr lange Meldung, die niemals in eine "
    "einzige Zeile passt.'}}"
)


def make(qtbot, host) -> StatusBar:
    window, slot = host
    bar = StatusBar(slot, window)
    bar.show()
    qtbot.waitUntil(lambda: bar.width() > 0, timeout=1000)
    return bar


def test_kurze_meldung_bleibt_einzeilig(qtbot, host, paint):
    bar = make(qtbot, host)
    bar.setText("Bereit")

    assert bar.height() == 20
    assert bar.text() == "Bereit"
    assert not bar._up.isVisible()
    paint(bar)


def test_lange_meldung_klappt_auf_ohne_das_fenster_zu_aendern(qtbot, host, paint):
    window, slot = host
    bar = make(qtbot, host)

    groesse_vorher = window.size()
    unterkante = slot.mapTo(window, slot.rect().bottomLeft()).y()

    bar.setText(LONG)
    qtbot.waitUntil(lambda: bar.height() > 20, timeout=2000)

    assert window.size() == groesse_vorher, "Fenster darf sich nicht veraendern"
    assert abs((bar.y() + bar.height()) - unterkante) <= 1, "Unterkante verschoben"
    assert bar.width() == slot.width()
    paint(bar)


def test_klappt_von_selbst_zurueck_und_bietet_scrollpfeile(qtbot, host):
    bar = make(qtbot, host)
    bar.HOLD_MS = 300

    bar.setText(LONG)
    qtbot.waitUntil(lambda: bar.height() > 20, timeout=2000)
    qtbot.waitUntil(lambda: bar.height() == 20, timeout=3000)

    assert bar._up.isVisible() and bar._down.isVisible()

    vorher = bar._scroll.verticalScrollBar().value()
    bar._down.click()
    assert bar._scroll.verticalScrollBar().value() > vorher


def test_klick_klappt_wieder_auf(qtbot, host):
    bar = make(qtbot, host)
    bar.HOLD_MS = 300

    bar.setText(LONG)
    qtbot.waitUntil(lambda: bar.height() == 20, timeout=4000)

    bar.expand()
    qtbot.waitUntil(lambda: bar.height() > 20, timeout=2000)


def test_folgt_dem_platzhalter_wenn_ein_nachbar_breiter_wird(qtbot, host):
    """Regression: sonst ueberdeckt die Leiste den Nachbarn in der Zeile."""
    window, slot = host

    nachbar = QLabel("0")
    slot.parentWidget().layout().addWidget(nachbar)
    bar = make(qtbot, host)
    bar.setText("Bereit")

    nachbar.setText("Ein deutlich laengerer Text als vorher")
    qtbot.waitUntil(lambda: bar.width() == slot.width(), timeout=2000)

    assert bar.x() + bar.width() <= slot.x() + slot.width()


def test_verhaelt_sich_wie_ein_label(qtbot, host):
    bar = make(qtbot, host)

    bar.setText("Erste Meldung")
    assert bar.text() == "Erste Meldung"
    bar.setText("Zweite Meldung")
    assert bar.text() == "Zweite Meldung"
    assert bar.toolTip() == "Zweite Meldung"
