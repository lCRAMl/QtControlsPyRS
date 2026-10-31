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
from PyQt6.QtWidgets import QStatusBar

from qt_controls_pyrs import (
    COMPACT_HEIGHT, COMPACT_WRAP_WIDTH, CompactButton, CompactCheckBox,
    CompactDoubleSpinBox, CompactDropdown, CompactGroupBox, CompactIntField,
    CompactLineEdit, CompactNumberField, CompactRadioButton,
    CompactResultGrid, CompactSpinBox, HaloButton, HaloCheckBox,
    HaloDoubleSpinBox, HaloDropdown, HaloGroupBox, HaloLineEdit,
    HaloRadioButton, HaloSpinBox, IntField, NumberField, ResultGrid,
    StatusBarButton, WideResultGrid
)


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


def test_die_umbruchbreite_gilt_fuer_das_kaestchen():
    """Dieselbe Kante fuer Kaestchen und fuer Hinweistexte der Anwendung."""
    assert CompactCheckBox.WRAP_WIDTH == COMPACT_WRAP_WIDTH


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
