# Changelog

## Unreleased

- `HeartCheckBox` aufgenommen: Herz zum Anhaken nach dem Muster
  "heart-container" von Uiverse.io. Das volle Herz springt beim Anhaken heraus
  und leuchtet kurz auf, sechs Funken stieben weg; abgehakt ist es sofort weg.
  Die Herzen sind die Originalpfade der Vorlage (`QSvgRenderer`), die Farbe ist
  über `setHeartColor()` austauschbar. Das Herz geht mit der Widget-Größe mit.
- Knöpfe und Kästchen liegen jetzt in den Unterpaketen `buttons` und
  `checkboxes`. Die Importe aus `qt_controls_pyrs` bleiben unverändert; wer
  bisher `qt_controls_pyrs.glowbutton` oder `.toggleswitch` direkt importiert
  hat, schreibt nun `qt_controls_pyrs.buttons.glowbutton` beziehungsweise
  `qt_controls_pyrs.checkboxes.toggleswitch`.
- `AnimatedToggle`: den Puls-Ring beim Umschalten gibt es nicht mehr, samt
  `PULSE_MS` und der Eigenschaft `pulse_radius`. Der Knopf gleitet nur noch.
- Die Demo zeigt jetzt auch `ReferenceThumb` und `HeartCheckBox`.
- `FrameButton` aufgenommen: Knopf nach dem CSS-Muster `.btn-three`. Unter der
  Maus schrumpft der Schleier über der Fläche zur Mitte und verblasst, während
  ein feiner Rahmen von außen hereinfährt; die Fläche hellt dabei langsamer auf.
  Die Farben kommen aus der Palette, damit der Knopf im Hell- wie im Dunkelmodus
  stimmt. Für den hereinfahrenden Rahmen hält der Knopf einen Rand frei
  (`RING_ROOM`), den `sizeHint()` mitrechnet.

## 0.2.0 – 2026-09-20

- Paket heißt jetzt `qt_controls_pyrs` (vorher `qt_controls`).
- `ReferenceThumb` samt ImgBB-Anbindung (`ImgBBClient`, `ImgBBUploadWorker`)
  aufgenommen. Neue Abhängigkeit: `requests`.
- `PromptEditor` mit `PromptHighlighter` aufgenommen, von PySide6 nach PyQt6
  portiert. Die Abschnitte werden jetzt direkt übergeben
  (`PromptEditor(["Motiv", "Stil"])`) statt über ein Config-Objekt;
  `reload_sections()` heißt `setSections()`.
- `flash_taskbar()` aufgenommen, mit Schutz für Nicht-Windows-Systeme,
  einstellbarer Blinkzahl und `stop_flashing()`.
- `StatusBar` richtet sich beim Erzeugen und beim Anzeigen selbst aus.

## 0.1.0 – 2026-09-20

Erste Fassung. Die drei Widgets stammen aus dem Projekt APIImageGenerator und
wurden für die Wiederverwendung herausgelöst.

- `GlowButton`: Ruhezustand mit abgerundeter Fläche und Rahmen in der
  Akzentfarbe. Während einer laufenden Aufgabe blenden Ruhe- und
  Arbeits-Beschriftung ineinander über (Zoom + Sichtbarkeit) und der Rahmen
  leuchtet in waagrecht wandernden Regenbogenfarben. Alias `GenerateButton`.
- `AnimatedToggle`: Schiebeschalter mit gleitendem Knopf und Puls, portiert
  nach PyQt6, mit mitgezeichneter Beschriftung und Farben aus der Palette.
- `StatusBar`: Statuszeile, die lange Meldungen über dem darüberliegenden
  Inhalt aufklappt, nach einer Haltezeit wieder zusammenklappt und dann
  Scroll-Pfeile anbietet. Richtet sich selbstständig neu aus, wenn ihr
  Platzhalter die Größe ändert.
