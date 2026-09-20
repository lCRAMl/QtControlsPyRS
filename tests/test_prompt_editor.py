from qt_controls_pyrs import PromptEditor, PromptHighlighter

SECTIONS = ["Motiv", "Stil", "Kamera"]


def make(qtbot, sections=SECTIONS) -> PromptEditor:
    editor = PromptEditor(sections)
    editor.resize(320, 160)
    qtbot.addWidget(editor)
    editor.show()
    qtbot.waitExposed(editor)
    return editor


def test_platzhalter_kommt_aus_den_abschnitten(qtbot):
    editor = make(qtbot)
    assert editor.placeholderText() == "Motiv:\nStil:\nKamera:"
    assert editor.sections() == SECTIONS


def test_abschnitte_sind_zur_laufzeit_aenderbar(qtbot):
    editor = make(qtbot)
    editor.setPlainText("Motiv: ein Hund")

    editor.setSections(["Szene"])
    assert editor.sections() == ["Szene"]
    assert editor.placeholderText() == "Szene:"
    assert editor.toPlainText() == "Motiv: ein Hund", "Der Inhalt darf nicht verlorengehen"


def test_abschnittszeile_wird_hervorgehoben(qtbot):
    editor = make(qtbot)
    editor.setPlainText("Motiv: ein Hund\neinfach nur Text")
    qtbot.wait(50)

    formatiert = editor.document().findBlockByNumber(0).layout().formats()
    schlicht = editor.document().findBlockByNumber(1).layout().formats()

    assert formatiert, "Abschnittszeile bekommt keine Hervorhebung"
    assert not schlicht, "Normale Zeile darf nicht hervorgehoben werden"
    assert formatiert[0].format.foreground().color().name() == PromptHighlighter.COLOR


def test_sonderzeichen_im_abschnittsnamen_brechen_nichts(qtbot):
    editor = make(qtbot, ["C++ (Stil)"])
    editor.setPlainText("C++ (Stil): klar")
    qtbot.wait(50)

    assert editor.document().findBlockByNumber(0).layout().formats()


def test_ohne_abschnitte_bleibt_alles_schlicht(qtbot):
    editor = make(qtbot, [])
    editor.setPlainText("Irgendein Text")
    qtbot.wait(50)

    assert editor.placeholderText() == ""
    assert not editor.document().findBlockByNumber(0).layout().formats()
