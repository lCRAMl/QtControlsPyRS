from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPixmap
from PyQt6.QtWidgets import QMenu, QVBoxLayout, QWidget

from qt_controls_pyrs import HaloCommandBar, HaloToolButton, tinted_pixmap


def schwarzes_symbol() -> QIcon:
    """Einfarbiges Symbol wie ein schwarz gezeichnetes SVG: Quadrat auf Durchsichtig."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.fillRect(8, 8, 16, 16, QColor("black"))
    painter.end()
    return QIcon(pixmap)


def aktion(text: str, parent, icon: bool = True, **kwargs) -> QAction:
    action = QAction(schwarzes_symbol() if icon else QIcon(), text, parent)
    for key, value in kwargs.items():
        getattr(action, "set" + key[0].upper() + key[1:])(value)
    return action


def fenster(qtbot, breite: int = 1200):
    window = QWidget()
    window.resize(breite, 200)
    layout = QVBoxLayout(window)
    bar = HaloCommandBar()
    layout.addWidget(bar)
    layout.addStretch(1)
    qtbot.addWidget(window)
    return window, bar


def zeigen(qtbot, window, bar):
    window.show()
    qtbot.waitExposed(window)
    qtbot.wait(20)        # die Dichte wird nach dem Layoutlauf angepasst


# ==============================
# Knopf und Aktion
# ==============================

def test_knopf_folgt_der_aktion(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    action = aktion("&Speichern", host, checkable=True)
    button = HaloToolButton(action, "large", host)

    assert button._label() == "Speichern"
    action.setEnabled(False)
    assert not button.isEnabled()
    action.setEnabled(True)
    action.setChecked(True)
    assert button.isChecked()

    ausgeloest = []
    action.triggered.connect(lambda: ausgeloest.append(True))
    button.click()
    assert ausgeloest


def test_tooltip_nennt_kurzbefehl_und_statustext(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    action = aktion("Speichern", host, shortcut=QKeySequence("Ctrl+S"),
                    statusTip="Projekt sichern")
    button = HaloToolButton(action, "small", host)

    tip = button.toolTip()
    assert "Speichern" in tip
    assert QKeySequence("Ctrl+S").toString(QKeySequence.SequenceFormat.NativeText) in tip
    assert "Projekt sichern" in tip

    action.setShortcut(QKeySequence("Ctrl+Shift+S"))
    assert "Shift" in button.toolTip()


def test_knopf_nimmt_keinen_fokus(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    button = HaloToolButton(aktion("Öffnen", host), "large", host)
    assert button.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_menue_oeffnet_sofort_und_braucht_platz_fuer_den_pfeil(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    ohne = HaloToolButton(aktion("Drehen", host), "large", host)
    action = aktion("Drehen", host)
    menu = QMenu(host)
    menu.addAction("90°")
    action.setMenu(menu)
    mit = HaloToolButton(action, "large", host)

    assert mit.popupMode() == HaloToolButton.ToolButtonPopupMode.InstantPopup
    assert mit.sizeHint().width() > ohne.sizeHint().width()


def test_neue_beschriftung_aendert_die_breite(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    action = aktion("Kurz", host)
    button = HaloToolButton(action, "small", host)
    vorher = button.sizeHint().width()
    action.setText("Eine deutlich längere Beschriftung")
    assert button.sizeHint().width() > vorher


def test_ohne_symbol_bleibt_die_schrift(qtbot):
    host = QWidget()
    qtbot.addWidget(host)
    button = HaloToolButton(aktion("Nur Text", host, icon=False), "large", host)
    button.set_text_visible(False)
    assert button.text_visible()


def test_unbekannte_groesse_wird_abgelehnt(qtbot):
    import pytest
    host = QWidget()
    qtbot.addWidget(host)
    with pytest.raises(ValueError):
        HaloToolButton(aktion("x", host), "huge", host)


# ==============================
# Gruppe und Leiste
# ==============================

def test_kleine_knoepfe_stapeln_sich_zu_zweit(qtbot):
    window, bar = fenster(qtbot)
    group = bar.add_group("Datei")
    for name in ("Neu", "Öffnen", "Speichern"):
        group.add_action(aktion(name, window), "small")
    group.add_action(aktion("Export", window))     # groß, eigene Spalte

    spalten = [len(column) for column in group._columns]
    assert spalten == [2, 1, 1]


def test_trennstriche_nur_zwischen_sichtbaren_gruppen(qtbot):
    window, bar = fenster(qtbot)
    a = bar.add_group("A")
    a.add_action(aktion("Eins", window))
    b = bar.add_group("B")
    b.add_action(aktion("Zwei", window))
    bar.add_stretch()
    c = bar.add_group("C")
    c.add_action(aktion("Drei", window))
    zeigen(qtbot, window, bar)

    # Über den Stretch hinweg steht kein Strich.
    assert len(bar.separator_positions()) == 1
    x = bar.separator_positions()[0]
    assert a.geometry().right() < x < b.geometry().left()

    b.hide()
    qtbot.wait(20)
    assert bar.separator_positions() == []
    b.show()
    qtbot.wait(20)
    assert len(bar.separator_positions()) == 1


def test_schmales_fenster_erhoeht_die_dichte_ohne_hoehe_zu_aendern(qtbot):
    window, bar = fenster(qtbot, breite=1400)
    group = bar.add_group("Bearbeiten mit langer Überschrift")
    for name in ("Rückgängig", "Wiederholen", "Ausschneiden", "Kopieren"):
        group.add_action(aktion(name, window), "small")
    for name in ("Paket hinzufügen", "Muster drehen", "Muster prüfen"):
        group.add_action(aktion(name, window))
    zeigen(qtbot, window, bar)
    assert bar.density() == 0
    hoehe = bar.height()

    window.resize(bar.width_for(1) + 30, 200)
    qtbot.waitUntil(lambda: bar.density() == 1, timeout=1000)
    klein = [b for b in group.buttons() if b.size_kind() == "small"]
    gross = [b for b in group.buttons() if b.size_kind() == "large"]
    assert not any(b.text_visible() for b in klein)
    assert all(b.text_visible() for b in gross)

    window.resize(bar.width_for(2) + 30, 200)
    qtbot.waitUntil(lambda: bar.density() == 2, timeout=1000)
    assert not any(b.text_visible() for b in gross)
    assert bar.height() == hoehe

    window.resize(1400, 200)
    qtbot.waitUntil(lambda: bar.density() == 0, timeout=1000)
    assert all(b.text_visible() for b in group.buttons())


def test_leiste_haelt_das_fenster_nicht_breit(qtbot):
    window, bar = fenster(qtbot)
    group = bar.add_group("Viele")
    for index in range(12):
        group.add_action(aktion(f"Befehl Nummer {index}", window))
    zeigen(qtbot, window, bar)
    assert bar.minimumSizeHint().width() < bar.sizeHint().width()


# ==============================
# Symbole und Zeichnen
# ==============================

def test_eingefaerbtes_symbol_behaelt_die_form(qtbot):
    pixmap = tinted_pixmap(schwarzes_symbol(), 32, QColor("#5a8cff"), 1.0)
    image = pixmap.toImage()
    innen = image.pixelColor(16, 16)
    aussen = image.pixelColor(2, 2)
    assert innen.name() == "#5a8cff" and innen.alpha() == 255
    assert aussen.alpha() == 0


def test_alle_zustaende_zeichnen(qtbot, paint):
    window, bar = fenster(qtbot)
    group = bar.add_group("Alles")
    menu = QMenu(window)
    menu.addAction("90°")
    mit_menue = aktion("Drehen", window)
    mit_menue.setMenu(menu)
    buttons = [
        group.add_action(aktion("Groß", window, checkable=True, checked=True)),
        group.add_action(mit_menue),
        group.add_action(aktion("Klein", window), "small"),
        group.add_action(aktion("Nur Text", window, icon=False), "small"),
        group.add_action(aktion("Gesperrt", window, enabled=False), "small"),
    ]
    zeigen(qtbot, window, bar)

    for button in buttons:
        button.hover = 1.0
        paint(button)
        button.set_text_visible(False)
        paint(button)
        button.setDown(True)
        paint(button)
    paint(bar)
