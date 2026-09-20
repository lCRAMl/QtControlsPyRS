import pytest
from PyQt6.QtCore import QPointF
from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QHBoxLayout, QWidget

from qt_controls_pyrs import ReferenceThumb


@pytest.fixture
def bilddatei(tmp_path):
    bild = QImage(80, 60, QImage.Format.Format_ARGB32)
    bild.fill(QColor("#3366cc"))
    pfad = tmp_path / "referenz.png"
    assert bild.save(str(pfad))
    return str(pfad)


def make(qtbot, api_key: str = "") -> ReferenceThumb:
    thumb = ReferenceThumb(2, api_key)
    qtbot.addWidget(thumb)
    thumb.show()
    qtbot.waitExposed(thumb)
    return thumb


def make_paar(qtbot) -> tuple[QWidget, ReferenceThumb, ReferenceThumb]:
    """Zwei Miniaturen nebeneinander, wie in einem Feld aus mehreren."""
    host = QWidget()
    layout = QHBoxLayout(host)
    erste, zweite = ReferenceThumb(0, ""), ReferenceThumb(1, "")
    layout.addWidget(erste)
    layout.addWidget(zweite)
    qtbot.addWidget(host)
    host.show()
    qtbot.waitExposed(host)
    return host, erste, zweite


def test_leerer_zustand(qtbot, paint):
    thumb = make(qtbot)

    assert thumb.upload_url is None
    assert not thumb.has_image()
    assert not thumb.overlay.isVisible()
    assert thumb.size().width() == ReferenceThumb.THUMB_SIZE
    paint(thumb)


def test_bild_setzen_zeigt_die_vorschau(qtbot, paint, bilddatei):
    thumb = make(qtbot)

    thumb.set_image(bilddatei)

    assert thumb.has_image()
    assert not thumb.pixmap().isNull()
    # Die Decke kommt erst, wenn die Maus darauf steht.
    assert not thumb.overlay.isVisible()
    paint(thumb)


def test_decke_kommt_nur_mit_bild(qtbot, paint, bilddatei):
    thumb = make(qtbot)

    thumb.pointer_entered()
    assert not thumb.overlay.isVisible(), "leer gibt es nichts wegzunehmen"

    thumb.set_image(bilddatei)
    thumb.pointer_entered()
    assert thumb.overlay.isVisible()
    paint(thumb)


def test_das_x_dreht_sich_aus(qtbot, bilddatei):
    thumb = make(qtbot)
    thumb.set_image(bilddatei)

    thumb.pointer_entered()
    knopf = thumb.overlay.button

    # Erst dreht es schnell, dann steht es still.
    qtbot.waitUntil(lambda: knopf.spin > 0.0, timeout=1000)
    qtbot.waitUntil(
        lambda: knopf.spin == 360.0 * knopf.SPIN_TURNS,
        timeout=3000,
    )


def test_licht_folgt_dem_zeiger(qtbot, paint):
    thumb = make(qtbot)
    vorher = thumb._light

    ecke = thumb.mapToGlobal(thumb.rect().topLeft())
    thumb.pointer_moved(QPointF(ecke))

    assert thumb._light != vorher
    qtbot.waitUntil(lambda: thumb.glow == 1.0, timeout=2000)
    paint(thumb)


def test_nachbarinnen_leuchten_mit(qtbot, paint):
    host, erste, zweite = make_paar(qtbot)

    mitte = erste.mapToGlobal(erste.rect().center())
    erste.pointer_moved(QPointF(mitte))

    # Beide bekommen dieselbe Stelle, jede in ihren eigenen Koordinaten.
    qtbot.waitUntil(lambda: erste.glow == 1.0 and zweite.glow == 1.0, timeout=2000)
    assert erste._light != zweite._light
    paint(erste)
    paint(zweite)

    erste.pointer_left()
    qtbot.waitUntil(lambda: erste.glow == 0.0 and zweite.glow == 0.0, timeout=2000)


def test_ohne_api_key_startet_kein_upload(qtbot, bilddatei):
    thumb = make(qtbot)

    thumb.set_image(bilddatei)

    assert thumb._worker is None, "Ohne Schluessel darf kein Upload starten"
    assert not thumb._uploading


def test_leeren_setzt_zurueck_und_meldet(qtbot, paint, bilddatei):
    thumb = make(qtbot)
    thumb.set_image(bilddatei)
    thumb.pointer_entered()

    with qtbot.waitSignal(thumb.cleared, timeout=1000) as signal:
        thumb.clear()

    assert signal.args == [2]
    assert thumb.upload_url is None
    assert not thumb.has_image()
    assert thumb.progress.width() == 0
    qtbot.waitUntil(lambda: not thumb.overlay.isVisible(), timeout=2000)
    paint(thumb)


def test_fortschritt_wird_begrenzt(qtbot):
    thumb = make(qtbot)

    thumb.set_progress(0.5)
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE // 2

    thumb.set_progress(2.0)
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE

    thumb.set_progress(-1.0)
    assert thumb.progress.width() == 0


def test_fehlgeschlagener_upload_meldet_und_zeigt_es(qtbot, paint):
    thumb = make(qtbot)

    with qtbot.waitSignal(thumb.upload_failed, timeout=1000) as signal:
        thumb._on_upload_failed("Netzwerk weg")

    assert signal.args == [2, "Netzwerk weg"]
    assert "failed" in thumb.message().lower()
    paint(thumb)


def test_erfolgreicher_upload_merkt_sich_die_url(qtbot):
    thumb = make(qtbot)

    with qtbot.waitSignal(thumb.uploaded, timeout=1000) as signal:
        thumb._on_upload_finished("https://i.ibb.co/abc/bild.png")

    assert signal.args == [2, "https://i.ibb.co/abc/bild.png"]
    assert thumb.upload_url == "https://i.ibb.co/abc/bild.png"
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE


def test_leuchtfarbe_ist_austauschbar(qtbot, paint):
    thumb = make(qtbot)

    assert thumb.glow_color() == QColor(ReferenceThumb.GLOW_COLOR)
    thumb.setGlowColor("#ff7a18")
    assert thumb.glow_color() == QColor("#ff7a18")

    thumb.glow = 1.0
    paint(thumb)


def test_karte_schrumpft_unter_der_maus(qtbot, paint):
    thumb = make(qtbot)

    ruhe = thumb._card_rect()
    thumb.hover = 1.0
    unter_maus = thumb._card_rect()

    assert unter_maus.width() < ruhe.width()
    assert unter_maus.center() == ruhe.center()
    paint(thumb)
