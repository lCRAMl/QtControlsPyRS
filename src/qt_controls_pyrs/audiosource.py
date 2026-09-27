# audiosource.py
#
# Tonquellen und die Aufnahme im Hintergrund — die Zulieferung für
# HaloSpectrum. Unter Windows kann `soundcard` jede Ausgabe als Loopback
# aufnehmen: damit hört das Spektrum den Systemton mit, ohne dass in Windows
# „Stereomix" freigeschaltet sein muss. Eingänge (Mikrofon, Line-In) gehen
# genauso.
#
# `soundcard` wird erst beim Zugriff geladen, nicht beim Import. Fehlt das
# Paket, bleibt alles Übrige benutzbar: `available_sources()` liefert dann
# eine leere Liste, und der Worker meldet es über sein `failed`-Signal.

from __future__ import annotations

from dataclasses import dataclass

from PyQt6.QtCore import QThread, pyqtSignal as Signal

MISSING_PACKAGE = (
    "Für die Tonaufnahme fehlt das Paket soundcard — "
    "nachzuinstallieren mit: pip install qt-controls-pyrs[audio]"
)


@dataclass(frozen=True)
class AudioSource:
    """Eine Tonquelle, wie sie in einer Auswahlliste stehen kann."""

    name: str          # was der Anwender liest
    device_id: str     # womit soundcard das Gerät wiederfindet
    loopback: bool     # True: eine Ausgabe wird mitgehört (Systemton)


def _soundcard():
    """Das Paket `soundcard`, oder None, wenn es fehlt oder nicht lädt."""
    try:
        import soundcard
    except Exception:
        # Nicht nur ImportError: auf Rechnern ohne Tonausgabe scheitert schon
        # das Laden der Systembibliothek.
        return None
    return soundcard


def available_sources() -> list[AudioSource]:
    """Alle Quellen: zuerst die Ausgaben zum Mithören, dann die Eingänge."""
    soundcard = _soundcard()
    if soundcard is None:
        return []

    sources: list[AudioSource] = []
    try:
        for speaker in soundcard.all_speakers():
            sources.append(AudioSource(f"{speaker.name} (Systemton)", str(speaker.id), True))
        for microphone in soundcard.all_microphones(include_loopback=False):
            sources.append(AudioSource(microphone.name, str(microphone.id), False))
    except Exception:
        # Geräteliste nicht lesbar (etwa ohne Tondienst) — dann eben keine.
        return []
    return sources


def default_source() -> AudioSource | None:
    """Der Systemton: die Standard-Ausgabe, mitgehört. None, wenn es keine gibt."""
    soundcard = _soundcard()
    if soundcard is None:
        return None
    try:
        speaker = soundcard.default_speaker()
    except Exception:
        return None
    if speaker is None:
        return None
    return AudioSource(f"{speaker.name} (Systemton)", str(speaker.id), True)


def split_channels(block):
    """Aus einem Aufnahmeblock den linken und den rechten Kanal holen.

    Eine einkanalige Quelle liefert zweimal dasselbe — dann sieht das Spektrum
    links und rechts gleich aus, was ehrlicher ist als eine leere Hälfte.
    """
    if block.ndim == 1:
        return block, block
    if block.shape[1] == 1:
        single = block[:, 0]
        return single, single
    return block[:, 0], block[:, 1]


class AudioCaptureWorker(QThread):
    """Nimmt in einem eigenen Thread auf und schickt jeden Block weiter.

    `block` liefert zwei numpy-Arrays: den linken und den rechten Kanal.
    Geht etwas schief, kommt `failed` mit dem Grund, und der Thread endet —
    ein Fehler in der Aufnahme darf das Programm nicht mitreißen.
    """

    block = Signal(object, object)
    failed = Signal(str)

    def __init__(
        self, source: AudioSource, samplerate: int = 44100, block_size: int = 2048,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._source = source
        self._samplerate = samplerate
        self._block_size = block_size
        self._running = False

    def source(self) -> AudioSource:
        return self._source

    def stop(self) -> None:
        """Beendet die Aufnahme, sobald der laufende Block da ist."""
        self._running = False

    def run(self) -> None:
        soundcard = _soundcard()
        if soundcard is None:
            self.failed.emit(MISSING_PACKAGE)
            return

        self._running = True
        try:
            microphone = soundcard.get_microphone(
                self._source.device_id, include_loopback=self._source.loopback
            )
            with microphone.recorder(
                samplerate=self._samplerate, blocksize=self._block_size
            ) as recorder:
                while self._running:
                    data = recorder.record(numframes=self._block_size)
                    left, right = split_channels(data)
                    self.block.emit(left, right)
        except Exception as error:
            self.failed.emit(f"Aufnahme fehlgeschlagen: {error}")
        finally:
            self._running = False
