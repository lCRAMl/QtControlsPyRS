from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import QLineEdit

from qt_controls_pyrs import HaloLineEdit


def make(qtbot, text: str = "") -> HaloLineEdit:
    feld = HaloLineEdit()
    if text:
        feld.setText(text)
    feld.resize(feld.sizeHint())
    qtbot.addWidget(feld)
    feld.show()
    qtbot.waitExposed(feld)
    return feld


def enter(feld) -> None:
    point = QPointF(feld.rect().center())
    feld.enterEvent(QEnterEvent(point, point, point))


# ----------------------------------------------------------------------
# QLineEdit bleibt QLineEdit
# ----------------------------------------------------------------------

def test_ist_ein_qlineedit(qtbot, paint):
    feld = make(qtbot)

    assert isinstance(feld, QLineEdit)
    with qtbot.waitSignal(feld.textChanged, timeout=1000) as signal:
        feld.setText("Artikel 4711")
    assert signal.args == ["Artikel 4711"]
    assert feld.text() == "Artikel 4711"
    paint(feld)


def test_tippen_kommt_an(qtbot):
    feld = make(qtbot)
    feld.setFocus()

    qtbot.keyClicks(feld, "abc")
    assert feld.text() == "abc"

    qtbot.keyClick(feld, Qt.Key.Key_Backspace)
    assert feld.text() == "ab"


def test_platzhalter_und_pruefung_bleiben_qt_ueberlassen(qtbot, paint):
    feld = make(qtbot)
    feld.setPlaceholderText("Artikelnummer")
    feld.setMaxLength(4)

    assert feld.placeholderText() == "Artikelnummer"
    paint(feld)

    feld.setText("123456")
    assert feld.text() == "1234"


# ----------------------------------------------------------------------
# Die Leiste
# ----------------------------------------------------------------------

def test_die_schrift_klebt_nicht_am_rahmen(qtbot):
    feld = make(qtbot, "Hallo")

    links = feld.textMargins().left()
    assert links >= feld.ROOM + feld.PAD, (
        "Der Text muesste innerhalb des Rahmens beginnen, nicht darauf"
    )


def test_unter_der_maus_wird_der_rahmen_hell(qtbot, paint):
    feld = make(qtbot)
    assert feld.hover == 0.0

    enter(feld)
    qtbot.waitUntil(lambda: feld.hover == 1.0, timeout=3000)
    paint(feld)

    feld.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: feld.hover == 0.0, timeout=3000)


def test_die_schreibmarke_haelt_den_rahmen_hell(qtbot, paint):
    """Ein Feld, in das getippt wird, bleibt hell - auch ohne Maus darauf.

    Geprueft wird die Zusage und nicht der Weg dorthin: im Offscreen-Betrieb
    liegt der Zeiger auf (0,0) und damit auf dem Feld, und Qt erzeugt das
    Maus-Enter neu, sobald Ereignisse laufen. Ein Test, der sich darauf
    verlaesst, dass die Maus weg ist, prueft die Plattform statt das Widget.
    """
    feld = make(qtbot)

    feld.setFocus()
    qtbot.waitUntil(lambda: feld.focus == 1.0, timeout=3000)
    paint(feld)

    # Ohne Maus, nur mit Schreibmarke: hell.
    feld.hover = 0.0
    assert feld._level() == 1.0

    # Ohne beides: dunkel.
    feld.focus = 0.0
    assert feld._level() == 0.0

    # Und die Maus allein reicht ebenfalls.
    feld.hover = 1.0
    assert feld._level() == 1.0


def test_die_schreibmarke_loest_die_bewegung_aus(qtbot):
    """focusIn und focusOut muessen die Animation starten, nicht nur setzen."""
    feld = make(qtbot)

    feld.focus = 0.0
    feld.setFocus()
    qtbot.waitUntil(lambda: feld.focus == 1.0, timeout=3000)

    feld.clearFocus()
    qtbot.waitUntil(lambda: feld.focus == 0.0, timeout=3000)


def test_gesperrt_wird_blass_gezeichnet(qtbot, paint):
    feld = make(qtbot, "Hallo")
    enter(feld)
    qtbot.waitUntil(lambda: feld.hover == 1.0, timeout=3000)

    feld.setEnabled(False)
    # Ein gesperrtes Feld bekommt kein leaveEvent mehr - es muesste sonst
    # hell stehenbleiben.
    qtbot.waitUntil(lambda: feld.hover == 0.0, timeout=3000)
    paint(feld)
