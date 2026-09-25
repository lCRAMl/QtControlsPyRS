# Changelog

## Unreleased

- `HaloPromptBox` aufgenommen: ein mehrzeiliges Eingabefeld im Halo-Stil, das
  sich über den Inhalt darunter ausfahren lässt. Oben rechts sitzt ein
  Doppelpfeil; ein Klick fährt das Feld in 300 ms nach unten aus, ein zweiter
  Klick oder Escape wieder ein. `set_expand_stop()` legt fest, wo unten Schluss
  ist. Wie die `StatusBar` schwebt es über einem Platzhalter im Layout, damit
  das Ausfahren die Aufteilung darunter nicht verschiebt.
- Die Demo zeigt es oben im Fenster; ausgefahren reicht es bis an die
  Statuszeile. Damit alles ins Fenster passt, stehen die Abschnitte der Demo
  etwas enger (Abstand 18 → 12 px).

- `ReferenceThumb`: Ein Klick auf die Decke über einem geladenen Bild öffnete
  den Dateidialog zweimal — nach dem ersten Bild erschien sofort wieder ein
  Dialog. Die Decke nahm den Klick nicht an, und Qt reicht einen nicht
  angenommenen Mausklick an das Elternwidget weiter: erst meldete ihn die
  Decke, dann sah ihn die Karte darunter noch einmal. Sie nimmt Drücken und
  Loslassen jetzt an.
- `ReferenceThumb`: Wo der Dateidialog aufgeht, lässt sich festlegen —
  `ReferenceThumb(..., start_dir=pfad)` oder `setStartDir()`. Ohne Angabe
  bleibt es wie bisher bei dem Ordner, den Qt zuletzt gezeigt hat.

- `HaloTabWidget` aufgenommen, in einem neuen Unterpaket `tabs`: Reiter statt
  `QTabWidget`. Die Reiter teilen sich die ganze Breite; unter dem aktiven
  liegt ein dünner Strich in der Signalfarbe auf einer blassen Grundlinie.
  Beim Wechsel gleitet der Strich hinüber, der ganze Inhalt schiebt sich
  seitlich hinaus und wird unscharf, der nächste kommt scharf herein — auf
  Federn wie bei animate-ui, umlenkbar mitten in der Bewegung. Die Höhe
  bleibt fest. Einstellbar über `SLIDE_MS`, `LINE_MS`, `BLUR`, `ACCENT` und
  weitere Konstanten. `ROOM` rückt Leiste und Gleiten ein, damit sie bündig mit
  den Halo-Knöpfen darunter enden; der Inhalt verschwindet beim Gleiten dann
  genau an dieser Kante.
- Die Demo zeigt die Reiter wie später im APIImageGenerator: auf dem ersten
  die Halo-Schalter und das Dropdown, auf dem zweiten ein `PromptEditor`.

- Drei Schalter im Halo-Stil aufgenommen, passend zu den Halo-Knöpfen und
  zum `HaloDropdown`: `FrameToggle` (Rahmen mit gleitender Kugel),
  `LineToggle` (Strich mit laufender Kugel, der hinter ihr aufleuchtet) und
  `HaloCheckBox` (Kästchen, aus dem beim Anhaken einmal ein Strich nach außen
  läuft). Alle drei bleiben eine `QCheckBox`, folgen `RADIUS` und haben ihre
  Signalfarbe in `ACCENT`. Ein Zustand, der vor dem Anzeigen gesetzt wird
  (gespeicherte Einstellungen), steht sofort, ohne Animation. Der klassische
  `AnimatedToggle` bleibt erhalten.
- `HaloDropdown` aufgenommen, in einem neuen Unterpaket `dropdowns`: ein
  Auswahlfeld statt `QComboBox` im Stil der Halo-Knöpfe. Beim Aufklappen
  rollt das Feld von der Leiste aus auf, und die Einträge gleiten nach,
  sobald die Kante sie erreicht — rund 250 ms, unabhängig von der Länge der
  Liste. Bewegt werden nur Lage und Deckkraft, nichts wird skaliert, damit
  die Schrift ruhig bleibt. Nach einer Wahl leuchtet der Eintrag kurz auf, dann
  blendet die Liste als Ganzes aus. Der Pfeil rechts dreht beim Öffnen von ↓
  nach ←.
- `HaloDropdown`: Buchstaben springen zum passenden Eintrag, offen wie
  geschlossen, wiederholt durch alle mit diesem Buchstaben; `SORTED` sortiert
  deutsch und natürlich. `flash()` lässt den Rahmen rot blinken, auch wenn
  das Feld gesperrt ist. Die Markierung gleitet, lange Listen rollen weich,
  der Text in der Leiste blendet bei einem Wechsel über, und
  `setPlaceholderText()` wird gedimmt angezeigt.
- `HaloButton`, `PulseHaloButton` und `FiberHaloButton`: die Ecken lassen sich
  über `RADIUS` abrunden (Voreinstellung 0, also wie bisher). Rahmen,
  wandernde Striche, Schein und die Faser-Animation folgen der Rundung.
- `ReferenceThumb`: die Decke mit dem X blieb nach dem Dateidialog stehen, auch
  wenn der Zeiger längst woanders war. Qt schickt für den Weg über einen
  modalen Dialog kein Leave und meldet weiter `underMouse`; die Karte sieht nun
  zusätzlich nach, wo der Zeiger wirklich steht, und zieht Decke, Schein und
  Größe nach dem Dialog selbst nach — auch wenn er abgebrochen wurde.
- `ReferenceThumb`: wie weit der Schein reicht, hängt jetzt an der Kartenseite
  statt an festen Pixeln — `GLOW_SPREAD` (Voreinstellung 0.25) gibt den
  Grundradius als Anteil davon an. Eine größere Miniatur bekommt damit denselben
  Schein, nur größer. Der Wert entscheidet auch, wie stark die Nachbarinnen
  mitleuchten.
- Die Demo zeigt sechs Miniaturen nebeneinander, weil man daran erst sieht, wie
  der Schein über mehrere Karten wandert.
- `PulseHaloButton` aufgenommen: der `HaloButton` mit einer zurückhaltenden
  Arbeitsanzeige. Aus dem Rahmen lösen sich Striche und wandern nach außen, die
  Fläche bleibt leer. Für Stellen, an denen eine Anzeige nötig ist, aber nichts
  blinken soll.
- Die Arbeits-Beschriftung wird jetzt überblendet statt hart getauscht: die eine
  blendet aus, die andere an derselben Stelle ein (`SWAP_MS`). Gilt für beide
  arbeitenden Halo-Knöpfe.
- Zustand, Takt und Beschriftung der arbeitenden Halo-Knöpfe stehen jetzt in
  `BusyHaloButton`. `FiberHaloButton` erbt davon, sein Verhalten und seine API
  bleiben unverändert; eine eigene Anzeige braucht nur noch `_paint_busy()`.
- `ReferenceThumb` sieht neu aus: eine dunkle Karte, deren feiner Rahmen dort
  aufleuchtet, wo der Mauszeiger steht, nach dem bekannten CSS-Muster mit dem
  mitwandernden `radial-gradient`. Mehrere Miniaturen nebeneinander leuchten
  gemeinsam. Leer zeigt sie ein Pluszeichen und innen zusätzlich einen weichen
  Schein, mit Bild bleibt das Leuchten auf dem Rahmen. Leuchtfarbe `#5a8cff`,
  über `GLOW_COLOR` und `setGlowColor()` austauschbar.
- Der kleine X-Knopf oben rechts ist einer halbdurchsichtigen Decke gewichen
  (`ThumbOverlay`), die unter der Maus über dem Bild aufblendet und ein rundes
  X in der Mitte zeigt; das X dreht sich beim Erscheinen schnell durch und läuft
  weich aus. Ein Klick daneben tauscht das Bild aus.
- `ReferenceThumb` zeichnet sich jetzt selbst, statt ein Label mit Stylesheet zu
  benutzen: `thumb.image` und `thumb.close_btn` gibt es nicht mehr. Dafür gibt
  es `has_image()`, `pixmap()`, `message()` und `thumb.overlay`; `__init__`
  nimmt zusätzlich ein `parent`.
- `FiberHaloButton` aufgenommen: der `HaloButton` mit Arbeitsanzeige. Nach dem
  Klick füllt sich die ganze Fläche — ein tiefer Grund, darüber ziehende
  Farbflächen in Nuancen der Grundfarbe, aufblitzende Lichter und fünf
  schwingende Glasfasern mit wandernden Lichtpaketen; ein Durchlauf dauert
  9 Sekunden. Gesteuert wird er wie der `GlowButton` über `start_busy()` und
  `stop_busy()`, ein Klick startet die Anzeige von allein. Die Grundfarbe der
  Animation (`#5a8cff`) ist über `ACCENT` und `setAccentColor()` austauschbar
  und färbt alle Nuancen mit um; der Rest kommt aus der Palette.
- Fünf Knöpfe aus der CSS-Sammlung `.btn-1` … `.btn-5` aufgenommen:
  `DashBorderButton` (der Rahmen schnurrt zu einem Strich zusammen),
  `SpreadButton` (Sperrschrift mit wachsenden Strichen), `RaisedButton`
  (erhaben und flach), `ShineButton` (Lichtstreifen) und `HaloButton`
  (auswandernder Strich mit Schein). Sie teilen sich die Grundform
  `_HoverButton` und stehen in der Demo nebeneinander.
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
