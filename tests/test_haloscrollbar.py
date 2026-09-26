from PyQt6.QtCore import QPointF, QSize, Qt
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtWidgets import QScrollBar

from qt_controls_pyrs import HaloScrollBar


def make(qtbot, maximum: int = 500) -> HaloScrollBar:
    bar = HaloScrollBar()
    bar.setMinimum(0)
    bar.setMaximum(maximum)
    bar.setPageStep(100)
    bar.resize(bar.sizeHint().width(), 300)
    qtbot.addWidget(bar)
    bar.show()
    qtbot.waitExposed(bar)
    return bar


def press(bar: HaloScrollBar, y: float) -> None:
    point = QPointF(bar.width() / 2, y)
    bar.mousePressEvent(QMouseEvent(
        QMouseEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    ))


def move(bar: HaloScrollBar, y: float) -> None:
    point = QPointF(bar.width() / 2, y)
    bar.mouseMoveEvent(QMouseEvent(
        QMouseEvent.Type.MouseMove, point, Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    ))


def release(bar: HaloScrollBar) -> None:
    point = QPointF(bar.width() / 2, 0.0)
    bar.mouseReleaseEvent(QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease, point, Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
    ))


def test_ist_eine_qscrollbar(qtbot, paint):
    bar = make(qtbot)

    assert isinstance(bar, QScrollBar)
    assert bar.sizeHint().width() == HaloScrollBar.THICKNESS

    with qtbot.waitSignal(bar.valueChanged, timeout=1000) as signal:
        bar.setValue(250)
    assert signal.args == [250]
    paint(bar)


def test_das_band_wandert_mit_dem_wert(qtbot):
    bar = make(qtbot)
    anfang, laenge = bar._track_span()

    oben_bei_null, band = bar._thumb_span()
    assert oben_bei_null == anfang
    assert band >= HaloScrollBar.MIN_THUMB

    bar.setValue(bar.maximum())
    oben_am_ende, _ = bar._thumb_span()
    assert oben_am_ende + band == anfang + laenge, "ganz unten schließt es mit der Schiene ab"

    bar.setValue(bar.maximum() // 2)
    oben_mitte, _ = bar._thumb_span()
    assert oben_bei_null < oben_mitte < oben_am_ende


def test_kurze_inhalte_bekommen_ein_langes_band(qtbot):
    bar = make(qtbot)
    _, schiene = bar._track_span()

    bar.setPageStep(10_000)        # fast alles ist zu sehen
    _, band = bar._thumb_span()
    assert band > schiene * 0.9, "wenig zu scrollen, also füllt das Band die Schiene fast"
    assert band <= schiene


def test_scrollen_bringt_bewegung_und_beruhigt_sich_wieder(qtbot, paint):
    bar = make(qtbot)
    assert bar.activity() == 0.0
    assert not bar._timer.isActive()

    bar.setValue(200)
    assert bar.activity() > 0.5, "zwei Seiten weiter ist volle Bewegung"
    assert bar._timer.isActive(), "der Bildtakt läuft"
    paint(bar)

    # Weiterscrollen hält die Bewegung oben.
    for wert in range(200, 480, 20):
        bar.setValue(wert)
        qtbot.wait(20)
    assert bar.activity() > 0.5
    paint(bar)

    # Danach läuft sie aus, und der Bildtakt bleibt stehen.
    qtbot.waitUntil(lambda: not bar._timer.isActive(), timeout=4000)
    assert bar.activity() <= 0.01
    paint(bar)


def test_waagerecht_laeuft_alles_gespiegelt(qtbot, paint):
    bar = HaloScrollBar()
    bar.setOrientation(Qt.Orientation.Horizontal)
    bar.setMaximum(500)
    bar.setPageStep(100)
    bar.resize(300, bar.sizeHint().height())
    qtbot.addWidget(bar)
    bar.show()
    qtbot.waitExposed(bar)

    assert not bar.is_vertical()
    assert bar.sizeHint() == QSize(120, HaloScrollBar.THICKNESS)
    # Gemessen wird jetzt die Breite, nicht die Höhe.
    _, laenge = bar._track_span()
    assert laenge == bar.width() - 2 * HaloScrollBar.PADDING
    paint(bar)

    # Ziehen geht nach rechts statt nach unten.
    oben, band = bar._thumb_span()
    point = QPointF(oben + band / 2, bar.height() / 2)
    bar.mousePressEvent(QMouseEvent(
        QMouseEvent.Type.MouseButtonPress, point, Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    ))
    assert bar._dragging
    bar.mouseMoveEvent(QMouseEvent(
        QMouseEvent.Type.MouseMove, QPointF(point.x() + 60, point.y()),
        Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
    ))
    assert bar.value() > 0
    paint(bar)


def test_ziehen_am_band(qtbot):
    bar = make(qtbot)
    oben, laenge = bar._thumb_span()

    press(bar, oben + laenge / 2)
    assert bar._dragging
    move(bar, oben + laenge / 2 + 50)
    assert bar.value() > 0
    release(bar)
    assert not bar._dragging


def test_klick_neben_das_band_springt_dorthin(qtbot):
    bar = make(qtbot)
    _, laenge = bar._thumb_span()

    press(bar, bar.height() - HaloScrollBar.PADDING - laenge / 2)
    release(bar)
    assert bar.value() == bar.maximum()


def test_ohne_inhalt_zum_scrollen_bleibt_es_leer(qtbot, paint):
    bar = make(qtbot, maximum=0)

    assert bar.maximum() == bar.minimum()
    paint(bar)      # nur der Hintergrund, kein Band
