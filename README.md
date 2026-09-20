# qt-controls-pyrs

Bedienelemente für PyQt6, die sich nach außen wie ihre Qt-Vorbilder verhalten.

| Baustein | Ersetzt | Wofür |
| --- | --- | --- |
| `GlowButton` | `QPushButton` | Zeigt an, dass eine Aufgabe läuft: Beschriftung blendet über, Rahmen leuchtet in wandernden Regenbogenfarben |
| `FrameButton` | `QPushButton` | Gibt unter der Maus seinen Schleier ab und fängt dafür einen feinen Rahmen ein, der von außen hereinfährt |
| `DashBorderButton`, `SpreadButton`, `RaisedButton`, `ShineButton`, `HaloButton` | `QPushButton` | Fünf Knöpfe aus einer CSS-Sammlung, jeder mit einer eigenen Bewegung unter der Maus |
| `PulseHaloButton` | `QPushButton` | Wie `HaloButton`, lässt während der laufenden Aufgabe ruhig Striche aus dem Rahmen wandern |
| `FiberHaloButton` | `QPushButton` | Dasselbe auffälliger: ziehende Farbflächen und schwingende Fasern füllen die ganze Fläche |
| `AnimatedToggle` | `QCheckBox` | Schiebeschalter mit gleitendem Knopf |
| `HeartCheckBox` | `QCheckBox` | Herz zum Anhaken: es füllt sich mit einem Hüpfer, sechs Funken stieben weg |
| `StatusBar` | `QLabel` in einer Statuszeile | Klappt lange Meldungen kurz auf, ohne das Fenster zu verschieben |
| `ReferenceThumb` | — | Bild-Miniatur als Karte, deren Rahmen dem Mauszeiger nachleuchtet; lädt die Datei zu ImgBB hoch und zeigt den Fortschritt |
| `PromptEditor` | `QTextEdit` | Hebt Abschnittsüberschriften im Text hervor |
| `flash_taskbar()` | — | Lässt den Taskleisten-Eintrag blinken (Windows) |

Die animierten Widgets holen ihre Farben aus der Palette und sehen deshalb im
Hell- wie im Dunkelmodus richtig aus.

Abhängigkeiten: PyQt6, dazu `requests` — das braucht nur der ImgBB-Upload von
`ReferenceThumb`.

## Aufbau

Knöpfe und Kästchen liegen in eigenen Ordnern, weil es von beiden mehrere gibt:

```
qt_controls_pyrs/
    buttons/      GlowButton, FrameButton, die fünf aus hoverbuttons.py
    checkboxes/   AnimatedToggle, HeartCheckBox
    statusbar.py, referencethumb.py, imgbb.py, prompt_editor.py, flashtaskbar.py
```

Importiert wird weiterhin aus dem Paket selbst — `from qt_controls_pyrs import
GlowButton` —, die Ordner sind also nur innen sichtbar. Wer mag, greift auch
direkt zu: `from qt_controls_pyrs.buttons import GlowButton`.

## Installation

Aus dem lokalen Ordner, damit Änderungen sofort in allen Projekten wirken:

```
pip install -e Z:\Code\python\QtControlsPyRS
```

PyInstaller findet das Paket danach von allein — es enthält keine Bilddateien,
also braucht die `.spec` keine Zusatzeinträge.

## In eine bestehende Anwendung einbinden

Die Widgets zeichnen sich selbst und holen ihre Farben aus der Palette. Wer in
seiner Anwendung eine Palette setzt — üblich ist `app.setStyle("Fusion")` und
ein `QPalette` gleich beim Start —, bekommt sie also ohne Zutun im Stil des
Programms. Wichtig ist nur die Reihenfolge: erst die Palette setzen, dann die
Fenster bauen.

Ein Stylesheet (`setStyleSheet`) wirkt dagegen **nicht** auf sie. Das ist keine
Lücke, sondern der Preis dafür, dass sie ihr Aussehen selbst in die Hand nehmen:
Qt fragt bei einem selbstgezeichneten Widget keine QSS-Regeln ab. Was eine
Anwendung im Stylesheet stehen hat, gehört für diese Widgets also in die Palette
oder in eine eigene Unterklasse mit den passenden Konstanten.

Wo ein Widget etwas auf Palettenfarben nicht abbilden kann — die Signalfarbe des
`FiberHaloButton`, die Herzfarbe der `HeartCheckBox` —, gibt es einen Setter und
eine Klassenkonstante dafür.

## Ausprobieren

```
python examples/demo.py
```

Zeigt Schalter, Herz, alle Knöpfe, die Bild-Miniatur und die Statuszeile in
einem Fenster, im Dunkelmodus. Mit gesetztem `IMGBB_API_KEY` lädt die Miniatur
auch wirklich hoch, sonst bleibt es bei der Vorschau.

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
herüber. Die Beschriftung wird mitgezeichnet, ein Klick darauf schaltet
ebenfalls um.

Einstellbar: `TRACK_W`, `TRACK_H`, `GAP`, `SLIDE_MS`.

Grundlage ist `AnimatedToggle` aus dem Paket
[qtwidgets](http://github.com/learnpyqt/python-qtwidgets) von Martin Fitzpatrick
(MIT). Diese Fassung ist nach PyQt6 portiert, zeichnet zusätzlich die
Beschriftung und nimmt die Farben aus der Palette. Den Puls-Ring der Vorlage
gibt es hier nicht mehr.

## Fünf Knöpfe aus einer CSS-Sammlung

```python
from qt_controls_pyrs import (
    DashBorderButton, HaloButton, RaisedButton, ShineButton, SpreadButton
)

button = ShineButton("Hover me")
button.clicked.connect(los)
```

Die `.btn-1` bis `.btn-5` einer bekannten CSS-Sammlung, jeder mit einer eigenen
Bewegung unter der Maus:

| Klasse | Vorlage | Unter der Maus |
| --- | --- | --- |
| `DashBorderButton` | `.btn-1` | Der geschlossene Rahmen schnurrt zu einem kurzen, dicken Strich zusammen, die Füllung verschwindet, die Schrift geht von hauchdünn auf fett |
| `SpreadButton` | `.btn-2` | Die Schrift sperrt sich auf 5 Pixel, über und unter ihr wächst je ein feiner Strich aus der Mitte auf 70 % der Breite |
| `RaisedButton` | `.btn-3` | Steht mit harter Kante und Schatten erhaben da und legt sich flach, die Schrift nimmt dabei die Farbe der Fläche an |
| `ShineButton` | `.btn-4` | Ein schräger Lichtstreifen wischt einmal über die Fläche; der Rand schneidet ihn ab |
| `HaloButton` | `.btn-5` | Der Strich um den Knopf wandert nach außen und verblasst, während der Knopf innen wie außen zu leuchten anfängt |

Gemeinsam ist ihnen die Grundform `_HoverButton`: 45 Pixel hoch, Beschriftung in
Großbuchstaben (`UPPERCASE = False` schaltet das ab) und ein Weg `hover` von 0
nach 1, den die Maus vorwärts und beim Verlassen rückwärts laufen lässt. Hin-
und Rückweg dürfen verschieden sein — `DashBorderButton` braucht hin 1350 ms mit
weitem Ausschwingen und zurück 350 ms geradlinig, genau wie die Vorlage. Wer
eine zweite, anders getaktete Bewegung braucht, meldet sie mit `_track()` an;
`SpreadButton` macht das für seine Striche, die schneller sind als die Schrift.

Auch hier kommen die Farben aus der Palette: die Fläche aus `Button`, alles
Weiße der Vorlage aus `ButtonText`. Wo die Vorlage den Seitengrund durchscheinen
lässt, zeichnet der Knopf schlicht nichts — dort steht das Elternteil. Damit
sehen die fünf im Hell- wie im Dunkelmodus richtig aus, statt nur auf Rot.

Zwei Stellen weichen bewusst ab:

* `box-shadow` hat in Qt keine Entsprechung, weil beim Zeichnen kein
  Weichzeichner zur Verfügung steht. Schatten und Schein entstehen hier aus
  mehreren immer blasseren Strichen übereinander.
* Was außerhalb der Fläche liegt — der Schatten von `RaisedButton`, der
  auswandernde Strich von `HaloButton` — braucht Platz, denn ein Widget
  zeichnet nicht über seinen Rand hinaus. Beide halten sich über `ROOM` einen
  Rand frei, den `sizeHint()` mitrechnet.

Einstellbar über Klassenkonstanten: `HEIGHT`, `PAD`, `ROOM`, `IN_MS`/`OUT_MS`
samt Kurven, `UPPERCASE`, `WEIGHT_REST`/`WEIGHT_HOVER` und
`SPACING_REST`/`SPACING_HOVER`. Dazu je Knopf die eigenen Werte, etwa `DASH`,
`GAP` und `OFFSET` beim `DashBorderButton` oder `INNER_GLOW` und `OUTER_GLOW`
beim `HaloButton`.

## PulseHaloButton

```python
from qt_controls_pyrs import PulseHaloButton

button = PulseHaloButton("Generate", busy_text="Generating")
button.clicked.connect(start)

def start():
    # Der Klick hat die Anzeige schon gestartet (AUTO_BUSY).
    starte_aufgabe()

def done():
    button.stop_busy()
```

Der `HaloButton` mit einer zurückhaltenden Arbeitsanzeige: unter der Maus
verhält er sich unverändert, und solange etwas läuft, lösen sich Striche aus
seinem Rahmen und wandern nach außen, wo sie verblassen. `RINGS` davon sind
gleichzeitig unterwegs, gegeneinander versetzt, damit nie eine Lücke entsteht;
auf halbem Weg sind sie am kräftigsten. Die Fläche bleibt dabei leer — gedacht
für Stellen, an denen eine Anzeige nötig ist, aber nichts blinken oder flimmern
soll.

Gleichzeitig blendet die Ruhe-Beschriftung aus und die Arbeits-Beschriftung an
derselben Stelle ein; beim Anhalten umgekehrt. Ohne `busy_text` bleibt die
Beschriftung einfach stehen.

### Steuerung

Dieselbe wie beim `GlowButton`, ein Austausch ist also unauffällig:

```python
button.start_busy("Generating")   # Beschriftung blendet mit über
button.stop_busy()
button.is_busy()
```

`AUTO_BUSY = True` heißt: ein Klick startet die Anzeige von allein, beendet wird
sie von der Anwendung. Wer das nicht will — etwa weil die Anwendung nach dem
Klick noch prüft und abbrechen kann —, setzt die Konstante auf `False` und ruft
`start_busy()` selbst auf.

Sperrt die Anwendung den Knopf, solange sie arbeitet (`setEnabled(False)`),
bleibt die Anzeige trotzdem kräftig — gerade sie soll man ja sehen, während man
wartet. Alles andere am Knopf blasst wie gewohnt ab. `sizeHint()` rechnet immer
mit der breiteren der beiden Beschriftungen, damit der Knopf nicht springt,
sobald die Aufgabe losläuft.

Einstellbar: `RINGS`, `RING_W` und `RING_ALPHA` (die wandernden Striche),
`CYCLE_MS` (Dauer eines Durchlaufs, länger heißt ruhiger), `FADE_MS` (Ein- und
Ausblenden), `SWAP_MS` (Überblenden der Beschriftung), `ACCENT` und alles vom
`HaloButton`.

### Die gemeinsame Grundlage

Zustand, Takt und die überblendende Beschriftung stehen in `BusyHaloButton`;
`PulseHaloButton` und `FiberHaloButton` erben davon und unterscheiden sich nur
darin, was sie damit zeichnen. Wer eine eigene Anzeige will, erbt ebenfalls und
überschreibt eine einzige Methode:

```python
from qt_controls_pyrs import BusyHaloButton

class BalkenButton(BusyHaloButton):
    def _paint_busy(self, painter, rect, ink):
        # `self.phase` läuft in CYCLE_MS von 0 nach 1 und wieder von vorn;
        # die Deckkraft hat der Aufrufer schon gesetzt.
        ...
```

## FiberHaloButton

```python
from qt_controls_pyrs import FiberHaloButton

button = FiberHaloButton("Generate", busy_text="Generating")
button.clicked.connect(start)

def start():
    # Der Klick blendet die Animation schon auf (AUTO_BUSY).
    starte_aufgabe()

def done():
    button.stop_busy()
```

Der `HaloButton` mit Arbeitsanzeige: unter der Maus verhält er sich
unverändert, nach dem Klick füllt sich seine ganze Fläche.

Zuunterst liegt ein tiefer Ton der Grundfarbe. Darüber ziehen vier weiche
Flächen in verschiedenen Nuancen davon durch den Knopf — jede in ihrem eigenen
Tempo, teils von links, teils von rechts, dabei langsam auf und ab wandernd.
Dazwischen blitzen drei helle Lichter auf, die an- und abschwellen. Ganz oben
schwingen fünf dünne Glasfasern von Rand zu Rand: sie laufen an den Rändern aus,
sind in der Mitte am weitesten ausgelenkt, haben je eigene Wellenlängen und
driften abwechselnd in beide Richtungen; in jeder wandert ein Lichtpaket entlang.

Ein voller Durchlauf dauert `CYCLE_MS` (9 Sekunden), und weil alle Bewegungen
gegeneinander verschoben sind, wiederholt sich das Bild nie sichtbar. Beim Ein-
und Ausblenden liegt ein kurzer Übergang, und die Bewegung hält erst an, wenn
nichts mehr davon zu sehen ist. Der Halo-Strich und sein Schein liegen über der
Animation, nicht darunter.

Gesteuert wird er genau wie der `PulseHaloButton` — `start_busy()`,
`stop_busy()`, `is_busy()`, `AUTO_BUSY`, die überblendende Beschriftung und das
Verhalten im gesperrten Zustand stehen dort beschrieben. Beide erben das von
`BusyHaloButton`, ein Austausch untereinander ist also eine Zeile.

### Farben ändern

Im Ruhezustand kommen die Farben wie überall in dieser Sammlung aus der Palette:
die Fläche aus `Button`, Schrift und Strich aus `ButtonText`. Ein Knopf in einer
fremden Anwendung übernimmt deren Aussehen also von selbst, sobald dort eine
Palette gesetzt ist.

Die laufende Animation hat dagegen eine eigene Grundfarbe — sie soll auffallen
und gerade nicht mit dem Rest verschwimmen. Aus ihr leitet sich alles ab: der
tiefe Grund, die Nuancen der ziehenden Flächen, die Lichter und die äußeren
Fasern. Gerechnet wird in HSV, verschoben werden Farbton, Sättigung und
Helligkeit — ein Wechsel der Grundfarbe färbt deshalb das ganze Bild stimmig um,
auf drei Wegen:

```python
# 1. für die ganze Anwendung, vor dem Erzeugen der Knöpfe
FiberHaloButton.ACCENT = "#ffb703"

# 2. für einen einzelnen Knopf, auch zur Laufzeit
button.setAccentColor("#ffb703")
button.setAccentColor(palette.color(QPalette.ColorRole.Highlight))

# 3. dauerhaft in einer eigenen Klasse
class ProjektButton(FiberHaloButton):
    ACCENT = "#ffb703"
    CYCLE_MS = 6000
```

Der dritte Weg ist der saubere, wenn eine Anwendung mehrere solcher Knöpfe hat:
alle Abweichungen stehen an einer Stelle, und die Anwendung benutzt nur noch
ihre eigene Klasse.

Einstellbar sind außerdem `FIBERS` (Anzahl der Fasern), `SWING` (wie weit sie
ausschlagen), `CYCLE_MS`, `FADE_MS` und `PACKET` (Länge des Lichtpakets). Das
Bild selbst steht in drei Tabellen: `GROUND` ist der tiefe Grundton, `CLOUDS`
beschreibt je Fläche Farbton-Versatz, Sättigung, Helligkeit, Deckkraft, Größe,
Lage und Tempo, `SPARKS` dasselbe knapper für die Lichter. Wer das Bild
umbauen will, ändert dort Zeilen, statt Zeichencode anzufassen. Alles vom
`HaloButton` gilt weiter.

## HeartCheckBox

```python
from qt_controls_pyrs import HeartCheckBox

heart = HeartCheckBox("Gefällt mir")
heart.setToolTip("Like")
heart.toggled.connect(merken)
```

Nachbau des Musters [heart-container](https://uiverse.io) von Uiverse.io
(catraco). Im Ruhezustand steht nur der Umriss da. Angehakt fährt das volle Herz
in einem Sprung heraus — erst auf 1.2, dann zurück auf 1 — und leuchtet dabei
kurz auf, während sechs Striche nach außen stieben und verblassen. Abgehakt ist
das volle Herz sofort weg; die Vorlage blendet dort ebenfalls nicht aus, sondern
schaltet mit `display: none` hart um.

Nach außen bleibt es eine `QCheckBox`: `isChecked()`, `setChecked()` und das
`toggled`-Signal funktionieren unverändert. Die Beschriftung wird mitgezeichnet,
ein Klick darauf hakt ebenfalls an.

Die beiden Herzen sind die Originalpfade der Vorlage, gezeichnet über
`QSvgRenderer` — das Herz bleibt dadurch in jeder Größe scharf. Es füllt die
Höhe des Widgets: ein kleineres Kästchen bekommt ein kleineres Herz, samt
Funken. Die Funken der Vorlage fliegen weiter hinaus, als in Qt Platz ist (ein
Widget zeichnet nicht über seinen Rand hinaus), deshalb hält das Kästchen
`SPARK_ROOM` Pixel Rand frei und die Funken rücken so weit zusammen, dass sie
am Ende gerade noch hineinpassen.

Die Herzfarbe ist `--heart-color` der Vorlage und zur Laufzeit austauschbar:

```python
heart.setHeartColor("#44cc88")
```

Einstellbar über Klassenkonstanten: `HEART` (Kantenlänge), `SPARK_ROOM`,
`SPARK_END` (wie weit die Funken wachsen), `GAP`, `POP_MS`, `SPARK_MS`,
`COLOR` und `SPARKS` (die sechs Striche).

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
einem Fehler. Ohne Schlüssel bleibt es bei der reinen Vorschau — es wird nichts
hochgeladen.

Die drei Signale liefern immer den `index` mit, damit ein Feld aus mehreren
Miniaturen mit einem einzigen Handler auskommt.

### Wie sie aussieht

Leer ist sie eine dunkle Karte mit einem Pluszeichen, deren feiner Rahmen dort
aufleuchtet, wo der Mauszeiger steht — nachgebaut nach dem CSS-Muster, bei dem
ein `radial-gradient` dem Zeiger folgt und nur ein Streifen von einem Pixel
davon zu sehen ist. Innen liegt dann zusätzlich ein weicher Schein, und die
Karte schrumpft eine Spur (`HOVER_SCALE`, wie `transform: scale(0.98)`).

Wie im Vorbild leuchten **alle** Miniaturen nebeneinander mit, nicht nur die
unter dem Zeiger: jede bekommt dieselbe Stelle, rechnet sie in ihre eigenen
Koordinaten um und wird zum Zeiger hin heller. Dafür braucht es keinen globalen
Maus-Filter — die Miniatur gibt die Bewegung an ihre Geschwister im selben
Elternteil weiter.

Liegt ein Bild darin, bleibt das Leuchten auf dem Rahmen, und unter der Maus
legt sich eine halbdurchsichtige Decke darüber (`ThumbOverlay`) mit einem runden
X in der Mitte: es dreht sich beim Erscheinen zweimal schnell durch und kommt
weich zum Stillstand. Das X entfernt das Bild, ein Klick daneben tauscht es aus.
Unter der Maus färbt sich das X rot.

Ein Unterschied zum Vorbild: dort ist der Rahmen unsichtbar, bis die Maus das
erste Mal darüberfährt. Hier bleibt immer ein ruhiger Rahmen stehen
(`RIM_ALPHA`), sonst sähe eine leere Karte aus wie ein Loch.

Die Leuchtfarbe ist `#5a8cff` und wie beim `FiberHaloButton` austauschbar —
über `GLOW_COLOR` für alle, `setGlowColor()` für eine einzelne. Der Rest kommt
aus der Palette: die Kartenfläche aus `Base`, Pluszeichen und Rahmen aus
`WindowText`.

Einstellbar: `THUMB_SIZE`, `WIDGET_HEIGHT`, `PROGRESS_HEIGHT`, `RADIUS`,
`HOVER_SCALE`, `HOVER_MS`, `GLOW_MS`, `GLOW_REACH`, `INNER_REACH`,
`INNER_ALPHA`, `RIM_ALPHA` und die Farben `_COLOR_PROGRESS`,
`_COLOR_UPLOADING`, `_COLOR_ERROR`. An der Decke: `ThumbOverlay.DIM` und
`FADE_MS`, am X `CloseButton.SIZE`, `SPIN_MS`, `SPIN_TURNS` und `DANGER`.

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
