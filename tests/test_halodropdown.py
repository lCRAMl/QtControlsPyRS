from PyQt6.QtCore import QPoint, QPointF, QRectF, Qt
from PyQt6.QtWidgets import QComboBox

from qt_controls_pyrs import HaloDropdown

ITEMS = ["Portraits", "Landschaft", "Produkte", "Architektur", "Tiere"]


def make(qtbot, items=ITEMS, cls=HaloDropdown) -> HaloDropdown:
    box = cls()
    box.addItems(items)
    box.resize(box.sizeHint().width() + 60, box.sizeHint().height())
    qtbot.addWidget(box)
    box.show()
    qtbot.waitExposed(box)
    return box


def open_fully(qtbot, box: HaloDropdown) -> None:
    box.showPopup()
    qtbot.waitUntil(lambda: box.popup().settled(), timeout=3000)


class Sortiert(HaloDropdown):
    SORTED = True


# ----------------------------------------------------------------------
# QComboBox bleibt QComboBox
# ----------------------------------------------------------------------

def test_ist_eine_qcombobox(qtbot, paint):
    box = make(qtbot)

    assert isinstance(box, QComboBox)
    assert box.count() == 5
    assert box.currentText() == "Portraits"

    box.setCurrentIndex(2)
    assert box.currentText() == "Produkte"
    paint(box)


def test_platzhalter_steht_gedimmt_in_der_leiste(qtbot, paint):
    box = make(qtbot)
    box.setPlaceholderText("WÄHLE EINEN ORDNER")
    box.setCurrentIndex(-1)

    assert box.currentIndex() == -1
    assert box._display() == ("WÄHLE EINEN ORDNER", True)
    paint(box)


# ----------------------------------------------------------------------
# Aufklappen: das Feld rollt auf, die Einträge gleiten nach
# ----------------------------------------------------------------------


def test_klick_klappt_auf_und_der_pfeil_dreht(qtbot, paint):
    box = make(qtbot)
    assert not box.is_open()

    open_fully(qtbot, box)
    assert box.is_open()
    assert box.popup().isVisible()
    qtbot.waitUntil(lambda: box.arrow == 1.0, timeout=1000)
    paint(box)
    paint(box.popup())


def test_aufrollen_das_feld_waechst_von_der_leiste_aus(qtbot, paint):
    box = make(qtbot)
    box.showPopup()
    popup = box.popup()
    popup._open_anim.stop()

    popup.clock = 0.0
    assert popup.field_rect().height() == 0.0

    popup.clock = HaloDropdown.UNFOLD_MS / 3
    teil = popup.field_rect()
    assert 0.0 < teil.height() < popup._list.height()
    # Nach unten aufgeklappt: die Oberkante bleibt an der Leiste.
    assert teil.top() == popup._list.top()
    paint(popup)

    popup.clock = float(HaloDropdown.UNFOLD_MS)
    assert popup.field_rect() == popup._list


def test_aufrollen_eintraege_folgen_der_kante(qtbot):
    box = make(qtbot)
    box.showPopup()
    popup = box.popup()
    popup._open_anim.stop()

    popup.clock = HaloDropdown.UNFOLD_MS / 2
    # Der obere ist schon weiter als der untere, und der unterste hat
    # vielleicht noch gar nicht angefangen.
    fortschritt = [popup.item_progress(i) for i in range(5)]
    assert fortschritt == sorted(fortschritt, reverse=True)
    assert fortschritt[0] > fortschritt[4]


def test_aufrollen_dauert_bei_langen_listen_kaum_laenger(qtbot):
    kurz = make(qtbot, items=[f"Ordner {i}" for i in range(5)])
    lang = make(qtbot, items=[f"Ordner {i}" for i in range(10)])
    lang.setMaxVisibleItems(10)

    kurz.showPopup()
    lang.showPopup()
    dauer_kurz = kurz.popup()._open_anim.duration()
    dauer_lang = lang.popup()._open_anim.duration()

    # Der Versatz ergibt sich aus der Kante, nicht aus einer Wartezeit je Eintrag.
    assert dauer_lang - dauer_kurz < 50
    assert dauer_lang <= HaloDropdown.UNFOLD_MS + HaloDropdown.ITEM_MS


def test_eintraege_gleiten_nur_ein_paar_pixel(qtbot, paint):
    """Nichts wird skaliert — ein Eintrag verschiebt sich nur um SLIDE."""
    box = make(qtbot)
    box.showPopup()
    popup = box.popup()
    popup._open_anim.stop()
    for clock in (0.0, 40.0, 90.0, 150.0, 400.0):
        popup.clock = clock
        paint(popup)


# ----------------------------------------------------------------------
# Wählen und Zuklappen
# ----------------------------------------------------------------------

def test_eintrag_mit_der_maus_waehlen(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()

    ziel = QRectF(
        popup._list.left(), popup._row_top(3), popup._list.width(), HaloDropdown.ITEM_HEIGHT
    ).center().toPoint()
    assert popup.index_at(QPointF(ziel)) == 3

    with qtbot.waitSignals([box.currentIndexChanged, box.activated], timeout=1000):
        qtbot.mouseClick(popup, Qt.MouseButton.LeftButton, pos=ziel)

    assert box.currentText() == "Architektur"
    qtbot.waitUntil(lambda: not popup.isVisible(), timeout=2000)


def test_wahl_leuchtet_auf_und_dann_klappt_es_zu(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()

    box._choose(2)
    # Erst leuchtet der Eintrag, das Zuklappen wartet solange.
    assert not box.is_open()
    qtbot.waitUntil(lambda: popup.confirm > 0.0, timeout=1000)
    assert popup.isVisible()
    qtbot.waitUntil(lambda: not popup.isVisible(), timeout=2000)
    assert box.currentText() == "Produkte"


def test_zuklappen_als_ganzes_und_schnell(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()

    box.hidePopup()
    assert not box.is_open()
    assert popup._close_anim.duration() == HaloDropdown.CLOSE_MS
    qtbot.waitUntil(lambda: not popup.isVisible(), timeout=2000)
    qtbot.waitUntil(lambda: box.arrow == 0.0, timeout=1000)


def test_klick_daneben_klappt_nur_zu(qtbot):
    box = make(qtbot)
    box.setCurrentIndex(1)
    open_fully(qtbot, box)
    popup = box.popup()

    daneben = QPoint(2, int(popup._list.center().y()))
    assert popup.index_at(QPointF(daneben)) == -1
    qtbot.mouseClick(popup, Qt.MouseButton.LeftButton, pos=daneben)

    assert not box.is_open()
    assert box.currentText() == "Landschaft"


def test_tastatur_waehlt_aus(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()

    qtbot.keyClick(popup, Qt.Key.Key_Down)
    qtbot.keyClick(popup, Qt.Key.Key_Down)
    with qtbot.waitSignal(box.activated, timeout=1000):
        qtbot.keyClick(popup, Qt.Key.Key_Return)

    assert box.currentText() == "Produkte"


def test_escape_schliesst_ohne_zu_aendern(qtbot):
    box = make(qtbot)
    box.setCurrentIndex(1)
    open_fully(qtbot, box)
    popup = box.popup()

    qtbot.keyClick(popup, Qt.Key.Key_Down)
    qtbot.keyClick(popup, Qt.Key.Key_Escape)

    assert box.currentText() == "Landschaft"
    qtbot.waitUntil(lambda: not popup.isVisible(), timeout=2000)


def test_leeres_feld_klappt_nicht_auf(qtbot):
    box = make(qtbot, items=[])

    box.showPopup()
    assert not box.is_open()


def test_gesperrt_klappt_zu_und_nicht_mehr_auf(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)

    box.setEnabled(False)
    assert not box.is_open()

    box.showPopup()
    assert not box.is_open()


# ----------------------------------------------------------------------
# Feinschliff: Markierung, Rollen, Leistentext
# ----------------------------------------------------------------------

def test_markierung_gleitet(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()
    assert popup.glide == 0.0

    qtbot.keyClick(popup, Qt.Key.Key_Down)
    qtbot.keyClick(popup, Qt.Key.Key_Down)
    # Die Markierung ist unterwegs, nicht sofort da ...
    assert popup._hot == 2
    assert popup.glide < 2.0
    # ... und kommt an.
    qtbot.waitUntil(lambda: popup.glide == 2.0, timeout=1000)


def test_lange_liste_rollt_weich(qtbot, paint):
    box = make(qtbot, items=[f"Ordner {i:02d}" for i in range(30)])
    box.setMaxVisibleItems(8)
    open_fully(qtbot, box)
    popup = box.popup()
    rows = popup._rows
    assert 1 <= rows <= 8

    qtbot.keyClick(popup, Qt.Key.Key_End)
    assert popup._hot == 29
    assert popup._scroll_target == 30 - rows
    # Gerollt wird fliessend, nicht in einem Satz.
    assert popup.scroll < popup._scroll_target
    qtbot.waitUntil(lambda: popup.scroll == popup._scroll_target, timeout=1000)
    paint(popup)


def test_leistentext_blendet_ueber(qtbot, paint):
    box = make(qtbot)
    qtbot.wait(300)
    assert box.swap == 1.0

    box.setCurrentIndex(3)
    assert box.swap < 1.0
    assert box._old_text == "Portraits"
    paint(box)
    qtbot.waitUntil(lambda: box.swap == 1.0, timeout=1000)


# ----------------------------------------------------------------------
# Buchstaben und Sortierung
# ----------------------------------------------------------------------

def test_buchstabe_springt_in_der_offenen_liste(qtbot):
    box = make(qtbot)
    open_fully(qtbot, box)
    popup = box.popup()

    qtbot.keyClick(popup, Qt.Key.Key_T, delay=0)
    assert popup._hot == 4           # "Tiere"
    qtbot.wait(500)                  # neue Eingabe, nicht "ta"
    qtbot.keyClick(popup, Qt.Key.Key_A)
    assert popup._hot == 3           # "Architektur"


def test_gleicher_buchstabe_wiederholt_springt_weiter(qtbot):
    box = make(qtbot, items=["Sand", "Schatten", "Tal", "Sonne"])

    erste = box.find_typed("s", -1)
    zweite = box.find_typed("s", erste)
    dritte = box.find_typed("s", zweite)
    assert [box.itemText(i) for i in (erste, zweite, dritte)] == ["Sand", "Schatten", "Sonne"]


def test_schnell_getippt_zaehlt_der_ganze_anfang(qtbot):
    box = make(qtbot, items=["Sand", "Schatten", "Sonne"])

    erste = box.find_typed("s", -1)
    assert box.itemText(erste) == "Sand"
    zweite = box.find_typed("c", erste)
    assert box.itemText(zweite) == "Schatten"


def test_umlaute_und_gross_klein_zaehlen_nicht(qtbot):
    box = make(qtbot, items=["Berge", "Äpfel", "Zoo"])

    assert box.itemText(box.find_typed("a", -1)) == "Äpfel"


def test_geschlossen_waehlt_ein_buchstabe_direkt(qtbot):
    box = make(qtbot)

    with qtbot.waitSignal(box.activated, timeout=1000):
        qtbot.keyClick(box, Qt.Key.Key_T)
    assert box.currentText() == "Tiere"


def test_sortiert_deutsch_und_natuerlich(qtbot):
    box = make(qtbot, cls=Sortiert, items=["ordner 10", "Zoo", "Äpfel", "ordner 2", "Berge"])

    assert [box.itemText(i) for i in range(box.count())] == [
        "Äpfel", "Berge", "ordner 2", "ordner 10", "Zoo",
    ]


def test_sortieren_behaelt_die_auswahl_und_den_platzhalter(qtbot):
    box = make(qtbot, cls=Sortiert, items=[])
    box.setPlaceholderText("WÄHLE EINEN ORDNER")
    for name in ["Tiere", "Architektur", "Portraits"]:
        box.addItem(name)
    box.setCurrentIndex(-1)

    assert box.currentIndex() == -1
    assert box.itemText(0) == "Architektur"

    box.setCurrentText("Portraits")
    box.addItem("Berge")
    assert box.currentText() == "Portraits"


def test_ohne_sorted_bleibt_die_reihenfolge(qtbot):
    box = make(qtbot, items=["Zoo", "Äpfel", "Berge"])

    assert [box.itemText(i) for i in range(box.count())] == ["Zoo", "Äpfel", "Berge"]


# ----------------------------------------------------------------------
# flash()
# ----------------------------------------------------------------------

def test_flash_blinkt_und_hoert_wieder_auf(qtbot, paint):
    box = make(qtbot)

    box.flash()
    qtbot.waitUntil(lambda: box.flash_level > 0.5, timeout=1000)
    paint(box)
    qtbot.waitUntil(
        lambda: box._flash_anim.state() != box._flash_anim.State.Running, timeout=2000
    )
    assert box.flash_level == 0.0


def test_flash_ist_auch_gesperrt_zu_sehen(qtbot, paint):
    box = make(qtbot)
    box.setEnabled(False)

    box.flash(count=1)
    qtbot.waitUntil(lambda: box.flash_level > 0.5, timeout=1000)
    paint(box)


# ----------------------------------------------------------------------
# Aussehen
# ----------------------------------------------------------------------

def test_platz_fuer_breitesten_eintrag_und_den_rand(qtbot):
    kurz = make(qtbot, items=["A"])
    lang = make(qtbot, items=["Ein deutlich laengerer Eintrag"])

    assert lang.sizeHint().width() > kurz.sizeHint().width()
    assert kurz.sizeHint().height() == HaloDropdown.HEIGHT + 2 * HaloDropdown.ROOM_Y

    flaeche = kurz._surface()
    assert flaeche.left() == HaloDropdown.ROOM
    assert kurz.width() - flaeche.right() == HaloDropdown.ROOM


def test_abgerundete_ecken(qtbot, paint):
    class Rund(HaloDropdown):
        RADIUS = 10

    box = make(qtbot, cls=Rund)
    box.hover = 1.0
    paint(box)
    open_fully(qtbot, box)
    paint(box.popup())
