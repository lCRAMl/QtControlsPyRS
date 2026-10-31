"""Die kompakten Fassungen: dichter als ihre Vorbilder, sonst gleich.

Der erste Test ist der wichtigste und sieht nach Tautologie aus. Er ist keine:
an dieser Bibliothek hängen mehrere Anwendungen, und sie sollen alle gleich
aussehen. Der bequeme Weg zu einer dichteren Oberfläche wäre, HaloButton.HEIGHT
von 45 auf 26 zu setzen - und damit jedes Fenster jeder Anwendung beim nächsten
Update zu verändern, ohne dass jemand darum gebeten hat. Deshalb sind die
kompakten Fassungen neue Klassen, und deshalb stehen die Zahlen der Vorbilder
hier als Zusage aufgeschrieben.
"""

from __future__ import annotations

import pytest
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QSplitter, QStatusBar

from qt_controls_pyrs import (
    COMPACT_HEIGHT, COMPACT_WRAP_WIDTH, CompactButton, CompactCheckBox,
    CompactDoubleSpinBox, CompactDropdown, CompactGroupBox, CompactIntField,
    CompactLineEdit, CompactNumberField, CompactRadioButton,
    CompactResultGrid, CompactSpinBox, Debouncer, HaloButton, HaloCheckBox,
    HaloDoubleSpinBox, HaloDropdown, HaloGroupBox, HaloLineEdit,
    HaloRadioButton, HaloSpinBox, IntField, NumberField, ResultGrid,
    StatusBarButton, WideResultGrid
)
from qt_controls_pyrs import windowstate


#: Die Masse der Vorbilder, wie sie waren und bleiben sollen.
VORBILDER = {
    HaloButton: dict(HEIGHT=45, ROOM=16, PAD=22),
    HaloDropdown: dict(HEIGHT=45, ROOM=16, ROOM_Y=4, PAD=16),
    HaloLineEdit: dict(HEIGHT=45, ROOM=16, ROOM_Y=4, PAD=16),
    HaloSpinBox: dict(HEIGHT=45, ROOM=16, ROOM_Y=4, PAD=16, ARROW_ZONE=26),
    HaloDoubleSpinBox: dict(HEIGHT=45, ROOM=16, ROOM_Y=4, PAD=16, ARROW_ZONE=26),
    HaloGroupBox: dict(PAD_X=16, PAD_TOP=10, PAD_BOTTOM=16),
    HaloCheckBox: dict(ROOM=8, BOX=18, GAP=8, WRAP_WIDTH=0),
    HaloRadioButton: dict(ROOM=8, RING=18, GAP=8),
    NumberField: dict(GAP=6, MIN_WIDTH=110, UNIT_WIDTH=40),
    IntField: dict(GAP=6, MIN_WIDTH=110, UNIT_WIDTH=40),
    ResultGrid: dict(PAD_X=16, PAD_TOP=10, PAD_BOTTOM=16, COLUMNS=1),
}


@pytest.mark.parametrize("klasse", list(VORBILDER), ids=lambda k: k.__name__)
def test_die_vorbilder_bleiben_wie_sie_waren(klasse):
    """Eine kompakte Fassung darf ihr Vorbild nicht nachträglich verändern.

    Fällt dieser Test, hat jemand die Vorgaben einer Halo-Klasse geändert statt
    eine eigene Fassung daneben zu stellen. Das ändert das Aussehen JEDER
    Anwendung, die diese Bibliothek benutzt - auch der, die niemand gerade
    offen hat.
    """
    for feld, erwartet in VORBILDER[klasse].items():
        assert getattr(klasse, feld) == erwartet, (
            klasse.__name__ + "." + feld + " ist " + str(getattr(klasse, feld))
            + " statt " + str(erwartet) + " - das aendert bestehende Fenster."
        )


#: Kompakte Fassung -> ihr Vorbild.
PAARE = [
    (CompactButton, HaloButton),
    (CompactDropdown, HaloDropdown),
    (CompactLineEdit, HaloLineEdit),
    (CompactSpinBox, HaloSpinBox),
    (CompactDoubleSpinBox, HaloDoubleSpinBox),
    (CompactGroupBox, HaloGroupBox),
    (CompactCheckBox, HaloCheckBox),
    (CompactRadioButton, HaloRadioButton),
    (CompactNumberField, NumberField),
    (CompactIntField, IntField),
    (CompactResultGrid, ResultGrid),
    (StatusBarButton, HaloButton),
]


@pytest.mark.parametrize("eng, weit", PAARE, ids=lambda k: k.__name__)
def test_jede_kompakte_fassung_erbt_von_ihrem_vorbild(eng, weit):
    """Geändert werden Zahlen, nicht Verhalten - also wird geerbt."""
    assert issubclass(eng, weit)


@pytest.mark.parametrize("eng, weit", PAARE, ids=lambda k: k.__name__)
def test_jede_kompakte_fassung_ist_wirklich_enger(eng, weit):
    """Eine Fassung, die nichts verengt, ist eine Klasse ohne Grund."""
    enger = [
        feld for feld in ("HEIGHT", "ROOM", "PAD", "PAD_X", "PAD_TOP",
                          "PAD_BOTTOM", "BOX", "RING", "GAP", "MIN_WIDTH",
                          "UNIT_WIDTH", "ARROW_ZONE")
        if hasattr(weit, feld) and getattr(eng, feld, None) is not None
        and getattr(eng, feld) < getattr(weit, feld)
    ]
    assert enger, (
        eng.__name__ + " ist an keiner Stelle enger als " + weit.__name__
    )


def test_die_leisten_knoepfe_halten_eine_statusleiste_flach(qtbot):
    """Eine Statusleiste ist so hoch wie ihr höchstes Element.

    Mit einem gewöhnlichen HaloButton wird sie 77 Bildpunkte hoch - gut
    anderthalb Zentimeter für eine Zeile Text. Genau dafür gibt es
    StatusBarButton.
    """
    weit = QStatusBar()
    weit.addPermanentWidget(HaloButton("Probe"))
    qtbot.addWidget(weit)

    eng = QStatusBar()
    eng.addPermanentWidget(StatusBarButton("Probe"))
    qtbot.addWidget(eng)

    assert eng.sizeHint().height() < weit.sizeHint().height() / 2
    assert eng.sizeHint().height() <= 40


def test_die_umbruchbreite_gilt_fuer_kaestchen_und_hinweise():
    """Dieselbe Kante, deshalb dieselbe Zahl.

    Vorher stand die 240 an drei Stellen: im Kästchen, im Formularbau und als
    eine dritte, von niemandem benutzte Konstante daneben.
    """
    from qt_controls_pyrs import formbuilder

    assert CompactCheckBox.WRAP_WIDTH == COMPACT_WRAP_WIDTH
    assert formbuilder.COMPACT_WRAP_WIDTH == COMPACT_WRAP_WIDTH


def test_das_breite_raster_hat_mehr_spalten_als_das_kompakte():
    assert WideResultGrid.COLUMNS > CompactResultGrid.COLUMNS
    assert issubclass(WideResultGrid, CompactResultGrid)


def test_die_eingabefelder_sind_so_hoch_wie_angegeben(qtbot):
    """Die Zahl im Modul und das, was auf dem Schirm steht, sind dasselbe."""
    for klasse in (CompactLineEdit, CompactDropdown, CompactSpinBox,
                   CompactDoubleSpinBox, CompactButton):
        widget = klasse()
        qtbot.addWidget(widget)
        gemessen = widget.sizeHint().height()
        assert gemessen >= COMPACT_HEIGHT, klasse.__name__
        # Die Luft je Seite kommt dazu, mehr als das Doppelte ist zu viel.
        assert gemessen <= COMPACT_HEIGHT + 4 * klasse.ROOM, klasse.__name__


# ----------------------------------------------------------------------
# Debouncer
# ----------------------------------------------------------------------

def test_der_debouncer_sammelt_schnelle_aenderungen(qtbot):
    aufrufe = []
    bremse = Debouncer(lambda: aufrufe.append(1), delay_ms=50)

    bremse.trigger()
    bremse.trigger()
    bremse.trigger()
    assert bremse.pending
    assert aufrufe == []

    qtbot.wait(150)
    assert aufrufe == [1], "drei Aenderungen muessen einen Aufruf ergeben"
    assert not bremse.pending


def test_abbrechen_verwirft_was_aussteht(qtbot):
    aufrufe = []
    bremse = Debouncer(lambda: aufrufe.append(1), delay_ms=50)
    bremse.trigger()
    bremse.cancel()
    qtbot.wait(150)
    assert aufrufe == []


def test_sofort_ausloesen_holt_die_letzte_eingabe(qtbot):
    aufrufe = []
    bremse = Debouncer(lambda: aufrufe.append(1), delay_ms=5000)
    bremse.trigger()
    bremse.flush()
    assert aufrufe == [1], "ohne flush() waere die letzte Eingabe verloren"
    assert not bremse.pending

    # Ohne etwas Ausstehendes passiert nichts - flush() ist kein Auslöser.
    bremse.flush()
    assert aufrufe == [1]


# ----------------------------------------------------------------------
# windowstate
# ----------------------------------------------------------------------

def test_ohne_anwendungsnamen_gibt_es_eine_klare_meldung(monkeypatch):
    """Ein leerer Name ist kein brauchbarer Standardwert.

    Unter einem leeren Namen landen die gemerkten Werte irgendwo in der
    Registry, und niemand findet sie wieder, um sie zu löschen. Lieber eine
    Meldung, die sagt, was zu tun ist.
    """
    monkeypatch.setattr(windowstate, "_application", "")
    monkeypatch.setattr(QCoreApplication, "organizationName", staticmethod(lambda: ""))
    monkeypatch.setattr(QCoreApplication, "applicationName", staticmethod(lambda: ""))

    with pytest.raises(RuntimeError, match="set_application"):
        windowstate.application()


def test_der_gesetzte_name_schlaegt_den_von_qt(monkeypatch):
    monkeypatch.setattr(windowstate, "_application", "")
    monkeypatch.setattr(QCoreApplication, "organizationName", staticmethod(lambda: "VonQt"))
    assert windowstate.application() == "VonQt"

    windowstate.set_application("Ausdruecklich")
    assert windowstate.application() == "Ausdruecklich"


def test_eine_gemerkte_teilung_kommt_zurueck(qtbot, monkeypatch, tmp_path):
    """Gespeichert wird der Zustand, nicht zwei Zahlen - siehe restore_splitter."""
    from PyQt6.QtCore import QSettings
    monkeypatch.setattr(windowstate, "_application", "")
    windowstate.set_application("QtControlsPyRSTest")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    monkeypatch.setenv("HOME", str(tmp_path))

    teiler = QSplitter()
    teiler.addWidget(CompactLineEdit())
    teiler.addWidget(CompactLineEdit())
    qtbot.addWidget(teiler)
    teiler.resize(400, 50)
    teiler.setSizes([300, 100])

    windowstate.save_splitter(teiler, "probe")

    zweiter = QSplitter()
    zweiter.addWidget(CompactLineEdit())
    zweiter.addWidget(CompactLineEdit())
    qtbot.addWidget(zweiter)
    zweiter.resize(400, 50)
    windowstate.restore_splitter(zweiter, "probe", fallback=[50, 350])

    # Die Vorgabe darf nicht gewonnen haben.
    assert zweiter.sizes()[0] > zweiter.sizes()[1]


def test_ohne_gemerkte_teilung_gilt_die_vorgabe(qtbot, monkeypatch):
    """Geprüft wird das Verhältnis, nicht der Bildpunkt.

    Qt rechnet die Breite des Griffs von der verfügbaren Breite ab und verteilt
    den Rest: aus 120/280 werden bei 400 Bildpunkten Breite 119/277. Auf
    genaue Zahlen zu prüfen hiesse, die Griffbreite mitzuprüfen - und die
    gehört zum Stil und nicht zu dieser Funktion.
    """
    monkeypatch.setattr(windowstate, "_application", "")
    windowstate.set_application("QtControlsPyRSTestLeer")

    teiler = QSplitter()
    teiler.addWidget(CompactLineEdit())
    teiler.addWidget(CompactLineEdit())
    qtbot.addWidget(teiler)
    teiler.resize(400, 50)

    windowstate.restore_splitter(teiler, "nochnichtbenutzt", fallback=[120, 280])
    links, rechts = teiler.sizes()
    assert links + rechts >= 390, "die Breite muss vollstaendig verteilt sein"
    assert rechts / links == pytest.approx(280 / 120, rel=0.05)
