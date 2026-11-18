from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout

from qt_controls_pyrs import HaloDialog, HaloMessageBox


def test_dialog_ohne_windows_rahmen_mit_titel(qtbot, paint):
    dialog = HaloDialog("Optionen")
    QVBoxLayout(dialog.body).addWidget(QLabel("Inhalt"))
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert dialog.title() == "Optionen" and dialog.windowTitle() == "Optionen"
    assert isinstance(dialog, QDialog)
    paint(dialog)


def test_titelleiste_verschiebt_den_dialog(qtbot):
    dialog = HaloDialog("Ziehen")
    dialog.resize(300, 200)
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    before = dialog.pos()
    bar = dialog.title_bar
    qtbot.mousePress(bar, Qt.MouseButton.LeftButton, pos=QPoint(40, 10))
    qtbot.mouseMove(bar, pos=QPoint(90, 40))
    qtbot.mouseRelease(bar, Qt.MouseButton.LeftButton, pos=QPoint(90, 40))
    assert dialog.pos() != before


def test_schliessknopf_und_escape_brechen_ab(qtbot):
    for close in ("x", "esc"):
        box = HaloMessageBox("Frage", "Wirklich?", buttons=(("yes", "Ja"), ("no", "Nein")))
        qtbot.addWidget(box)
        box.show()
        qtbot.waitExposed(box)
        if close == "x":
            box.title_bar.close_button.click()
        else:
            qtbot.keyClick(box, Qt.Key.Key_Escape)
        assert box.result() == QDialog.DialogCode.Rejected
        assert box.clicked() is None


def test_knopf_liefert_seinen_schluessel(qtbot):
    box = HaloMessageBox("Löschen", "Muster 7 löschen?", kind="warning",
                         buttons=(("yes", "Löschen"), ("cancel", "Abbrechen")), default="cancel")
    qtbot.addWidget(box)
    box.show()
    assert box.buttons["cancel"].isDefault() and not box.buttons["yes"].isDefault()
    box.buttons["yes"].click()
    assert box.clicked() == "yes" and box.result() == QDialog.DialogCode.Accepted


def test_enter_waehlt_den_standardknopf(qtbot):
    box = HaloMessageBox("Speichern", "Änderungen speichern?",
                         buttons=(("save", "Speichern"), ("discard", "Verwerfen")), default="save")
    qtbot.addWidget(box)
    box.show()
    qtbot.waitExposed(box)
    qtbot.keyClick(box, Qt.Key.Key_Return)
    assert box.clicked() == "save"


def test_ask_gibt_den_schluessel_zurueck(qtbot):
    def antworten():
        for widget in qtbot_widgets():
            if isinstance(widget, HaloMessageBox) and widget.isVisible():
                widget.buttons["discard"].click()

    from PyQt6.QtWidgets import QApplication

    def qtbot_widgets():
        return QApplication.topLevelWidgets()

    QTimer.singleShot(50, antworten)
    answer = HaloMessageBox.ask(None, "Frage", "Was tun?",
                                buttons=(("save", "Speichern"), ("discard", "Verwerfen")))
    assert answer == "discard"


def test_einzelheiten_klappen_auf(qtbot, paint):
    box = HaloMessageBox("Fehler", "Export fehlgeschlagen.", kind="error", details="Traceback ...")
    qtbot.addWidget(box)
    box.show()
    qtbot.waitExposed(box)
    assert box.details.isHidden()
    box.details_button.click()
    assert not box.details.isHidden()
    assert box.details.toPlainText() == "Traceback ..."
    paint(box)


def test_alle_arten_zeichnen_und_unbekannte_wird_abgelehnt(qtbot, paint):
    import pytest
    for kind in HaloMessageBox.KINDS:
        box = HaloMessageBox("Art", "Text", "Zusatz", kind=kind)
        qtbot.addWidget(box)
        box.show()
        paint(box)
    with pytest.raises(ValueError):
        HaloMessageBox("x", "y", kind="fatal")
