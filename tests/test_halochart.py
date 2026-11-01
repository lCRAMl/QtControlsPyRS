import math

import pytest
from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QMouseEvent

from qt_controls_pyrs import HaloChart
from qt_controls_pyrs.charts.halochart import _format, _nice_step


def make(qtbot, breite: int = 420, hoehe: int = 260) -> HaloChart:
    bild = HaloChart()
    bild.resize(breite, hoehe)
    qtbot.addWidget(bild)
    bild.show()
    qtbot.waitExposed(bild)
    return bild


RAMPE = [(0.0, 0.0), (1.0, 100.0), (2.0, 150.0), (3.0, 170.0)]


# ----------------------------------------------------------------------
# Inhalt
# ----------------------------------------------------------------------

def test_leeres_diagramm_zeichnet_sich(qtbot, paint):
    """Ohne Kurven gibt es trotzdem Rahmen und Gitter - und keinen Absturz."""
    bild = make(qtbot)

    assert bild.series_names() == ()
    assert bild.x_range() == (0.0, 1.0)
    paint(bild)


def test_kurve_aufnehmen_und_ersetzen(qtbot, paint):
    """Gleicher Name heisst dieselbe Kurve - sonst waechst die Liste bei jeder
    Neuberechnung, und die Farben springen."""
    bild = make(qtbot)

    bild.add_series("Verlauf", RAMPE)
    assert bild.series_names() == ("Verlauf",)

    bild.add_series("Verlauf", [(0.0, 0.0), (1.0, 50.0)])
    assert bild.series_names() == ("Verlauf",)
    assert bild.value_at("Verlauf", 1.0) == pytest.approx(50.0)

    bild.add_series("Zweite", RAMPE)
    assert bild.series_names() == ("Verlauf", "Zweite")
    paint(bild)


def test_kurve_entfernen(qtbot):
    bild = make(qtbot)
    bild.add_series("a", RAMPE)
    bild.add_series("b", RAMPE)

    bild.remove_series("a")
    assert bild.series_names() == ("b",)

    bild.clear()
    assert bild.series_names() == ()


def test_farbe_bleibt_beim_ersetzen_stehen(qtbot):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE, color="#ff0000")
    bild.add_series("Verlauf", [(0.0, 1.0), (1.0, 2.0)])

    assert bild._series[0].color == QColor("#ff0000")


# ----------------------------------------------------------------------
# Achsen
# ----------------------------------------------------------------------

def test_achsen_stellen_sich_auf_die_kurve_ein(qtbot):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)

    x0, x1 = bild.x_range()
    y0, y1 = bild.y_range()
    assert x0 < 0.0 and x1 > 3.0, "Etwas Luft gehoert dazu"
    assert y0 < 0.0 and y1 > 170.0


def test_eine_marke_oberhalb_aller_punkte_bleibt_im_bild(qtbot, paint):
    """Sonst laeuft der Sollwert aus dem Bild - und gerade dort will man ihn
    sehen, naemlich wenn die Kurve ihn nicht erreicht."""
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    bild.add_rule(400.0, label="Sollvakuum")

    _y0, y1 = bild.y_range()
    assert y1 > 400.0
    paint(bild)


def test_feste_spanne_schlaegt_die_selbsteinstellung(qtbot):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)

    bild.set_y_range(0.0, 1000.0)
    assert bild.y_range() == (0.0, 1000.0)

    bild.set_y_range(None)
    assert bild.y_range()[1] < 1000.0


def test_eine_waagerechte_kurve_bekommt_trotzdem_eine_spanne(qtbot, paint):
    """Alle Werte gleich - ohne Abfangen waere die Spanne null und die
    Umrechnung teilte durch null."""
    bild = make(qtbot)
    bild.add_series("Flach", [(0.0, 7.0), (1.0, 7.0), (2.0, 7.0)])

    y0, y1 = bild.y_range()
    assert y1 > y0
    paint(bild)


# ----------------------------------------------------------------------
# Umrechnung und Ablesen
# ----------------------------------------------------------------------

def test_punkte_landen_in_der_zeichenflaeche(qtbot):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    rahmen = bild._plot_rect()

    for x, y in RAMPE:
        punkt = bild._to_px(x, y)
        assert rahmen.left() <= punkt.x() <= rahmen.right()
        assert rahmen.top() <= punkt.y() <= rahmen.bottom()


def test_y_waechst_nach_oben(qtbot):
    """Im Bild heisst oben kleineres y - der haeufigste Dreher beim Zeichnen."""
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)

    unten = bild._to_px(0.0, 0.0)
    oben = bild._to_px(0.0, 170.0)
    assert oben.y() < unten.y()


def test_zwischenwert_wird_geradlinig_gemittelt(qtbot):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)

    assert bild.value_at("Verlauf", 0.0) == pytest.approx(0.0)
    assert bild.value_at("Verlauf", 0.5) == pytest.approx(50.0)
    assert bild.value_at("Verlauf", 1.5) == pytest.approx(125.0)
    assert bild.value_at("Verlauf", 3.0) == pytest.approx(170.0)


def test_ausserhalb_der_kurve_gibt_es_keinen_wert(qtbot):
    """Nicht fortsetzen: eine Kurve, die bei 3 s endet, hat bei 4 s keinen
    Wert, und ihn trotzdem zu zeigen waere erfunden."""
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)

    assert bild.value_at("Verlauf", -0.1) is None
    assert bild.value_at("Verlauf", 3.1) is None
    assert bild.value_at("Gibtsnicht", 1.0) is None


# ----------------------------------------------------------------------
# Marken
# ----------------------------------------------------------------------

def test_linien_und_baender_in_beiden_lagen(qtbot, paint):
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    bild.add_rule(150.0, label="Soll")
    bild.add_rule(2.0, vertical=True, label="Umschaltpunkt")
    bild.add_band(140.0, 175.0, label="Saettigung")
    bild.add_band(1.5, 2.5, vertical=True)

    paint(bild)
    bild.clear_marks()
    paint(bild)


def test_ein_band_nimmt_die_grenzen_in_jeder_reihenfolge(qtbot):
    bild = make(qtbot)
    bild.add_band(200.0, 100.0)

    marke = bild._marks[0]
    assert (marke.low, marke.high) == (100.0, 200.0)


# ----------------------------------------------------------------------
# Lineal unter der Maus
# ----------------------------------------------------------------------

def test_lineal_erscheint_nur_unter_der_maus(qtbot, paint):
    """Das Ereignis wird direkt geschickt, NICHT ueber qtbot.mouseMove().

    qtbot.mouseMove() bewegt den echten Zeiger. Wird das Widget danach
    abgeraeumt, bleibt Qts Vorstellung davon, welches Widget unter der Maus
    liegt, veraltet - und der naechste Test, der auf ein Enter-Ereignis
    wartet, bekommt keines. Gemessen: mit mouseMove() fiel anschliessend
    test_halopromptbox.py::test_rahmen_wird_hell_unter_der_maus_und_beim_tippen
    reproduzierbar aus, allein und ohne Zutun in Ordnung. Ein Test, der einen
    anderen umwirft, ist ein Fehler im Test.
    """
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    assert bild._cursor is None

    mitte = bild._plot_rect().center()
    bild.mouseMoveEvent(QMouseEvent(
        QEvent.Type.MouseMove, mitte, mitte,
        Qt.MouseButton.NoButton, Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    ))
    assert bild._cursor is not None
    paint(bild)

    bild.leaveEvent(QEvent(QEvent.Type.Leave))
    assert bild._cursor is None
    paint(bild)


def test_lineal_am_rechten_rand_klappt_nach_links(qtbot, paint):
    """Sonst steht das Kaestchen zur Haelfte ausserhalb des Bildes."""
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    rahmen = bild._plot_rect()

    bild._cursor = QPointF(rahmen.right() - 2.0, rahmen.center().y())
    paint(bild)


# ----------------------------------------------------------------------
# Im Bild gemessen
# ----------------------------------------------------------------------

def test_kurven_werden_gestrichen_und_nicht_gefuellt(qtbot, paint):
    """Gemessen im BILD, nicht am Zustand - anders faellt es nicht auf.

    drawPath() faerbt den Pfad mit dem zuletzt gesetzten Pinsel und schliesst
    einen offenen Pfad dafuer stillschweigend vom letzten zum ersten Punkt.
    Stand noch der Pinsel eines Bandes, fuellte sich der ganze Keil zwischen
    Kurve und Sehne. Keine Zusicherung ueber Punkte oder Farben haette das
    bemerkt; sichtbar war es sofort.

    Geprueft wird ein Punkt tief unter der Kurve, aber oberhalb der Sehne von
    (0,0) nach (3,170) - genau dort, wo die Fuellung lag.
    """
    bild = make(qtbot, 400, 300)
    bild.add_band(140.0, 175.0)          # setzt den Pinsel, der frueher blieb
    bild.add_series("Verlauf", RAMPE)

    abbild = paint(bild).toImage()

    def farbe_bei(x: float, y: float):
        punkt = bild._to_px(x, y)
        return abbild.pixelColor(round(punkt.x()), round(punkt.y()))

    # Gemessen wird bei x = 1,3 und nicht bei 1,5: dort laeuft eine
    # Gitterlinie, und die faerbt den Bildpunkt. Beim ersten Anlauf war
    # genau das der Grund, warum die Messung auch nach der Behebung noch
    # einen Unterschied fand.
    #
    # Die Sehne von (0,0) nach (3,170) liegt bei x = 1,3 auf y = 73,7, die
    # Kurve auf 115. Der Bezugspunkt liegt UNTER der Sehne - also ausserhalb
    # der Flaeche, die eine gefuellte Kurve einnehmen wuerde -, der Messpunkt
    # dazwischen.
    bezug = farbe_bei(1.3, 40.0)
    gemessen = farbe_bei(1.3, 95.0)

    # Zuerst der Rahmen: eine freie Stelle INNERHALB der Zeichenflaeche muss
    # aussehen wie der Untergrund daneben. Ein gefuellter Rahmen faerbt sonst
    # alles gleichmaessig ein - und faellt beim Vergleich zweier Punkte
    # innerhalb der Flaeche nicht auf, weil beide denselben Schleier tragen.
    assert bezug == abbild.pixelColor(2, 2), (
        "Die Zeichenflaeche ist eingefaerbt - der Rahmen wird gefuellt statt "
        "gestrichen: " + bezug.name()
    )

    assert gemessen == bezug, (
        "Zwischen Sehne und Kurve steht Farbe - sie wird gefuellt statt "
        "gestrichen: " + gemessen.name() + " statt " + bezug.name()
    )


def test_die_kurve_selbst_ist_sichtbar(qtbot, paint):
    """Gegenstueck: ohne das waere der Test oben auch bei leerem Bild gruen."""
    bild = make(qtbot, 400, 300)
    bild.add_series("Verlauf", RAMPE)

    abbild = paint(bild).toImage()
    untergrund = abbild.pixelColor(2, 2)
    auf_der_kurve = bild._to_px(1.5, 125.0)
    gemessen = abbild.pixelColor(round(auf_der_kurve.x()), round(auf_der_kurve.y()))

    assert gemessen != untergrund, "Auf der Kurve muss Farbe stehen"


# ----------------------------------------------------------------------
# Hilfsfunktionen
# ----------------------------------------------------------------------

@pytest.mark.parametrize("spanne,erwartet", [
    (1.0, 0.2), (10.0, 2.0), (100.0, 20.0), (3.0, 0.5), (0.05, 0.01),
])
def test_runde_schrittweiten(spanne, erwartet):
    """Am Gitter sollen Zahlen wie 0,2 stehen und nicht 0,1667."""
    assert _nice_step(spanne, 5) == pytest.approx(erwartet)


def test_schrittweite_bei_leerer_spanne():
    assert _nice_step(0.0, 5) == 1.0
    assert _nice_step(10.0, 0) == 1.0


def test_zahlen_nur_so_genau_wie_noetig():
    assert _format(150.0, 20.0) == "150"
    assert _format(0.25, 0.05) == "0,25"
    assert _format(1.5, 1.0) == "2"


def test_sehr_kleines_diagramm_zeichnet_sich(qtbot, paint):
    """Schmaler als die Raender zusammen - die Zeichenflaeche hat Breite null."""
    bild = make(qtbot)
    bild.add_series("Verlauf", RAMPE)
    bild.setMinimumSize(1, 1)
    bild.resize(20, 20)

    paint(bild)
    assert math.isfinite(bild._to_px(1.0, 100.0).x())
