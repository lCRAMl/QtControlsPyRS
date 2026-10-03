from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QPixmap

from qt_controls_pyrs import HaloImageView


def make(qtbot, text="🗋") -> HaloImageView:
    view = HaloImageView(text)
    view.resize(300, 400)
    qtbot.addWidget(view)
    view.show()
    qtbot.waitExposed(view)
    return view


def solid(width: int, height: int, color: str = "red") -> QPixmap:
    pixmap = QPixmap(width, height)
    pixmap.fill(QColor(color))
    return pixmap


def test_platzhaltertext_ohne_bild(qtbot, paint):
    view = make(qtbot)
    assert view.text() == "🗋"
    assert view.pixmap().isNull()
    paint(view)


def test_bild_wird_eingepasst_und_behaelt_seitenverhaeltnis(qtbot, paint):
    view = make(qtbot)
    view.setPixmap(solid(1000, 1000))
    content = view._content_rect()
    assert view._scaled.width() == int(content.width())
    assert view._scaled.width() == view._scaled.height()
    # Die Mitte zeigt das Bild, nicht den Hintergrund.
    image = paint(view).toImage()
    assert image.pixelColor(150, 200) == QColor("red")


def test_bild_folgt_der_groesse(qtbot):
    view = make(qtbot)
    view.setPixmap(solid(1000, 500))
    view.resize(200, 400)
    assert view._scaled.width() == int(view._content_rect().width())


def test_clear_entfernt_bild_und_text(qtbot):
    view = make(qtbot)
    view.setPixmap(solid(10, 10))
    view.clear()
    assert view.pixmap().isNull()
    assert view.text() == ""


def test_klick_meldet_clicked(qtbot):
    view = make(qtbot)
    with qtbot.waitSignal(view.clicked, timeout=1000):
        qtbot.mouseClick(view, Qt.MouseButton.LeftButton, pos=QPoint(50, 50))


def test_rechtsklick_meldet_nichts(qtbot):
    view = make(qtbot)
    with qtbot.assertNotEmitted(view.clicked):
        qtbot.mouseClick(view, Qt.MouseButton.RightButton, pos=QPoint(50, 50))


def test_warte_animation_mit_und_ohne_bild(qtbot, paint):
    view = make(qtbot)
    view.setBusyIcon(solid(64, 64, "white"))

    view.start_busy()                       # ohne Bild: helle Fläche
    assert view.is_busy() and view._busy_timer.isActive()
    assert view._busy_background.isNull()
    paint(view)

    view.setPixmap(solid(400, 400))         # Bild kommt während des Wartens
    assert not view._busy_background.isNull()
    phase = view._busy_phase
    qtbot.waitUntil(lambda: view._busy_phase != phase, timeout=1000)
    paint(view)

    view.stop_busy()
    assert not view.is_busy() and not view._busy_timer.isActive()


def test_warte_animation_ohne_symbol(qtbot, paint):
    view = make(qtbot)
    view.setPixmap(solid(100, 100))
    view.start_busy()
    paint(view)
    view.stop_busy()


def test_rahmen_wird_unter_der_maus_hell(qtbot, paint):
    view = make(qtbot)
    view.HOVER_MS = 0
    view.bright = 1.0
    image = paint(view).toImage()
    # Der Rahmenstrich liegt ganz außen; hell heißt fast deckend.
    assert image.pixelColor(150, 0).alpha() > 200 or image.pixelColor(150, 0).lightness() > 200
