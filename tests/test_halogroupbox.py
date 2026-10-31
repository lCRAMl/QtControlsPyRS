from PyQt6.QtCore import QEvent, QPointF, Qt
from PyQt6.QtGui import QColor, QEnterEvent
from PyQt6.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from qt_controls_pyrs import HaloGroupBox


def make(qtbot, titel: str = "Platte und Sauger") -> HaloGroupBox:
    gruppe = HaloGroupBox(titel)
    layout = QVBoxLayout(gruppe)
    layout.addWidget(QLabel("Inhalt"))
    gruppe.resize(320, 140)
    qtbot.addWidget(gruppe)
    gruppe.show()
    qtbot.waitExposed(gruppe)
    return gruppe


# ----------------------------------------------------------------------
# QGroupBox bleibt QGroupBox
# ----------------------------------------------------------------------

def test_ist_eine_qgroupbox(qtbot, paint):
    gruppe = make(qtbot)

    assert isinstance(gruppe, QGroupBox)
    assert gruppe.title() == "Platte und Sauger"

    gruppe.setTitle("Vakuum und Sicherheit")
    assert gruppe.title() == "Vakuum und Sicherheit"
    paint(gruppe)


def test_abschaltbar_wie_gewohnt(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)

    # QGroupBox ist nach setCheckable(True) angehakt - das ist Qts Vorgabe
    # und bleibt so.
    assert gruppe.isCheckable()
    assert gruppe.isChecked()

    with qtbot.waitSignal(gruppe.toggled, timeout=1000) as signal:
        gruppe.setChecked(False)
    assert signal.args == [False]
    paint(gruppe)


def test_ein_layout_laesst_sich_hineinsetzen(qtbot):
    gruppe = make(qtbot)

    assert gruppe.layout() is not None
    assert gruppe.layout().count() == 1


# ----------------------------------------------------------------------
# Rahmen, Ueberschrift und Inhalt
# ----------------------------------------------------------------------

def _inhaltsrand(gruppe: HaloGroupBox):
    """Was den Inhalt tatsaechlich vom Rand fernhaelt.

    Entweder die Raender des Widgets oder die des Layouts - welche von beiden,
    entscheidet die Gruppe selbst (siehe _apply_margins). Geprueft wird hier
    das Ergebnis und nicht der Weg: an welchem Objekt die Zahl steht, ist eine
    Eigenheit von Qt und keine Zusage nach aussen.
    """
    layout = gruppe.layout()
    return layout.contentsMargins() if layout is not None else gruppe.contentsMargins()


def test_der_inhalt_liegt_im_rahmen_und_unter_der_ueberschrift(qtbot):
    gruppe = make(qtbot)
    raender = _inhaltsrand(gruppe)

    assert raender.left() == gruppe.PAD_X
    assert raender.right() == gruppe.PAD_X
    assert raender.bottom() == gruppe.PAD_BOTTOM
    assert raender.top() >= gruppe._title_height(), (
        "Der Inhalt muesste unterhalb der Ueberschrift beginnen"
    )


def test_das_erste_element_liegt_nicht_in_der_ueberschrift(qtbot):
    """Der Fehler, um den es geht - gemessen am Bildpunkt und nicht am Rand.

    make() setzt das Layout mit `QVBoxLayout(gruppe)`. Dieser Weg laeuft durch
    C++ und ruft setLayout() der Python-Seite nie; die Gruppe erfuhr also
    nichts von ihrem Layout und liess die Raender am Widget stehen. Solange
    kein Stylesheet mitredet, faellt das nicht auf.
    """
    gruppe = make(qtbot)
    inhalt = gruppe.layout().itemAt(0).widget()

    assert inhalt.y() >= gruppe._title_rect().bottom(), (
        "Das erste Element liegt in der Ueberschrift"
    )


def test_auch_mit_kastenangabe_im_stylesheet_bleibt_der_kopf_frei(qtbot):
    """Die Kastenangabe ist der eigentliche Gegner.

    `margin`, `padding`, auch mit Wert 0: jede davon uebersteuert
    setContentsMargins() des Widgets. Eine Anwendung braucht sie, um die
    Vorgaben eines mitgelieferten dunklen Stylesheets fuer QGroupBox zu
    loeschen - und loescht damit zugleich den Abstand, den die Gruppe fuer
    ihre Ueberschrift braucht. Genau diese Verkettung hat in TRXing jeden
    Rahmen getroffen.
    """
    gruppe = HaloGroupBox("Platte und Sauger")
    gruppe.setStyleSheet("HaloGroupBox { margin-top: 0px; border: none; }")
    layout = QVBoxLayout(gruppe)
    layout.addWidget(QLabel("Inhalt"))
    gruppe.resize(320, 140)
    qtbot.addWidget(gruppe)
    gruppe.show()
    qtbot.waitExposed(gruppe)

    inhalt = layout.itemAt(0).widget()
    assert inhalt.y() >= gruppe._title_rect().bottom(), (
        "Eine Kastenangabe im Stylesheet darf die Ueberschrift nicht zudecken"
    )


def test_die_raender_zaehlen_nicht_doppelt(qtbot):
    """Widget UND Layout haetten beide Raender - der Inhalt sass doppelt tief.

    Zu sehen war das nur ohne Stylesheet, weil eine Kastenangabe die
    Widget-Raender ohnehin loescht. Zwei Fassungen derselben Anwendung saehen
    damit verschieden aus, ohne dass im Quelltext ein Unterschied steht.
    """
    gruppe = make(qtbot)
    widget_rand = gruppe.contentsMargins()

    assert widget_rand.top() == 0 and widget_rand.left() == 0, (
        "Traegt das Layout die Raender, muessen die des Widgets Null sein"
    )


def test_eine_laengere_ueberschrift_macht_mehr_platz(qtbot):
    gruppe = make(qtbot, "Kurz")
    schmal = gruppe._title_rect().width()

    gruppe.setTitle("Eine deutlich laengere Ueberschrift")
    assert gruppe._title_rect().width() > schmal


def test_das_kaestchen_steht_links_vor_der_ueberschrift(qtbot, paint):
    gruppe = make(qtbot)
    ohne = gruppe._title_rect().left()

    gruppe.setCheckable(True)
    mit = gruppe._title_rect().left()
    assert mit > ohne, "Die Ueberschrift muesste dem Kaestchen Platz machen"
    assert gruppe._box_rect().right() <= mit
    paint(gruppe)


def test_ohne_kaestchen_gibt_es_kein_kaestchen(qtbot):
    gruppe = make(qtbot)

    assert not gruppe.isCheckable()
    assert gruppe._box_rect().isEmpty()


def test_der_kopfbereich_schaltet_um_wie_bei_jeder_qgroupbox(qtbot):
    """Gezeichnet wird eigens, geklickt nicht - sonst waere es kein Vorbild mehr."""
    gruppe = make(qtbot)
    gruppe.setCheckable(True)
    gruppe.setChecked(False)

    qtbot.mouseClick(gruppe, Qt.MouseButton.LeftButton,
                     pos=gruppe._box_rect().center().toPoint())
    assert gruppe.isChecked()

    qtbot.mouseClick(gruppe, Qt.MouseButton.LeftButton,
                     pos=gruppe._title_rect().center().toPoint())
    assert not gruppe.isChecked()


def test_unter_der_maus_glimmt_der_rahmen_auf(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.hover = 0.0

    point = QPointF(gruppe.rect().center())
    gruppe.enterEvent(QEnterEvent(point, point, point))
    qtbot.waitUntil(lambda: gruppe.hover == 1.0, timeout=3000)
    paint(gruppe)

    gruppe.leaveEvent(QEvent(QEvent.Type.Leave))
    qtbot.waitUntil(lambda: gruppe.hover == 0.0, timeout=3000)


def test_das_kaestchen_fuellt_sich_statt_zu_springen(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)      # damit schon angehakt, siehe oben
    gruppe.setChecked(False)
    qtbot.waitUntil(lambda: gruppe.position == 0.0, timeout=2000)

    gruppe.setChecked(True)
    qtbot.wait(60)
    assert 0.0 < gruppe.position < 1.0
    paint(gruppe)
    qtbot.waitUntil(lambda: gruppe.position == 1.0, timeout=2000)


def test_die_signalfarbe_laesst_sich_setzen(qtbot, paint):
    gruppe = make(qtbot)
    gruppe.setCheckable(True)
    gruppe.setChecked(True)

    gruppe.setAccentColor(QColor("#ff8c00"))
    assert gruppe.accent_color() == QColor("#ff8c00")
    paint(gruppe)


def test_ohne_ueberschrift_laeuft_der_strich_durch(qtbot, paint):
    gruppe = make(qtbot, "")

    assert gruppe.title() == ""
    assert gruppe._title_rect().width() == 0
    paint(gruppe)


def test_gesperrt_wird_blass_gezeichnet(qtbot, paint):
    gruppe = make(qtbot)

    gruppe.setEnabled(False)
    qtbot.waitUntil(lambda: gruppe.hover == 0.0, timeout=3000)
    paint(gruppe)
