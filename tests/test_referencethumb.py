import pytest
from PyQt6.QtGui import QColor, QImage

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


def test_leerer_zustand(qtbot):
    thumb = make(qtbot)

    assert thumb.upload_url is None
    assert not thumb.close_btn.isVisible()
    assert thumb.size().width() == ReferenceThumb.THUMB_SIZE


def test_bild_setzen_zeigt_vorschau_und_schliessknopf(qtbot, bilddatei):
    thumb = make(qtbot)

    thumb.set_image(bilddatei)

    assert not thumb.image.pixmap().isNull()
    assert thumb.close_btn.isVisible()


def test_ohne_api_key_startet_kein_upload(qtbot, bilddatei):
    thumb = make(qtbot)

    thumb.set_image(bilddatei)

    assert thumb._worker is None, "Ohne Schluessel darf kein Upload starten"
    assert not thumb._uploading


def test_leeren_setzt_zurueck_und_meldet(qtbot, bilddatei):
    thumb = make(qtbot)
    thumb.set_image(bilddatei)

    with qtbot.waitSignal(thumb.cleared, timeout=1000) as signal:
        thumb.clear()

    assert signal.args == [2]
    assert thumb.upload_url is None
    assert not thumb.close_btn.isVisible()
    assert thumb.progress.width() == 0


def test_fortschritt_wird_begrenzt(qtbot):
    thumb = make(qtbot)

    thumb.set_progress(0.5)
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE // 2

    thumb.set_progress(2.0)
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE

    thumb.set_progress(-1.0)
    assert thumb.progress.width() == 0


def test_fehlgeschlagener_upload_meldet_und_zeigt_es(qtbot):
    thumb = make(qtbot)

    with qtbot.waitSignal(thumb.upload_failed, timeout=1000) as signal:
        thumb._on_upload_failed("Netzwerk weg")

    assert signal.args == [2, "Netzwerk weg"]
    assert "failed" in thumb.image.text().lower()


def test_erfolgreicher_upload_merkt_sich_die_url(qtbot):
    thumb = make(qtbot)

    with qtbot.waitSignal(thumb.uploaded, timeout=1000) as signal:
        thumb._on_upload_finished("https://i.ibb.co/abc/bild.png")

    assert signal.args == [2, "https://i.ibb.co/abc/bild.png"]
    assert thumb.upload_url == "https://i.ibb.co/abc/bild.png"
    assert thumb.progress.width() == ReferenceThumb.THUMB_SIZE
