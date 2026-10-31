# windowstate.py
#
# Was sich eine Oberfläche zwischen zwei Starts merkt.
#
# Fenstergröße, zuletzt benutzter Reiter, Aufteilung der Teiler. Alles davon
# ist eine Entscheidung des Benutzers - er zieht den Griff dorthin, wo er ihn
# haben will, und erwartet ihn beim nächsten Start dort wieder. Eine Vorgabe
# im Quelltext ist nur der erste Vorschlag für den allerersten Start.
#
# Gespeichert wird über QSettings, unter Windows also in der Registry unter
#
#     HKEY_CURRENT_USER\Software\<Anwendung>\<Abschnitt>
#
# Bewusst NICHT in einer mitgelieferten Konfigurationsdatei: dort stehen die
# Daten, die gepflegt und weitergegeben werden. Wie breit jemand seine
# Bedienspalte zieht, gehört zu seinem Rechner.
#
# Wer die gemerkten Werte loswerden will, löscht den Schlüssel - danach gelten
# wieder die Vorgaben aus dem Quelltext.

from __future__ import annotations

from typing import Sequence

from PyQt6.QtCore import QByteArray, QCoreApplication, QSettings
from PyQt6.QtWidgets import QSplitter


_application = ""


def set_application(name: str) -> None:
    """Unter welchem Namen die Werte liegen.

    Einmal beim Start aufzurufen. Wer stattdessen
    ``QCoreApplication.setOrganizationName()`` oder
    ``setApplicationName()`` setzt, braucht das nicht - siehe
    :func:`application`.
    """
    global _application
    _application = name


def application() -> str:
    """Der Name, unter dem gespeichert wird.

    Zuerst der mit :func:`set_application` gesetzte, sonst der von Qt
    bekannte. Fehlt beides, ist das ein Programmierfehler und kein
    Standardwert: unter einem leeren Namen landen die Werte irgendwo, und
    niemand findet sie wieder, um sie zu löschen.
    """
    if _application:
        return _application
    name = (QCoreApplication.organizationName()
            or QCoreApplication.applicationName())
    if name:
        return name
    raise RuntimeError(
        "Kein Anwendungsname gesetzt. Entweder "
        "qt_controls_pyrs.windowstate.set_application('Name') aufrufen oder "
        "QCoreApplication.setOrganizationName('Name') setzen."
    )


def store(section: str) -> QSettings:
    """Der Ablageort eines Fensters oder Reiters."""
    return QSettings(application(), section)


def save_splitter(splitter: QSplitter, section: str, key: str = "splitter") -> None:
    """Merkt sich die Aufteilung eines Teilers."""
    store(section).setValue(key, splitter.saveState())


def restore_splitter(
    splitter: QSplitter,
    section: str,
    fallback: Sequence[int],
    key: str = "splitter",
) -> None:
    """Stellt die gemerkte Aufteilung wieder her, sonst die Vorgabe.

    ``saveState``/``restoreState`` statt der bloßen Zahlen: der Zustand
    enthält auch, welche Seite zusammengeklappt ist, und Qt rechnet ihn auf
    die aktuelle Fensterbreite um. Zwei gespeicherte Bildpunktwerte wären auf
    einem anderen Bildschirm falsch.

    Die Mindestbreiten der beiden Seiten gelten weiterhin - eine gemerkte
    Aufteilung kann also nichts abschneiden, was nicht auch von Hand
    abgeschnitten werden könnte.
    """
    state = store(section).value(key)
    if (isinstance(state, QByteArray) and not state.isEmpty()
            and splitter.restoreState(state)):
        return
    splitter.setSizes(list(fallback))
