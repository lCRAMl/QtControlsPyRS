import pytest
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QFrame, QLabel

from qt_controls_pyrs import (
    HaloDoubleSpinBox, HaloGroupBox, HaloSpinBox, IntField, NumberField,
    ResultGrid, StaleBanner, mono_font
)


def zeige(qtbot, widget):
    widget.resize(widget.sizeHint())
    qtbot.addWidget(widget)
    widget.show()
    qtbot.waitExposed(widget)
    return widget


# ----------------------------------------------------------------------
# NumberField
# ----------------------------------------------------------------------

def test_numberfield_benutzt_das_halo_zahlenfeld(qtbot, paint):
    feld = zeige(qtbot, NumberField("mm", minimum=10, maximum=3000, value=360.0))

    assert isinstance(feld.spin, HaloDoubleSpinBox)
    assert feld.value() == pytest.approx(360.0)
    assert feld.unit() == "mm"
    paint(feld)


def test_numberfield_meldet_aenderungen(qtbot):
    feld = zeige(qtbot, NumberField("mm"))

    with qtbot.waitSignal(feld.value_changed, timeout=1000) as signal:
        feld.spin.setValue(12.5)
    assert signal.args == [pytest.approx(12.5)]


def test_set_value_loest_nichts_aus(qtbot):
    """Sonst entsteht eine Rueckkopplung, wenn ein Tab sein Feld nachfuehrt."""
    feld = zeige(qtbot, NumberField("mm"))
    gesehen = []
    feld.value_changed.connect(gesehen.append)

    feld.set_value(7.0)
    assert feld.value() == pytest.approx(7.0)
    assert gesehen == []

    feld.spin.setValue(8.0)
    assert gesehen == [pytest.approx(8.0)]


def test_configure_setzt_nachtraeglich_und_gibt_sich_selbst_zurueck(qtbot):
    feld = zeige(qtbot, NumberField())

    zurueck = feld.configure("kg", minimum=1.0, maximum=99.0, decimals=3,
                             step=0.5, value=42.5, tooltip="Gewicht")
    assert zurueck is feld
    assert feld.unit() == "kg"
    assert (feld.spin.minimum(), feld.spin.maximum()) == (1.0, 99.0)
    assert feld.spin.decimals() == 3
    assert feld.spin.singleStep() == pytest.approx(0.5)
    assert feld.value() == pytest.approx(42.5)
    assert feld.spin.toolTip() == "Gewicht"


def test_fehler_faerbt_den_rahmen_und_steht_unter_dem_feld(qtbot, paint):
    """Ein Stylesheet-Rand griffe nicht - die Leiste zeichnet ihren Rahmen selbst."""
    feld = zeige(qtbot, NumberField("mm"))
    assert feld.spin.alert_color() is None

    feld.set_error("zu kurz")
    assert feld.message() == "zu kurz"
    assert feld.spin.alert_color() == QColor(feld.ERROR)
    paint(feld)

    feld.set_warning("knapp")
    assert feld.spin.alert_color() == QColor(feld.WARNING)
    paint(feld)

    feld.clear_message()
    assert feld.message() == ""
    assert feld.spin.alert_color() is None


def test_der_platz_fuer_die_meldung_bleibt_reserviert(qtbot):
    """Sonst springt das Formular, sobald eine Meldung kommt oder geht."""
    feld = zeige(qtbot, NumberField("mm"))
    leer = feld.sizeHint().height()

    feld.set_error("etwas stimmt hier nicht")
    assert feld.sizeHint().height() == leer


def test_sperren_reicht_bis_zum_spinfeld(qtbot):
    feld = zeige(qtbot, NumberField("mm"))

    feld.setEnabled(False)
    assert not feld.spin.isEnabled()


# ----------------------------------------------------------------------
# IntField
# ----------------------------------------------------------------------

def test_intfield_benutzt_das_ganzzahlige_halo_feld(qtbot, paint):
    feld = zeige(qtbot, IntField("Stueck", maximum=200, value=12))

    assert isinstance(feld.spin, HaloSpinBox)
    assert feld.value() == 12
    assert isinstance(feld.value(), int)
    paint(feld)


def test_null_kann_automatisch_heissen(qtbot, paint):
    """Ohne Sondertext waere aus der Anzeige nicht zu erkennen, was 0 bedeutet."""
    feld = zeige(qtbot, IntField("Stueck", special_zero_text="automatisch"))

    assert feld.spin.specialValueText() == "automatisch"
    assert feld.value() == 0
    paint(feld)


def test_set_maximum_rutscht_nicht_unter_die_untergrenze(qtbot):
    feld = zeige(qtbot, IntField("Stueck", minimum=5, maximum=200, value=10))

    feld.set_maximum(2)
    assert feld.spin.maximum() == 5, "Die Obergrenze darf die Untergrenze nicht unterschreiten"


def test_intfield_meldet_ganze_zahlen(qtbot):
    feld = zeige(qtbot, IntField("Stueck", maximum=50))

    with qtbot.waitSignal(feld.value_changed, timeout=1000) as signal:
        feld.spin.setValue(7)
    assert signal.args == [7]


# ----------------------------------------------------------------------
# ResultGrid
# ----------------------------------------------------------------------

def test_resultgrid_sitzt_in_einem_halo_rahmen(qtbot, paint):
    raster = zeige(qtbot, ResultGrid("Ergebnis"))

    assert isinstance(raster, HaloGroupBox)
    assert raster.title() == "Ergebnis"
    paint(raster)


def test_zeilen_werden_ueber_ihren_schluessel_angesprochen(qtbot, paint):
    """Ueber die Nummer waere jede eingefuegte Zeile eine Fehlerquelle."""
    raster = zeige(qtbot, ResultGrid())
    raster.add_row("total", "Pakete gesamt")
    raster.add_separator()
    raster.add_row("weight", "Gesamtgewicht")

    assert raster.keys() == ("total", "weight")

    raster.set_value("total", "80")
    raster.set_value("weight", "400.0 kg", "#ef6a5a")
    paint(raster)

    raster.clear_values("-")
    assert raster.keys() == ("total", "weight")


def test_eine_unbekannte_zeile_wird_still_uebergangen(qtbot):
    raster = zeige(qtbot, ResultGrid())
    raster.add_row("total", "Pakete gesamt")

    raster.set_value("gibtesnicht", "42")      # darf nicht werfen
    assert raster.keys() == ("total",)


def test_die_werte_stehen_in_fester_laufweite(qtbot):
    """Damit Stellen untereinander stehen und sich zwei Laeufe vergleichen lassen."""
    raster = zeige(qtbot, ResultGrid())
    raster.add_row("total", "Pakete gesamt", "80")

    wert = raster._rows["total"]
    assert isinstance(wert, QLabel)
    assert wert.font().family() == mono_font().family()


# ----------------------------------------------------------------------
# StaleBanner
# ----------------------------------------------------------------------

def test_das_band_versteckt_sich_solange_es_nichts_zu_sagen_hat(qtbot, paint):
    band = StaleBanner()
    qtbot.addWidget(band)

    assert not band.isVisible()

    band.show_message("Ergebnis veraltet")
    assert band.isVisible()
    assert band.message() == "Ergebnis veraltet"
    band.resize(320, 30)
    paint(band)

    band.hide_message()
    assert not band.isVisible()


def test_das_band_zeichnet_sich_selbst(qtbot, paint):
    """Gezeichnet statt per Stylesheet - sonst erbt die Beschriftung den Rahmen."""
    band = StaleBanner()
    qtbot.addWidget(band)
    band.show_message("Ergebnis veraltet")
    band.resize(320, 30)
    band.show()
    qtbot.waitExposed(band)

    assert isinstance(band, QFrame)
    assert band.styleSheet() == ""
    paint(band)
