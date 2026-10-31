"""Die Bausteine bauen, was sie versprechen.

Diese Tests kommen aus der Anwendung, in der der Formularbau entstanden ist.
Dort hatten sie den .ui-Dateien und ihren erzeugten Gegenstücken die Arbeit
abgenommen. Beim Umstellen von XML auf Beschreibungen waren drei Dinge lautlos
verlorengegangen, alle derselben Art - ein Name oder eine Eigenschaft, die in
der XML stand und in der Beschreibung fehlte:

    eine nicht importierte Klasse   der Reiter baute gar nicht mehr auf
    minimumSize 360                 die Spalte liess sich auf 126 Pixel ziehen
    checked=true                    ein Kaestchen startete aus statt an

Der erste Fall fällt beim Starten auf, die beiden anderen erst beim Hinsehen.
Was hier geprüft wird, ist deshalb nicht, DASS gebaut wird, sondern dass jede
Eigenschaft der Beschreibung auch am Bedienelement ankommt.
"""

from __future__ import annotations

import pytest
from PyQt6.QtWidgets import QCheckBox, QLabel, QPushButton, QWidget

from qt_controls_pyrs import (
    CompactDropdown, CompactIntField, CompactNumberField, CompactResultGrid
)
from qt_controls_pyrs.formbuilder import (
    Auswahlknopf, Ganzzahl, Gruppe, Hinweis, Knopf, Platz, Raster, Schalter,
    Text, Wahl, Zahl, Zeile, baue
)


def test_jeder_baustein_wird_zu_seinem_bedienelement(qtbot):
    beschreibung = [
        Gruppe("Probe", [
            [Zahl("zahl", "Zahl", "mm", dict(min=1.0, max=9.0, stellen=2, wert=3.0))],
            [Ganzzahl("stueck", "Stueck", "Stueck", dict(min=0, max=50, wert=7))],
            [Wahl("auswahl", "Auswahl")],
            [Text("text", "Text", platzhalter="hier")],
            [Schalter("schalter", "Schalter")],
            [Hinweis("ein Hinweis", name="hinweis")],
        ]),
        Zeile([Knopf("knopf", "Knopf")]),
        Raster("raster", "Ergebnis"),
        Platz("platz"),
    ]
    widget, ui = baue(beschreibung)
    qtbot.addWidget(widget)

    assert isinstance(ui.zahl, CompactNumberField)
    assert ui.zahl.value() == pytest.approx(3.0)
    assert ui.zahl.unit() == "mm"
    assert ui.zahl.spin.decimals() == 2

    assert isinstance(ui.stueck, CompactIntField)
    assert ui.stueck.value() == 7

    assert isinstance(ui.auswahl, CompactDropdown)
    assert ui.text.placeholderText() == "hier"
    assert isinstance(ui.schalter, QCheckBox)
    assert isinstance(ui.hinweis, QLabel)
    assert isinstance(ui.knopf, QPushButton)
    assert isinstance(ui.raster, CompactResultGrid)
    assert isinstance(ui.platz, QWidget)


def test_vorgaben_gehen_nicht_verloren(qtbot):
    """Angehakt, gesperrt, unsichtbar, Erklärungstext - alles stand in der XML."""
    widget, ui = baue([
        Gruppe("Probe", [
            [Schalter("an", "An", angehakt=True, hinweis="erklaert")],
            [Schalter("aus", "Aus")],
            [Auswahlknopf("gewaehlt", "Gewaehlt", angehakt=True)],
        ]),
        Zeile([
            Knopf("vorgabe", "Berechnen", vorgabe=True),
            Knopf("gesperrt", "Abbrechen", aktiv=False),
            Knopf("versteckt", "Kamera", sichtbar=False),
        ]),
    ])
    qtbot.addWidget(widget)

    assert ui.an.isChecked() and ui.an.toolTip() == "erklaert"
    assert not ui.aus.isChecked()
    assert ui.gewaehlt.isChecked()
    assert ui.vorgabe.isDefault()
    assert not ui.gesperrt.isEnabled()
    assert not ui.versteckt.isVisible()


def test_lange_eintraege_ziehen_die_spalte_nicht_auseinander(qtbot):
    """Die Breitenbremse der Auswahlfelder, früher als sizeAdjustPolicy in der XML."""
    widget, ui = baue([Gruppe("Probe", [[Wahl("auswahl", "Auswahl", zeichen=12)]])])
    qtbot.addWidget(widget)

    ui.auswahl.addItems(["kurz", "Rueckschlagventil (schliesst bei offenem Sauger)"])
    assert ui.auswahl.minimumContentsLength() == 12


def test_ein_unbekannter_name_sagt_welche_es_gibt(qtbot):
    widget, ui = baue([Gruppe("Probe", [[Zahl("laenge", "Laenge", "mm")]])])
    qtbot.addWidget(widget)

    with pytest.raises(AttributeError, match="laenge"):
        _ = ui.gibtesnicht


def test_ein_unbekannter_baustein_sagt_was_er_ist(qtbot):
    """Ein neuer Zeilentyp braucht einen Zweig in _zelle() - und zwar laut."""
    with pytest.raises(TypeError, match="object"):
        baue([Gruppe("Probe", [[object()]])])


def test_beschriftung_oben_statt_daneben(qtbot):
    """`oben=True` legt zwei Rasterzeilen je Formularzeile an.

    Nebeneinander addieren sich Beschriftung und Feld; stehen zwei Paare in
    einer Zeile, addieren sich vier Breiten. Übereinander zählt je Spalte das
    grössere von beiden.
    """
    daneben, _ = baue([Gruppe("Probe", [
        [Zahl("a", "Eine lange Beschriftung", "mm"),
         Zahl("b", "Noch eine lange", "mm")],
    ])])
    oben, _ = baue([Gruppe("Probe", [
        [Zahl("a", "Eine lange Beschriftung", "mm"),
         Zahl("b", "Noch eine lange", "mm")],
    ], oben=True)])
    qtbot.addWidget(daneben)
    qtbot.addWidget(oben)

    assert oben.sizeHint().width() < daneben.sizeHint().width()
    assert oben.sizeHint().height() > daneben.sizeHint().height()


def test_eine_zeile_ohne_rahmen_dehnt_auf_wunsch(qtbot):
    """Ohne `dehnen` schwimmen zwei Knöpfe in voller Breite auseinander."""
    eng, _ = baue([Zeile([Knopf("a", "Eins"), Knopf("b", "Zwei")], dehnen=True)])
    qtbot.addWidget(eng)
    eng.resize(600, 60)
    eng.show()
    qtbot.waitExposed(eng)

    knoepfe = eng.findChildren(QPushButton)
    assert len(knoepfe) == 2
    # Mit Dehnraum rechts bleiben beide links beieinander.
    assert knoepfe[1].geometry().right() < 400


def test_ein_hinweis_hat_eine_mindestbreite(qtbot):
    """Ohne sie bricht ein langer Hinweis in eine Säule von zwei Wörtern um."""
    from qt_controls_pyrs import COMPACT_WRAP_WIDTH

    widget, ui = baue([Gruppe("Probe", [
        [Hinweis("Ein ziemlich langer Erklaerungstext, der umbrechen soll, "
                 "aber nicht zu einer Saeule werden darf.", name="h")],
    ])])
    qtbot.addWidget(widget)

    assert ui.h.wordWrap()
    assert ui.h.minimumWidth() == COMPACT_WRAP_WIDTH
    assert ui.h.property("role") == "note"
