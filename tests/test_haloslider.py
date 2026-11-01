import pytest

from PyQt6.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt6.QtGui import QEnterEvent
from PyQt6.QtWidgets import QSlider

from qt_controls_pyrs import HaloSlider


def make(qtbot, orientation: Qt.Orientation = Qt.Orientation.Horizontal) -> HaloSlider:
    regler = HaloSlider(orientation)
    regler.setRange(0, 100)
    regler.setValue(50)
    if orientation == Qt.Orientation.Horizontal:
        regler.resize(240, 26)
    else:
        regler.resize(26, 240)
    qtbot.addWidget(regler)
    regler.show()
    qtbot.waitExposed(regler)
    return regler


def _laengs(regler: HaloSlider, value: int) -> QPoint:
    """Der Punkt auf der Leiste, an dem dieser Wert steht."""
    regler_wert = regler.value()
    regler.setValue(value)
    stelle = regler._handle_along()
    regler.setValue(regler_wert)
    quer = regler._center()
    if regler.is_vertical():
        return QPoint(round(quer), round(stelle))
    return QPoint(round(stelle), round(quer))


# ----------------------------------------------------------------------
# QSlider bleibt QSlider
# ----------------------------------------------------------------------

def test_ist_eine_qslider(qtbot, paint):
    regler = make(qtbot)

    assert isinstance(regler, QSlider)
    assert regler.minimum() == 0 and regler.maximum() == 100
    assert regler.value() == 50

    regler.setValue(75)
    assert regler.value() == 75
    paint(regler)


def test_meldet_jede_aenderung(qtbot):
    regler = make(qtbot)
    gesehen = []
    regler.valueChanged.connect(gesehen.append)

    regler.setValue(60)
    regler.setValue(60)   # unveraendert - darf nicht melden
    regler.setValue(10)

    assert gesehen == [60, 10]


def test_tastatur_und_rad_wirken(qtbot, paint):
    regler = make(qtbot)
    regler.setSingleStep(5)

    regler.setFocus()
    qtbot.keyClick(regler, Qt.Key.Key_Right)
    assert regler.value() == 55

    qtbot.keyClick(regler, Qt.Key.Key_Left)
    assert regler.value() == 50
    paint(regler)


def test_grenzen_werden_eingehalten(qtbot):
    regler = make(qtbot)

    regler.setValue(1000)
    assert regler.value() == 100
    regler.setValue(-1000)
    assert regler.value() == 0


# ----------------------------------------------------------------------
# Laufrichtung
# ----------------------------------------------------------------------

def test_waagerecht_laeuft_das_minimum_nach_links(qtbot, paint):
    regler = make(qtbot)

    regler.setValue(0)
    links = regler._handle_along()
    regler.setValue(100)
    rechts = regler._handle_along()

    assert links < rechts
    paint(regler)


def test_senkrecht_liegt_das_minimum_unten(qtbot, paint):
    """Wie bei Qt. y waechst nach unten, das Minimum also beim groesseren y."""
    regler = make(qtbot, Qt.Orientation.Vertical)

    regler.setValue(0)
    unten = regler._handle_along()
    regler.setValue(100)
    oben = regler._handle_along()

    assert unten > oben, "Senkrecht gehoert das Minimum nach unten"
    paint(regler)


def test_umgekehrte_darstellung_dreht_die_leiste(qtbot):
    regler = make(qtbot)
    regler.setValue(0)
    vorher = regler._handle_along()

    regler.setInvertedAppearance(True)
    nachher = regler._handle_along()

    assert nachher > vorher


# ----------------------------------------------------------------------
# Maus
# ----------------------------------------------------------------------

def test_ziehen_am_griff_setzt_den_wert(qtbot, paint):
    regler = make(qtbot)

    qtbot.mousePress(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 50))
    assert regler.isSliderDown()

    qtbot.mouseMove(regler, pos=_laengs(regler, 80))
    assert regler.value() == 80

    qtbot.mouseRelease(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 80))
    assert not regler.isSliderDown()
    paint(regler)


def test_klick_daneben_springt_eine_seite_weiter(qtbot):
    """Wie QSlider es tut - und ausdruecklich NICHT an die Zeigerstelle.

    Die Sammlung haelt sich an ihre Vorbilder. Wer das Springen will,
    schaltet es ein; der naechste Test prueft das.
    """
    regler = make(qtbot)
    regler.setPageStep(10)

    qtbot.mouseClick(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 90))
    assert regler.value() == 60, "Erwartet war eine Seite, kein Sprung ans Ziel"


def test_eingeschaltet_springt_der_klick_ans_ziel(qtbot):
    regler = make(qtbot)
    assert not regler.jump_to_click()

    regler.set_jump_to_click(True)
    qtbot.mouseClick(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 90))

    assert abs(regler.value() - 90) <= 1


def test_ziehen_ueber_das_ende_bleibt_in_den_grenzen(qtbot):
    regler = make(qtbot)

    qtbot.mousePress(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 50))
    qtbot.mouseMove(regler, pos=QPoint(10_000, 13))
    assert regler.value() == 100

    qtbot.mouseMove(regler, pos=QPoint(-10_000, 13))
    assert regler.value() == 0
    qtbot.mouseRelease(regler, Qt.MouseButton.LeftButton, pos=QPoint(0, 13))


# ----------------------------------------------------------------------
# Leuchten und Bildtakt
# ----------------------------------------------------------------------

def test_in_ruhe_laeuft_kein_bildtakt(qtbot):
    """Ein Widget, das still steht, darf keine Rechenzeit ziehen."""
    regler = make(qtbot)
    assert not regler._timer.isActive()
    assert regler.glow() == 0.0


def test_ziehen_laesst_es_leuchten(qtbot, paint):
    regler = make(qtbot)

    qtbot.mousePress(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 50))
    qtbot.waitUntil(lambda: regler.glow() > 0.5, timeout=1000)
    paint(regler)

    qtbot.mouseRelease(regler, Qt.MouseButton.LeftButton, pos=_laengs(regler, 50))
    regler.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: regler.glow() <= 0.01, timeout=3000)
    assert not regler._timer.isActive(), "Danach muss der Bildtakt stehen"


def test_bei_erreichtem_ziel_steht_der_bildtakt(qtbot):
    """Liegt der Zeiger still, darf nichts mehr gerechnet werden.

    Gefunden beim ersten Testlauf: mit der Bedingung "solange die Maus darauf
    steht" lief der Takt endlos mit 16 ms weiter, ohne dass sich ein einziger
    Bildpunkt aenderte.
    """
    regler = make(qtbot)
    regler.enterEvent(QEnterEvent(QPointF(10, 13), QPointF(10, 13), QPointF(10, 13)))

    qtbot.waitUntil(lambda: not regler._timer.isActive(), timeout=2000)
    assert regler.glow() == pytest.approx(regler.HOVER_GLOW, abs=0.02)


def test_eine_leere_spanne_zeichnet_sich_trotzdem(qtbot, paint):
    """Minimum gleich Maximum - ohne Abfangen teilte das durch null."""
    regler = make(qtbot)
    regler.setRange(7, 7)

    assert regler.value() == 7
    paint(regler)


def test_sehr_kurze_leiste_zeichnet_sich_und_laesst_sich_bedienen(qtbot, paint):
    """Schmaler als die beiden Raender zusammen - die Schiene hat Laenge null.

    Gezeichnet wird trotzdem, und ein Klick darf nicht durch null teilen. Der
    zweite Teil ist der eigentliche Grund fuer diesen Test: ohne die Abfrage in
    _value_at() stuerzt hier die Bedienung ab, und das faellt beim blossen
    Zeichnen nicht auf.
    """
    regler = make(qtbot)
    regler.resize(8, 26)

    paint(regler)

    qtbot.mousePress(regler, Qt.MouseButton.LeftButton, pos=QPoint(4, 13))
    qtbot.mouseMove(regler, pos=QPoint(6, 13))
    qtbot.mouseRelease(regler, Qt.MouseButton.LeftButton, pos=QPoint(6, 13))
    assert regler.minimum() <= regler.value() <= regler.maximum()
