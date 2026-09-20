# qt-controls-pyrs

Bedienelemente für PyQt6, die sich nach außen wie ihre Qt-Vorbilder verhalten.

| Baustein | Ersetzt | Wofür |
| --- | --- | --- |
| `GlowButton` | `QPushButton` | Zeigt an, dass eine Aufgabe läuft: Beschriftung blendet über, Rahmen leuchtet in wandernden Regenbogenfarben |
| `FrameButton` | `QPushButton` | Gibt unter der Maus seinen Schleier ab und fängt dafür einen feinen Rahmen ein, der von außen hereinfährt |
| `AnimatedToggle` | `QCheckBox` | Schiebeschalter mit gleitendem Knopf und Puls beim Umschalten |
| `StatusBar` | `QLabel` in einer Statuszeile | Klappt lange Meldungen kurz auf, ohne das Fenster zu verschieben |
| `ReferenceThumb` | — | Bild-Miniatur zum Anklicken, lädt die Datei zu ImgBB hoch und zeigt den Fortschritt |
| `PromptEditor` | `QTextEdit` | Hebt Abschnittsüberschriften im Text hervor |
| `flash_taskbar()` | — | Lässt den Taskleisten-Eintrag blinken (Windows) |

Die animierten Widgets holen ihre Farben aus der Palette und sehen deshalb im
Hell- wie im Dunkelmodus richtig aus.

Abhängigkeiten: PyQt6, dazu `requests` — das braucht nur der ImgBB-Upload von
`ReferenceThumb`.

## Installation

Aus dem lokalen Ordner, damit Änderungen sofort in allen Projekten wirken:

```
pip install -e Z:\Code\python\QtControlsPyRS
```

PyInstaller findet das Paket danach von allein — es enthält keine Bilddateien,
also braucht die `.spec` keine Zusatzeinträge.

## Ausprobieren

```
python examples/demo.py
```

Zeigt Schalter, beide Knöpfe und die Statuszeile in einem Fenster, im Dunkelmodus.

## GlowButton

```python
from qt_controls_pyrs import GlowButton

button = GlowButton("✨ Generate AI", busy_text="Generating")
button.setFixedHeight(50)
button.clicked.connect(start)

def start():
    button.setEnabled(False)
    button.start_busy()          # Text blendet über, Rahmen wird zum Regenbogen

def done():
    button.stop_busy()           # blendet zurück
    button.setEnabled(True)
```

Im Ruhezustand eine abgerundete Fläche mit ruhigem Rahmen in der Akzentfarbe.
Nach `start_busy()` zoomt die Ruhe-Beschriftung heraus und verblasst, während
die Arbeits-Beschriftung hereinzoomt — beide werden währenddessen gleichzeitig
gezeichnet, der Übergang ist also weich. Gleichzeitig wandern sieben Farben
waagrecht durch den Rahmen; darunter liegt derselbe Verlauf als breiterer,
halbtransparenter Strich, was das Leuchten ergibt.

Weil der Knopf sich selbst zeichnet, bleibt die Schrift auch im gesperrten
Zustand gut lesbar, statt grau zu verblassen.

Einstellbar über Klassenkonstanten: `RADIUS`, `BORDER_W`, `GLOW_W`, `GLOW_A`,
`MORPH_MS` (Dauer der Überblendung), `CYCLE_MS` (Dauer eines Farbdurchlaufs),
`ZOOM` (Zoomweite) und `RAINBOW` (die Farbfolge; erste und letzte Farbe sollten
gleich sein, damit das Band nahtlos umläuft).

`GenerateButton` ist ein Alias auf `GlowButton` für älteren Code.

## FrameButton

```python
from qt_controls_pyrs import FrameButton

button = FrameButton("Mit Rahmen")
button.setFixedHeight(44)
button.clicked.connect(los)
```

Nachbau des CSS-Musters `.btn-three`: im Ruhezustand liegt ein hauchdünner
Schleier (10 %) über der ganzen Fläche und kein Rahmen ist zu sehen. Kommt die
Maus darauf, schrumpft der Schleier in 300 ms zur Mitte und verblasst, während
gleichzeitig ein feiner Rahmen (50 %) von außen hereinfährt und sichtbar wird.
Beim Verlassen läuft beides rückwärts. Die Fläche darunter hellt in 500 ms leicht
auf — das ist das `transition: all 0.5s` der Vorlage.

Schleier und Rahmen nehmen die Textfarbe aus der Palette, nicht fest Weiß: im
Dunkelmodus ist das dasselbe wie im CSS, im Hellmodus wären weiße Schichten auf
hellem Grund unsichtbar. Der Knopf zeichnet auch seine Beschriftung selbst,
damit Schleier und Rahmen darüber liegen (in CSS haben beide `z-index: 1`) und
die Schrift im gesperrten Zustand lesbar bleibt.

Der Rahmen startet außerhalb der Fläche, und Qt zeichnet nicht über den
Widget-Rand hinaus. Deshalb hält der Knopf `RING_ROOM` Pixel Rand frei: die
sichtbare Fläche ist etwas kleiner als die Widget-Geometrie, `sizeHint()` rechnet
den Rand mit ein. Bei kleinen Knöpfen entspricht der Weg genau `scale(1.2)`, bei
breiten bleibt er bei `RING_ROOM` Pixeln stehen, statt mit der Breite
mitzuwachsen — sonst käme der Rahmen bei einem breiten Knopf von sehr weit außen
und die Fläche müsste ein Fünftel der Breite dafür hergeben.

Wird der Knopf gesperrt, während die Maus darauf steht, nimmt er Schleier und
Rahmen selbst zurück — ein gesperrtes Widget bekommt kein `leaveEvent` mehr.

Einstellbar über Klassenkonstanten: `RADIUS` (0 = eckig wie im CSS), `VEIL_A`
und `VEIL_END` (Deckkraft und Endgröße des Schleiers), `RING_A`, `RING_W`,
`RING_START` und `RING_ROOM` (Rahmen), `HOVER_MS`, `TINT_MS` und `TINT`
(Aufhellung der Fläche, 100 = keine).

## AnimatedToggle

```python
from qt_controls_pyrs import AnimatedToggle

toggle = AnimatedToggle("Autoretry")
toggle.setChecked(True)
toggle.toggled.connect(speichern)
```

Eine `QCheckBox` mit eigenem Aussehen: `isChecked()`, `setChecked()` und das
`toggled`-Signal funktionieren unverändert. Der Knopf gleitet in 200 ms
herüber, danach läuft ein kurzer Puls-Ring nach außen. Die Beschriftung wird
mitgezeichnet, ein Klick darauf schaltet ebenfalls um.

Einstellbar: `TRACK_W`, `TRACK_H`, `GAP`, `SLIDE_MS`, `PULSE_MS`.

Grundlage ist `AnimatedToggle` aus dem Paket
[qtwidgets](http://github.com/learnpyqt/python-qtwidgets) von Martin Fitzpatrick
(MIT). Diese Fassung ist nach PyQt6 portiert, zeichnet zusätzlich die
Beschriftung und nimmt die Farben aus der Palette.

## StatusBar

Die Statuszeile hängt **nicht** im Layout — sonst würde eine lange Meldung die
Mindestbreite des Fensters hochtreiben und alles verschieben. Stattdessen steht
im Layout ein Platzhalter, über dem die Anzeige schwebt:

```python
from qt_controls_pyrs import StatusBar

slot = QWidget()                     # hält die Zeile im Layout frei
slot.setFixedHeight(20)
slot.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
status_row.addWidget(slot)

self.status = StatusBar(slot, self)  # Elternteil ist das Fenster
self.status.setText("Bereit")

def resizeEvent(self, event):        # Ausrichtung mitführen
    super().resizeEvent(event)
    self.status.sync_geometry()
```

Kurze Meldungen belegen eine Zeile. Eine lange Meldung klappt nach **oben** über
den Inhalt darüber auf, bis sie lesbar ist (höchstens `MAX_LINES` Zeilen), bleibt
`HOLD_MS` stehen und klappt dann wieder zusammen. Passt der Text danach nicht in
die eine Zeile, erscheinen rechts zwei kleine Scroll-Pfeile; ein Klick auf die
Zeile klappt sie erneut auf. Der vollständige Text steht immer im Tooltip.

`setText()` und `text()` verhalten sich wie bei einem `QLabel`, ein Austausch
gegen ein vorhandenes Label ist also unauffällig.

Einstellbar: `LINE_HEIGHT`, `MAX_LINES`, `HOLD_MS`, `ANIM_MS`.

## ReferenceThumb

```python
from qt_controls_pyrs import ReferenceThumb

thumb = ReferenceThumb(index=0, imgbb_api_key=key)
thumb.uploaded.connect(lambda i, url: merken(i, url))
thumb.upload_failed.connect(lambda i, fehler: melden(fehler))
thumb.cleared.connect(vergessen)
```

Ein Klick öffnet den Dateidialog, danach läuft der Upload im Hintergrund
(`ImgBBUploadWorker`, eigener Thread) und ein schmaler Balken unter dem Bild
zeigt den Fortschritt: blau während des Hochladens, grün bei Erfolg, rot bei
einem Fehler. Oben rechts erscheint ein kleiner Schließknopf. Ohne Schlüssel
bleibt es bei der reinen Vorschau — es wird nichts hochgeladen.

Die drei Signale liefern immer den `index` mit, damit ein Feld aus mehreren
Miniaturen mit einem einzigen Handler auskommt.

Einstellbar: `THUMB_SIZE`, `WIDGET_HEIGHT`, `PROGRESS_HEIGHT` und die Farben
`_COLOR_PROGRESS`, `_COLOR_UPLOADING`, `_COLOR_ERROR`.

Der ImgBB-Zugriff liegt offen: `ImgBBClient` lädt eine Datei hoch (mit
Fortschritts-Callback), `ImgBBUploadWorker` tut dasselbe in einem QThread, und
die Fehlerklassen `ImgBBError`, `ImgBBNetworkError`, `ImgBBApiError`,
`ImgBBFileNotFoundError` unterscheiden die Ursachen.

## PromptEditor

```python
from qt_controls_pyrs import PromptEditor

editor = PromptEditor(["Motiv", "Stil", "Kamera"])
editor.setSections(neue_abschnitte)   # auch zur Laufzeit, Inhalt bleibt stehen
```

Aus den Abschnittsnamen entstehen zwei Dinge: ein Platzhaltertext, der die
Abschnitte vorschlägt, und eine Hervorhebung, die jede Zeile fett und grün
färbt, die mit einem Abschnittsnamen beginnt. Namen mit Sonderzeichen sind
zulässig, sie werden maskiert.

## flash_taskbar

```python
from qt_controls_pyrs import flash_taskbar, stop_flashing

flash_taskbar(int(self.winId()))          # dreimal blinken
flash_taskbar(int(self.winId()), count=5)
stop_flashing(int(self.winId()))
```

Nützlich, wenn eine lange Aufgabe fertig ist und das Fenster im Hintergrund
liegt. Nur unter Windows wirksam; sonst passiert nichts und der Aufruf meldet
`False`, sodass man ihn nicht abfangen muss.

## Tests

```
pip install -e .[test]
pytest
```

Die Tests laufen ohne sichtbare Fenster (`QT_QPA_PLATFORM=offscreen`).
