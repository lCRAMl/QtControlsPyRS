# halospectrum.py
#
# Echtzeit-Spektrum im Halo-Stil: ein feiner weißer Rahmen, innen der
# Fensterhintergrund. In der Mitte liegen 0 Hz — nach links wächst die
# Frequenz des linken Kanals, nach rechts die des rechten. Die Bänder sind
# logarithmisch geteilt, jede Oktave bekommt also gleich viel Platz.
#
# Die Aufnahme läuft in einem eigenen Thread (audiosource.py) und schiebt ihre
# Blöcke mit `feed()` herein; gerechnet wird die FFT im GUI-Thread, für 2048
# Werte sind das mit numpy ein paar Dutzend Mikrosekunden. Geglättet und
# gezeichnet wird in einem festen Bildtakt, damit die Balken auch dann ruhig
# absinken, wenn gerade keine Blöcke kommen.
#
# Dieses Modul braucht numpy (und für die Aufnahme soundcard), der Rest der
# Sammlung nicht. Deshalb wird es nicht über `qt_controls_pyrs` mitgeladen,
# sondern eigens importiert:
#
#     from qt_controls_pyrs.halospectrum import HaloSpectrum

from __future__ import annotations

import math
import time

import numpy as np
from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal as Signal
from PyQt6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPalette, QPen
from PyQt6.QtWidgets import QWidget

from .audiosource import AudioCaptureWorker, AudioSource, available_sources, default_source
from .buttons.hoverbuttons import _crisp, _faded, _outline


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


class HaloSpectrum(QWidget):
    """Spektrum-Anzeige: links der linke Kanal, rechts der rechte, 0 Hz in der Mitte.

    Starten und stoppen:

        spectrum = HaloSpectrum()
        spectrum.start()                       # Systemton mithören
        spectrum.start(quelle)                 # oder eine bestimmte Quelle
        spectrum.stop()

    `available_sources()` aus `qt_controls_pyrs.audiosource` liefert die Liste
    für ein Auswahlfeld. Wer den Ton anderswoher hat, ruft einfach `feed(links,
    rechts)` mit zwei Blöcken auf — die Aufnahme ist dafür nicht nötig.

    Jedes Band steigt schnell und fällt ruhig (`ATTACK_MS`, `RELEASE_MS`), und
    über jedem steht ein Spitzenwert, der kurz hält und dann absinkt. Kommt
    kein Ton, sinkt alles auf die Grundlinie ab, die immer zu sehen bleibt.
    """

    # Die Aufnahme ging schief (Paket fehlt, Gerät weg) — mit Grund.
    failed = Signal(str)

    # --- Rahmen, wie bei den anderen Halo-Widgets ---
    ROOM          = 16      # Rand links und rechts
    ROOM_Y        = 4       # Rand oben und unten
    PAD           = 10      # Abstand der Balken zum Rahmen
    RADIUS        = 0       # Eckenradius
    OUTLINE_ALPHA = 0.5     # Deckkraft des weißen Rahmens

    # --- Bänder ---
    BANDS      = 72         # Bänder je Kanal
    FREQ_MIN   = 40.0       # linkes Ende: die tiefste gezeigte Frequenz
    FREQ_MAX   = 18000.0    # äußeres Ende: die höchste
    DB_FLOOR   = -60.0      # dieser Pegel ist ein leerer Balken
    DB_CEILING = -16.0       # ... und dieser ein voller

    # --- Aufnahme ---
    SAMPLERATE = 44100      # Abtastrate
    BLOCK      = 2048       # Werte je Block; bestimmt die Auflösung der FFT
    AVERAGE    = 1          # so viele Blöcke werden gemittelt (1 = jeder für sich)

    # --- Pegelanzeige je Kanal, ganz außen ---
    METER_W          = 6      # Breite des Pegelbalkens (0 = keine Anzeige)
    METER_GAP        = 8      # Abstand zwischen Pegelbalken und Spektrum
    METER_DB_FLOOR   = -40.0  # so leise ist der Balken leer
    METER_DB_CEILING = -6.0    # ... und so laut ist er voll (Aussteuerungsgrenze)

    # --- Bewegung ---
    FRAME_MS     = 16       # Bildtakt
    ATTACK_MS    = 60       # so schnell steigt ein Balken
    RELEASE_MS   = 320      # ... und so ruhig fällt er
    PEAK_HOLD_MS = 800      # so lange steht der Spitzenwert still
    PEAK_FALL_S  = 0.9      # danach sinkt er um diesen Anteil je Sekunde

    # --- Aussehen ---
    BAR_GAP     = 2         # Abstand zwischen zwei Balken
    BAR_MIN_W   = 2.0       # so schmal wird ein Balken höchstens
    CENTER_GAP  = 10        # Lücke zwischen den beiden Kanälen (0 Hz)
    PEAK_HEIGHT = 2.0       # Dicke des Spitzenwert-Strichs
    COLOR_LOW   = "#9C9C9C"  # Farbe am Fuß des Balkens
    COLOR_HIGH  = "#ffffff"  # ... und an der Spitze
    PEAK_ALPHA  = 0.75      # Deckkraft des Spitzenwert-Strichs
    FLOOR_ALPHA = 0.30      # Grundlinie unter den Balken
    TICK_ALPHA  = 0.16      # Markierungen und Mittellinie
    LABEL_HZ    = (100, 1000, 10000)   # dort stehen Markierung und Beschriftung
    LABEL_H     = 13        # Streifen am Boden für die Beschriftung (0 = keine)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Je Kanal ein Wert pro Band: zuletzt gemessen, geglättet, Spitzenwert
        # und wie lange dieser schon steht.
        self._measured = [self._zeros(), self._zeros()]
        self._level = [self._zeros(), self._zeros()]
        self._peak = [self._zeros(), self._zeros()]
        self._peak_age = [self._zeros(), self._zeros()]

        # Die letzten Blöcke je Kanal, für die Mittelung.
        self._history: list[list[list[float]]] = [[], []]

        # Pegelanzeige je Kanal: Lautstärke (Effektivwert) und der lauteste
        # Wert im Block, jeweils gemessen, geglättet und als Spitzenwert.
        self._measured_loudness = [0.0, 0.0]
        self._measured_top = [0.0, 0.0]
        self._meter = [0.0, 0.0]
        self._meter_peak = [0.0, 0.0]
        self._meter_peak_age = [0.0, 0.0]

        self._low_color = QColor(self.COLOR_LOW)
        self._high_color = QColor(self.COLOR_HIGH)

        self._worker: AudioCaptureWorker | None = None
        self._source: AudioSource | None = None

        # Die Zuordnung Band -> FFT-Werte hängt nur an der Blockgröße; sie
        # wird gemerkt, statt in jedem Block neu gerechnet zu werden.
        self._edges: list[tuple[int, int]] = []
        self._edges_key: tuple[int, int] | None = None

        self._last_frame = time.perf_counter()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_frame)

    def _zeros(self) -> list[float]:
        return [0.0] * self.BANDS

    def sizeHint(self) -> QSize:
        return QSize(420, 160)

    def minimumSizeHint(self) -> QSize:
        return QSize(160, 80)

    # ==============================
    # Aufnahme
    # ==============================

    def start(self, source: AudioSource | None = None) -> None:
        """Beginnt aufzunehmen. Ohne Angabe wird der Systemton mitgehört."""
        self.stop()

        if source is None:
            source = default_source()
        if source is None:
            self.failed.emit(
                "Keine Tonquelle gefunden. "
                f"Verfügbar sind: {len(available_sources())} Geräte."
            )
            return

        self._source = source
        self._worker = AudioCaptureWorker(source, self.SAMPLERATE, self.BLOCK, self)
        self._worker.block.connect(self.feed)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.start()

    def stop(self) -> None:
        """Beendet die Aufnahme und wartet, bis der Thread wirklich steht."""
        if self._worker is None:
            return
        self._worker.stop()
        self._worker.wait(2000)
        self._worker = None
        self._source = None

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def source(self) -> AudioSource | None:
        """Die Quelle, von der gerade aufgenommen wird."""
        return self._source

    def _on_worker_failed(self, message: str) -> None:
        self._worker = None
        self._source = None
        self.failed.emit(message)

    # ==============================
    # Messen
    # ==============================

    def feed(self, left, right) -> None:
        """Einen Aufnahmeblock verarbeiten: Bänder, Lautstärke und Spitze."""
        for channel, samples in ((0, left), (1, right)):
            block = np.asarray(samples, dtype=float).ravel()
            self._measured[channel] = self._averaged(channel, self._band_levels(block))
            self._measured_loudness[channel] = self._loudness(block)
            self._measured_top[channel] = self._top(block)

    def meters(self) -> tuple[float, float]:
        """Die Lautstärke links und rechts, 0 bis 1 — wie die Pegelbalken sie zeigen."""
        return self._meter[0], self._meter[1]

    def meter_peaks(self) -> tuple[float, float]:
        return self._meter_peak[0], self._meter_peak[1]

    def _averaged(self, channel: int, levels: list[float]) -> list[float]:
        """Die letzten AVERAGE Blöcke mitteln — das nimmt dem Bild das Zappeln."""
        history = self._history[channel]
        history.append(levels)
        while len(history) > max(1, self.AVERAGE):
            history.pop(0)
        if len(history) == 1:
            return list(levels)
        return [sum(values) / len(values) for values in zip(*history)]

    def _loudness(self, block) -> float:
        """Die Lautstärke des Blocks als Effektivwert, 0 bis 1."""
        if block.size == 0:
            return 0.0
        rms = float(np.sqrt(np.mean(block * block)))
        return self._as_share(rms, self.METER_DB_FLOOR, self.METER_DB_CEILING)

    def _top(self, block) -> float:
        """Der lauteste Wert im Block; 1.0 heißt: an der Aussteuerungsgrenze."""
        if block.size == 0:
            return 0.0
        return self._as_share(
            float(np.abs(block).max()), self.METER_DB_FLOOR, self.METER_DB_CEILING
        )

    @staticmethod
    def _as_share(amplitude: float, floor_db: float, ceiling_db: float) -> float:
        """Eine Amplitude in einen Anteil zwischen 0 und 1 umrechnen, über dB."""
        decibel = 20.0 * math.log10(amplitude + 1e-9)
        return _clamp((decibel - floor_db) / (ceiling_db - floor_db))

    def levels(self) -> tuple[list[float], list[float]]:
        """Die geglätteten Pegel, 0 bis 1, wie sie gerade gezeichnet werden."""
        return list(self._level[0]), list(self._level[1])

    def peaks(self) -> tuple[list[float], list[float]]:
        return list(self._peak[0]), list(self._peak[1])

    def band_frequencies(self) -> list[float]:
        """Die Mittenfrequenz jedes Bandes, von innen nach außen."""
        step = self._band_step()
        return [self.FREQ_MIN * step ** (index + 0.5) for index in range(self.BANDS)]

    def _band_step(self) -> float:
        """Das Frequenzverhältnis von einem Band zum nächsten."""
        return (self.FREQ_MAX / self.FREQ_MIN) ** (1.0 / self.BANDS)

    def _band_levels(self, block) -> list[float]:
        """FFT eines Blocks, daraus je Band ein Pegel zwischen 0 und 1."""
        if block.size < 16:
            return self._zeros()

        window = np.hanning(block.size)
        spectrum = np.abs(np.fft.rfft(block * window)) * (2.0 / window.sum())

        levels = []
        for start, end in self._band_edges(block.size):
            loudest = float(spectrum[start:end].max()) if end > start else 0.0
            levels.append(self._as_share(loudest, self.DB_FLOOR, self.DB_CEILING))
        return levels

    def _band_edges(self, block_size: int) -> list[tuple[int, int]]:
        """Welche FFT-Werte in welches Band fallen — logarithmisch geteilt."""
        key = (block_size, self.SAMPLERATE)
        if key == self._edges_key:
            return self._edges

        bin_width = self.SAMPLERATE / block_size
        last_bin = block_size // 2 + 1
        step = self._band_step()
        edges: list[tuple[int, int]] = []

        for index in range(self.BANDS):
            low = self.FREQ_MIN * step ** index
            high = low * step
            # Der erste Wert (0 Hz, Gleichanteil) bleibt außen vor. Für tiefe
            # Bänder, die schmaler sind als ein FFT-Wert, bleibt ein Wert
            # übrig — sonst wären sie immer leer.
            start = max(1, int(low / bin_width))
            end = max(start + 1, int(high / bin_width) + 1)
            edges.append((min(start, last_bin - 1), min(end, last_bin)))

        self._edges_key = key
        self._edges = edges
        return edges

    # ==============================
    # Bildtakt: glätten und Spitzenwerte
    # ==============================

    def _on_frame(self) -> None:
        now = time.perf_counter()
        dt = min(now - self._last_frame, 0.1)
        self._last_frame = now

        rise = self._share(dt, self.ATTACK_MS)
        fall = self._share(dt, self.RELEASE_MS)

        for channel in (0, 1):
            measured = self._measured[channel]
            level = self._level[channel]
            peak = self._peak[channel]
            age = self._peak_age[channel]

            for band in range(self.BANDS):
                level[band] = self._follow(level[band], measured[band], rise, fall)
                peak[band], age[band] = self._advance_peak(
                    peak[band], level[band], age[band], dt
                )

            # Die Pegelanzeige folgt genauso; ihr Spitzenwert hängt aber am
            # lautesten Wert des Blocks, nicht an der geglätteten Lautstärke.
            self._meter[channel] = self._follow(
                self._meter[channel], self._measured_loudness[channel], rise, fall
            )
            self._meter_peak[channel], self._meter_peak_age[channel] = self._advance_peak(
                self._meter_peak[channel], self._measured_top[channel],
                self._meter_peak_age[channel], dt,
            )

        self.update()

    @staticmethod
    def _follow(value: float, target: float, rise: float, fall: float) -> float:
        """Einen Wert nachziehen: schnell hinauf, ruhig hinunter."""
        share = rise if target > value else fall
        return value + (target - value) * share

    def _advance_peak(self, peak: float, level: float, age: float, dt: float) -> tuple[float, float]:
        """Den Spitzenwert nachziehen: mit nach oben, halten, dann absinken."""
        if level >= peak:
            return level, 0.0
        age += dt
        if age <= self.PEAK_HOLD_MS / 1000.0:
            return peak, age
        return max(level, peak - self.PEAK_FALL_S * dt), age

    @staticmethod
    def _share(dt: float, duration_ms: int) -> float:
        """Welcher Anteil des Wegs in dieser Zeitspanne zurückgelegt wird."""
        return 1.0 - math.exp(-dt * 1000.0 / max(1.0, float(duration_ms)))

    # ==============================
    # Farben
    # ==============================

    def colors(self) -> tuple[QColor, QColor]:
        return QColor(self._low_color), QColor(self._high_color)

    def setColors(self, low, high) -> None:
        """Der Farbverlauf der Balken: unten `low`, an der Spitze `high`."""
        self._low_color = QColor(low)
        self._high_color = QColor(high)
        self.update()

    # ==============================
    # Ereignisse
    # ==============================

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._last_frame = time.perf_counter()
        self._timer.start(self.FRAME_MS)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        # Unsichtbar muss nichts gezeichnet werden; die Aufnahme läuft weiter,
        # bis jemand stop() ruft.
        self._timer.stop()

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)

    # ==============================
    # Darstellung
    # ==============================

    def _ink(self) -> QColor:
        return self.palette().color(
            QPalette.ColorGroup.Normal, QPalette.ColorRole.ButtonText
        )

    def _frame_rect(self):
        """Die sichtbare Fläche: das Widget ohne den Rand für den Schein."""
        return self.rect().adjusted(self.ROOM, self.ROOM_Y, -self.ROOM, -self.ROOM_Y)

    def _plot_rect(self) -> QRectF:
        """Die Fläche, in der die Balken stehen.

        Abgezogen sind der Streifen für die Beschriftung unten und die beiden
        Pegelbalken außen.
        """
        inner = QRectF(self._frame_rect()).adjusted(
            self.PAD, self.PAD, -self.PAD, -self.PAD
        )
        inner = inner.adjusted(0.0, 0.0, 0.0, -float(self.LABEL_H))
        if self.METER_W > 0:
            side = float(self.METER_W + self.METER_GAP)
            inner = inner.adjusted(side, 0.0, -side, 0.0)
        return inner

    def _meter_rect(self, channel: int) -> QRectF:
        """Der Pegelbalken eines Kanals: links ganz außen, rechts ganz außen."""
        plot = self._plot_rect()
        width = float(self.METER_W)
        if channel == 0:
            left = plot.left() - self.METER_GAP - width
        else:
            left = plot.right() + self.METER_GAP
        return QRectF(left, plot.top(), width, plot.height())

    def _label_rect(self) -> QRectF:
        """Der Streifen darunter, in dem die Frequenzen stehen."""
        plot = self._plot_rect()
        return QRectF(plot.left(), plot.bottom(), plot.width(), float(self.LABEL_H))

    def _half_width(self, plot: QRectF) -> float:
        """Die Breite einer Kanalhälfte."""
        return max(0.0, (plot.width() - self.CENTER_GAP) / 2.0)

    def x_for_frequency(self, frequency: float, channel: int) -> float:
        """Wo eine Frequenz liegt. channel 0 ist links, 1 ist rechts."""
        plot = self._plot_rect()
        half = self._half_width(plot)
        span = math.log(self.FREQ_MAX / self.FREQ_MIN)
        share = _clamp(math.log(max(frequency, self.FREQ_MIN) / self.FREQ_MIN) / span)

        middle = plot.center().x()
        if channel == 0:
            return middle - self.CENTER_GAP / 2.0 - share * half
        return middle + self.CENTER_GAP / 2.0 + share * half

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        frame = QRectF(self._frame_rect())
        ink = self._ink()
        radius = float(self.RADIUS)

        painter.setPen(QPen(_faded(ink, self.OUTLINE_ALPHA), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        _outline(painter, _crisp(frame, 1.0), max(radius - 0.5, 0.0))

        plot = self._plot_rect()
        if plot.width() <= 0 or plot.height() <= 0:
            painter.end()
            return

        self._draw_scale(painter, plot, ink)
        self._draw_channel(painter, plot, channel=0)
        self._draw_channel(painter, plot, channel=1)
        if self.METER_W > 0:
            self._draw_meter(painter, channel=0, ink=ink)
            self._draw_meter(painter, channel=1, ink=ink)
        painter.end()

    def _draw_meter(self, painter: QPainter, channel: int, ink: QColor) -> None:
        """Der Pegelbalken eines Kanals: Lautstärke gefüllt, Spitze als Strich."""
        rect = self._meter_rect(channel)
        if rect.width() <= 0.0 or rect.height() <= 0.0:
            return

        painter.setPen(QPen(_faded(ink, self.TICK_ALPHA), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(_crisp(rect, 1.0))

        gradient = QLinearGradient(0.0, rect.bottom(), 0.0, rect.top())
        gradient.setColorAt(0.0, self._low_color)
        gradient.setColorAt(1.0, self._high_color)

        painter.setPen(Qt.PenStyle.NoPen)
        filled = self._meter[channel] * rect.height()
        if filled >= 1.0:
            painter.setBrush(QBrush(gradient))
            painter.drawRect(QRectF(rect.left(), rect.bottom() - filled, rect.width(), filled))

        top = self._meter_peak[channel] * rect.height()
        if top >= 1.0:
            painter.setBrush(QBrush(_faded(self._high_color, self.PEAK_ALPHA)))
            painter.drawRect(QRectF(
                rect.left(), rect.bottom() - top - self.PEAK_HEIGHT,
                rect.width(), self.PEAK_HEIGHT,
            ))

    def _draw_scale(self, painter: QPainter, plot: QRectF, ink: QColor) -> None:
        """Mittellinie, Markierungen und die Grundlinie, auf der alles steht."""
        painter.setPen(QPen(_faded(ink, self.TICK_ALPHA), 1.0))
        middle = plot.center().x()
        painter.drawLine(int(middle), int(plot.top()), int(middle), int(plot.bottom()))

        font = painter.font()
        font.setPointSizeF(max(6.0, font.pointSizeF() - 2.0))
        painter.setFont(font)
        strip = self._label_rect()

        for frequency in self.LABEL_HZ:
            if frequency >= self.FREQ_MAX:
                continue
            for channel in (0, 1):
                x = self.x_for_frequency(float(frequency), channel)
                painter.drawLine(int(x), int(plot.top()), int(x), int(plot.bottom()))
                if self.LABEL_H <= 0:
                    continue
                # Die Beschriftung steht unter der Grundlinie, damit kein
                # Balken sie zudeckt.
                label = QRectF(x - 20.0, strip.top(), 40.0, strip.height())
                painter.drawText(label, int(Qt.AlignmentFlag.AlignCenter), _hertz(frequency))

        # Die Grundlinie bleibt auch ohne Ton stehen.
        painter.setPen(QPen(_faded(ink, self.FLOOR_ALPHA), 1.0))
        painter.drawLine(
            int(plot.left()), int(plot.bottom()), int(plot.right()), int(plot.bottom())
        )

    def _draw_channel(self, painter: QPainter, plot: QRectF, channel: int) -> None:
        """Die Balken eines Kanals, von der Mitte nach außen."""
        half = self._half_width(plot)
        if half <= 0.0:
            return

        slot = half / self.BANDS
        width = max(self.BAR_MIN_W, slot - self.BAR_GAP)
        middle = plot.center().x()
        height = plot.height()
        floor = plot.bottom()

        gradient = QLinearGradient(0.0, floor, 0.0, plot.top())
        gradient.setColorAt(0.0, self._low_color)
        gradient.setColorAt(1.0, self._high_color)
        brush = QBrush(gradient)

        level = self._level[channel]
        peak = self._peak[channel]

        painter.setPen(Qt.PenStyle.NoPen)
        for band in range(self.BANDS):
            # Band 0 liegt an der Mitte, das letzte ganz außen.
            offset = self.CENTER_GAP / 2.0 + band * slot
            if channel == 0:
                left = middle - offset - width
            else:
                left = middle + offset

            bar_height = level[band] * height
            if bar_height >= 1.0:
                painter.setBrush(brush)
                painter.drawRect(QRectF(left, floor - bar_height, width, bar_height))

            peak_height = peak[band] * height
            if peak_height >= 1.0:
                painter.setBrush(QBrush(_faded(self._high_color, self.PEAK_ALPHA)))
                painter.drawRect(QRectF(
                    left, floor - peak_height - self.PEAK_HEIGHT, width, self.PEAK_HEIGHT
                ))


def _hertz(frequency: int) -> str:
    """100 bleibt 100, 1000 wird zu 1k."""
    if frequency < 1000:
        return str(frequency)
    return f"{frequency // 1000}k"
