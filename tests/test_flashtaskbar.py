import sys

from PyQt6.QtWidgets import QWidget

from qt_controls_pyrs import flash_taskbar, stop_flashing
from qt_controls_pyrs.flashtaskbar import FLASHW_ALL


def test_blinken_auf_einem_echten_fenster(qtbot):
    fenster = QWidget()
    qtbot.addWidget(fenster)
    fenster.show()
    qtbot.waitExposed(fenster)

    ergebnis = flash_taskbar(int(fenster.winId()))
    assert ergebnis is (sys.platform == "win32")

    assert stop_flashing(int(fenster.winId())) is (sys.platform == "win32")


def test_eigene_anzahl_und_flags(qtbot):
    fenster = QWidget()
    qtbot.addWidget(fenster)
    fenster.show()
    qtbot.waitExposed(fenster)

    assert flash_taskbar(int(fenster.winId()), count=1, flags=FLASHW_ALL) is (
        sys.platform == "win32"
    )


def test_unbekanntes_fenster_stuerzt_nicht_ab():
    # Ungueltiges Handle: Windows meldet nur einen Fehlercode zurueck.
    flash_taskbar(0)
