import math

import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal as Signal
from PyQt6.QtGui import QColor

from qt_controls_pyrs import audiosource
from qt_controls_pyrs.audiosource import AudioSource, MISSING_PACKAGE
from qt_controls_pyrs.halospectrum import HaloSpectrum

QUELLE = AudioSource("Prüfstand", "test-id", loopback=True)


def make(qtbot) -> HaloSpectrum:
    spectrum = HaloSpectrum()
    spectrum.resize(420, 160)
    qtbot.addWidget(spectrum)
    spectrum.show()
    qtbot.waitExposed(spectrum)
    return spectrum


def sinus(frequency: float, amplitude: float = 0.5) -> np.ndarray:
    """Ein Block reiner Ton, so lang wie ein Aufnahmeblock."""
    laenge = HaloSpectrum.BLOCK
    zeit = np.arange(laenge) / HaloSpectrum.SAMPLERATE
    return amplitude * np.sin(2.0 * math.pi * frequency * zeit)


def stille() -> np.ndarray:
    return np.zeros(HaloSpectrum.BLOCK)


def fuettern(spectrum: HaloSpectrum, links, rechts) -> None:
    """So viele Blöcke, wie die Mittelung verrechnet — wie im Betrieb."""
    for _ in range(max(1, spectrum.AVERAGE)):
        spectrum.feed(links, rechts)


def band_fuer(spectrum: HaloSpectrum, frequency: float) -> int:
    """Das Band, in dem diese Frequenz liegt."""
    schritt = spectrum._band_step()
    return int(math.log(frequency / spectrum.FREQ_MIN) / math.log(schritt))


class FakeWorker(QObject):
    """Aufnahme-Attrappe: startet nichts, lässt sich aber von Hand füttern."""

    block = Signal(object, object)
    failed = Signal(str)

    def __init__(self, source, samplerate, block_size, parent=None) -> None:
        super().__init__(parent)
        self.source_used = source
        self.samplerate = samplerate
        self.block_size = block_size
        self.running = False

    def start(self) -> None:
        self.running = True

    def stop(self) -> None:
        self.running = False

    def wait(self, ms: int = 0) -> bool:
        return True

    def isRunning(self) -> bool:
        return self.running


def test_ein_ton_landet_im_richtigen_band(qtbot):
    spectrum = make(qtbot)

    spectrum.feed(sinus(1000.0), stille())
    links, rechts = spectrum._measured

    treffer = band_fuer(spectrum, 1000.0)
    assert links[treffer] == max(links), "der 1-kHz-Balken ist der höchste"
    assert links[treffer] > 0.5
    # Zwei Bänder weiter ist schon fast nichts mehr davon zu sehen.
    assert links[treffer + 2] < links[treffer] / 2
    assert max(rechts) == 0.0, "der rechte Kanal bleibt still"


def test_beide_kanaele_getrennt(qtbot):
    spectrum = make(qtbot)

    spectrum.feed(sinus(200.0), sinus(4000.0))
    links, rechts = spectrum._measured

    assert links.index(max(links)) == band_fuer(spectrum, 200.0)
    assert rechts.index(max(rechts)) == band_fuer(spectrum, 4000.0)


def test_baender_sind_logarithmisch(qtbot):
    spectrum = make(qtbot)
    mitten = spectrum.band_frequencies()

    assert len(mitten) == HaloSpectrum.BANDS
    assert mitten[0] > HaloSpectrum.FREQ_MIN
    assert mitten[-1] < HaloSpectrum.FREQ_MAX
    # Von Band zu Band immer dasselbe Verhältnis — das ist die Oktavteilung.
    verhaeltnisse = [b / a for a, b in zip(mitten, mitten[1:])]
    assert max(verhaeltnisse) - min(verhaeltnisse) < 1e-9


def test_null_hertz_liegt_in_der_mitte(qtbot):
    spectrum = make(qtbot)
    plot = spectrum._plot_rect()
    mitte = plot.center().x()

    links_tief = spectrum.x_for_frequency(HaloSpectrum.FREQ_MIN, 0)
    rechts_tief = spectrum.x_for_frequency(HaloSpectrum.FREQ_MIN, 1)
    assert links_tief < mitte < rechts_tief
    assert mitte - links_tief == rechts_tief - mitte, "beide Hälften spiegeln sich"

    # Hohe Töne stehen außen.
    assert spectrum.x_for_frequency(HaloSpectrum.FREQ_MAX, 0) < links_tief
    assert spectrum.x_for_frequency(HaloSpectrum.FREQ_MAX, 1) > rechts_tief
    assert spectrum.x_for_frequency(HaloSpectrum.FREQ_MAX, 0) >= plot.left()
    assert spectrum.x_for_frequency(HaloSpectrum.FREQ_MAX, 1) <= plot.right()


def test_balken_steigt_schnell_und_faellt_ruhig(qtbot, paint):
    spectrum = make(qtbot)
    treffer = band_fuer(spectrum, 1000.0)

    fuettern(spectrum, sinus(1000.0), stille())
    qtbot.waitUntil(lambda: spectrum.levels()[0][treffer] > 0.5, timeout=2000)
    paint(spectrum)
    hoch = spectrum.levels()[0][treffer]

    fuettern(spectrum, stille(), stille())
    # Fallen dauert länger als Steigen: nach einer Attack-Zeit ist noch etwas da.
    qtbot.wait(HaloSpectrum.ATTACK_MS)
    assert 0.0 < spectrum.levels()[0][treffer] < hoch
    qtbot.waitUntil(lambda: spectrum.levels()[0][treffer] < 0.05, timeout=3000)
    paint(spectrum)


def test_spitzenwert_haelt_und_sinkt_dann(qtbot, paint):
    spectrum = make(qtbot)
    treffer = band_fuer(spectrum, 1000.0)

    fuettern(spectrum, sinus(1000.0), stille())
    qtbot.waitUntil(lambda: spectrum.levels()[0][treffer] > 0.5, timeout=2000)
    fuettern(spectrum, stille(), stille())
    qtbot.waitUntil(lambda: spectrum.levels()[0][treffer] < 0.1, timeout=3000)

    gehalten = spectrum.peaks()[0][treffer]
    assert gehalten > spectrum.levels()[0][treffer], "der Spitzenwert steht noch oben"
    paint(spectrum)

    qtbot.waitUntil(lambda: spectrum.peaks()[0][treffer] < gehalten / 2, timeout=4000)


def test_ruhebild_ohne_ton(qtbot, paint):
    spectrum = make(qtbot)

    assert spectrum.levels() == ([0.0] * HaloSpectrum.BANDS, [0.0] * HaloSpectrum.BANDS)
    paint(spectrum)      # Rahmen, Mittellinie, Markierungen und Grundlinie


def test_farben_sind_austauschbar(qtbot, paint):
    spectrum = make(qtbot)
    unten, oben = spectrum.colors()
    assert (unten, oben) == (QColor(HaloSpectrum.COLOR_LOW), QColor(HaloSpectrum.COLOR_HIGH))

    spectrum.setColors("#ff7a18", "#ffe6c0")
    assert spectrum.colors() == (QColor("#ff7a18"), QColor("#ffe6c0"))
    fuettern(spectrum, sinus(500.0), sinus(500.0))
    qtbot.waitUntil(lambda: max(spectrum.levels()[0]) > 0.3, timeout=2000)
    paint(spectrum)


def test_eigene_einstellungen_in_einer_unterklasse(qtbot, paint):
    class Schmal(HaloSpectrum):
        BANDS = 12
        FREQ_MIN = 60.0
        FREQ_MAX = 12000.0
        RADIUS = 6

    spectrum = Schmal()
    spectrum.resize(300, 120)
    qtbot.addWidget(spectrum)
    spectrum.show()
    qtbot.waitExposed(spectrum)

    assert len(spectrum.band_frequencies()) == 12
    fuettern(spectrum, sinus(1000.0), sinus(1000.0))
    qtbot.waitUntil(lambda: max(spectrum.levels()[0]) > 0.3, timeout=2000)
    paint(spectrum)


def test_start_und_stop(qtbot, monkeypatch):
    spectrum = make(qtbot)
    monkeypatch.setattr("qt_controls_pyrs.halospectrum.AudioCaptureWorker", FakeWorker)
    monkeypatch.setattr("qt_controls_pyrs.halospectrum.default_source", lambda: QUELLE)

    spectrum.start()
    assert spectrum.is_running()
    assert spectrum.source() is QUELLE
    worker = spectrum._worker
    assert (worker.samplerate, worker.block_size) == (HaloSpectrum.SAMPLERATE, HaloSpectrum.BLOCK)

    # Was der Worker meldet, landet in der Anzeige.
    for _ in range(spectrum.AVERAGE):
        worker.block.emit(sinus(1000.0), stille())
    assert max(spectrum._measured[0]) > 0.5

    spectrum.stop()
    assert not spectrum.is_running()
    assert spectrum.source() is None


def test_ohne_quelle_wird_gemeldet(qtbot, monkeypatch):
    spectrum = make(qtbot)
    monkeypatch.setattr("qt_controls_pyrs.halospectrum.default_source", lambda: None)
    monkeypatch.setattr("qt_controls_pyrs.halospectrum.available_sources", list)

    with qtbot.waitSignal(spectrum.failed, timeout=1000) as signal:
        spectrum.start()
    assert "Keine Tonquelle" in signal.args[0]
    assert not spectrum.is_running()


def test_fehler_der_aufnahme_kommt_beim_widget_an(qtbot, monkeypatch):
    spectrum = make(qtbot)
    monkeypatch.setattr("qt_controls_pyrs.halospectrum.AudioCaptureWorker", FakeWorker)

    spectrum.start(QUELLE)
    worker = spectrum._worker
    with qtbot.waitSignal(spectrum.failed, timeout=1000) as signal:
        worker.failed.emit("Gerät weg")
    assert signal.args == ["Gerät weg"]
    assert not spectrum.is_running()


def test_ohne_soundcard_bleibt_alles_ruhig(qtbot, monkeypatch):
    monkeypatch.setattr(audiosource, "_soundcard", lambda: None)

    assert audiosource.available_sources() == []
    assert audiosource.default_source() is None

    worker = audiosource.AudioCaptureWorker(QUELLE)
    with qtbot.waitSignal(worker.failed, timeout=2000) as signal:
        worker.start()
    assert signal.args == [MISSING_PACKAGE]
    worker.wait(2000)


def test_einkanalige_quelle_wird_auf_beide_seiten_gelegt():
    mono = np.array([[0.1], [0.2], [0.3]])
    links, rechts = audiosource.split_channels(mono)
    assert np.array_equal(links, rechts)

    flach = np.array([0.1, 0.2, 0.3])
    links, rechts = audiosource.split_channels(flach)
    assert links is flach and rechts is flach

    stereo = np.array([[0.1, 0.9], [0.2, 0.8]])
    links, rechts = audiosource.split_channels(stereo)
    assert list(links) == [0.1, 0.2] and list(rechts) == [0.9, 0.8]


def test_mittelung_beruhigt_das_bild(qtbot):
    """Mit AVERAGE > 1 zählt nicht nur der letzte Block."""
    spectrum = make(qtbot)
    assert spectrum.AVERAGE >= 2
    treffer = band_fuer(spectrum, 1000.0)

    fuettern(spectrum, sinus(1000.0), stille())
    laut = spectrum._measured[0][treffer]
    assert laut > 0.5

    # Ein einzelner stiller Block zieht den Wert nur anteilig herunter.
    spectrum.feed(stille(), stille())
    dazwischen = spectrum._measured[0][treffer]
    assert 0.0 < dazwischen < laut
    assert dazwischen > laut / spectrum.AVERAGE - 0.01

    # Erst wenn alle Blöcke still sind, ist auch der Mittelwert unten.
    fuettern(spectrum, stille(), stille())
    assert spectrum._measured[0][treffer] == 0.0


def test_ohne_mittelung_zaehlt_nur_der_letzte_block(qtbot):
    class Sofort(HaloSpectrum):
        AVERAGE = 1

    spectrum = Sofort()
    qtbot.addWidget(spectrum)
    spectrum.show()
    qtbot.waitExposed(spectrum)
    treffer = band_fuer(spectrum, 1000.0)

    spectrum.feed(sinus(1000.0), stille())
    assert spectrum._measured[0][treffer] > 0.5
    spectrum.feed(stille(), stille())
    assert spectrum._measured[0][treffer] == 0.0


def test_pegelanzeige_zeigt_lautstaerke_und_balance(qtbot, paint):
    spectrum = make(qtbot)
    assert spectrum.meters() == (0.0, 0.0)

    # Links laut, rechts leise — das muss man an den Pegelbalken sehen.
    fuettern(spectrum, sinus(1000.0, amplitude=0.8), sinus(1000.0, amplitude=0.05))
    qtbot.waitUntil(lambda: spectrum.meters()[0] > 0.5, timeout=2000)
    links, rechts = spectrum.meters()
    assert links > rechts + 0.2
    paint(spectrum)

    # Der Spitzenwert steht über der Lautstärke: er folgt dem lautesten Wert
    # im Block, nicht dem Effektivwert.
    assert spectrum.meter_peaks()[0] > links

    fuettern(spectrum, stille(), stille())
    qtbot.waitUntil(lambda: spectrum.meters()[0] < 0.05, timeout=3000)
    qtbot.waitUntil(lambda: spectrum.meter_peaks()[0] < 0.5, timeout=4000)
    paint(spectrum)


def test_pegelanzeige_laesst_sich_abschalten(qtbot, paint):
    class OhnePegel(HaloSpectrum):
        METER_W = 0

    mit = make(qtbot)
    ohne = OhnePegel()
    ohne.resize(420, 160)
    qtbot.addWidget(ohne)
    ohne.show()
    qtbot.waitExposed(ohne)

    # Ohne Pegelbalken bleibt mehr Platz für das Spektrum.
    assert ohne._plot_rect().width() > mit._plot_rect().width()
    paint(ohne)
