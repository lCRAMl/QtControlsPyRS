# imgbb.py

from __future__ import annotations

import base64
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Callable

import requests
from PyQt6.QtCore import QThread, pyqtSignal as Signal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Eigene Fehlerklassen – damit Aufrufer gezielt fangen können
# ---------------------------------------------------------------------------

class ImgBBError(Exception):
    """Basisklasse für alle ImgBB-Fehler."""


class ImgBBFileNotFoundError(ImgBBError):
    """Die zu uploadende Datei existiert nicht."""


class ImgBBNetworkError(ImgBBError):
    """Netzwerk- oder HTTP-Fehler beim Upload."""


class ImgBBApiError(ImgBBError):
    """ImgBB hat einen API-seitigen Fehler zurückgemeldet."""


# ---------------------------------------------------------------------------
# Result-Typ statt rohem dict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class UploadResult:
    display_url: str
    delete_url: str | None = None


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

def _shorten(text: str, limit: int = 300) -> str:
    """Kürzt lange Antworten für die Fehlermeldung."""
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + " …"


class ImgBBClient:
    """Lädt Bilder zu ImgBB hoch.

    Upload-URL und Zeitlimit gibt das Programm vor (bei APIImageGenerator aus
    dessen config.ini); ohne Angabe gelten UPLOAD_ENDPOINT und DEFAULT_TIMEOUT.
    """

    UPLOAD_ENDPOINT = "https://api.imgbb.com/1/upload"
    DEFAULT_TIMEOUT = 30  # Sekunden, je Netzwerkschritt (Verbinden, Senden, Antwort)

    def __init__(
        self,
        api_key: str,
        timeout: float = DEFAULT_TIMEOUT,
        upload_endpoint: str = UPLOAD_ENDPOINT,
    ) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.upload_endpoint = upload_endpoint

    def upload_image(
        self,
        local_path: str,
        progress_callback: Callable[[float], None] | None = None,
    ) -> UploadResult:
        """Lädt ein Bild auf ImgBB hoch und gibt das Ergebnis zurück.

        Die Fehlermeldungen sind mehrzeilig: oben, was schiefging, darunter
        Datei, Ziel, Zeitlimit, Dauer und die technische Ursache. Der API-Key
        steht nie darin.

        Args:
            local_path:         Dateipfad des lokalen Bildes.
            progress_callback:  Optionaler Callback mit Fortschritt [0.0 - 1.0].

        Raises:
            ImgBBFileNotFoundError: Datei nicht gefunden.
            ImgBBNetworkError:      Netzwerk- oder HTTP-Fehler.
            ImgBBApiError:          API-seitiger Fehler.
        """
        if not os.path.isfile(local_path):
            raise ImgBBFileNotFoundError(f"Datei nicht gefunden: {local_path}")

        # Datei chunk-weise Base64-kodieren, um RAM-Verbrauch zu begrenzen
        encoded_string = self._encode_file(local_path)

        if progress_callback:
            progress_callback(0.1)  # Kodierung abgeschlossen

        data = {
            "key": self.api_key,
            "image": encoded_string,
        }

        started = time.monotonic()
        try:
            response = requests.post(
                self.upload_endpoint,
                data=data,
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            elapsed_s = time.monotonic() - started
            details = self._upload_details(local_path, len(encoded_string), elapsed_s)
            raise ImgBBNetworkError(self._network_error_text(exc, details)) from exc
        elapsed_s = time.monotonic() - started

        if progress_callback:
            progress_callback(0.9)  # HTTP-Request abgeschlossen

        details = self._upload_details(local_path, len(encoded_string), elapsed_s)

        # HTTP-Fehler: die Fehlermeldung von ImgBB gehört in die erste Zeile,
        # die rohe Antwort nur weiter unten. Eine HTML-Fehlerseite in der
        # ersten Zeile würde ein QLabel als Rich Text deuten und verstümmeln.
        if response.status_code != 200:
            message = ""
            try:
                body = response.json()
                message = str(body.get("error", {}).get("message", ""))
            except (ValueError, AttributeError):
                pass
            first_line = f"HTTP {response.status_code} {response.reason}"
            if message:
                first_line += f": {_shorten(message)}"
            lines = [first_line]
            lines += details
            lines.append(f"Antwort: {_shorten(response.text)}")
            raise ImgBBNetworkError("\n".join(lines))

        try:
            result = response.json()
        except ValueError as exc:
            lines = ["ImgBB hat mit HTTP 200 geantwortet, aber kein JSON geliefert."]
            lines += details
            lines.append(f"Antwort: {_shorten(response.text)}")
            raise ImgBBApiError("\n".join(lines)) from exc

        if not result.get("success"):
            lines = ["ImgBB meldet einen Fehler (success = false)."]
            lines += details
            lines.append(f"Antwort: {_shorten(str(result))}")
            raise ImgBBApiError("\n".join(lines))

        return UploadResult(
            display_url=result["data"]["display_url"],
            delete_url=result["data"].get("delete_url"),
        )

    # ------------------------------------------------------------------
    # Fehlertexte
    # ------------------------------------------------------------------

    def _upload_details(self, local_path: str, payload_size: int, elapsed_s: float) -> list[str]:
        """Die Zeilen, die zu jeder Upload-Fehlermeldung gehören."""
        file_mb = os.path.getsize(local_path) / 1_000_000
        payload_mb = payload_size / 1_000_000
        return [
            f"Datei: {os.path.basename(local_path)} ({file_mb:.1f} MB, gesendet als "
            f"Base64 {payload_mb:.1f} MB)",
            f"Ziel: {self.upload_endpoint}",
            f"Zeitlimit: {self.timeout:g} s je Netzwerkschritt, Dauer bis zum Fehler: {elapsed_s:.1f} s",
        ]

    def _network_error_text(self, exc: requests.exceptions.RequestException, details: list[str]) -> str:
        """Mehrzeilige Meldung zu einem Fehler, bei dem keine Antwort ankam."""
        # ConnectTimeout ist zugleich ein ConnectionError — deshalb zuerst prüfen.
        if isinstance(exc, requests.exceptions.ConnectTimeout):
            summary = (
                f"Upload-Timeout: keine Verbindung zum Server innerhalb von {self.timeout:g} s."
            )
        elif isinstance(exc, requests.exceptions.ReadTimeout):
            summary = (
                f"Upload-Timeout: der Server hat nicht innerhalb von {self.timeout:g} s geantwortet."
            )
        elif isinstance(exc, requests.exceptions.Timeout):
            summary = f"Upload-Timeout überschritten ({self.timeout:g} s)."
        elif isinstance(exc, requests.exceptions.ConnectionError):
            summary = "Verbindungsfehler beim Upload."
        else:
            summary = "Netzwerkfehler beim Upload."

        lines = [summary]
        lines += details
        lines.append(f"Ursache: {type(exc).__name__}: {exc}")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Hilfsmethoden
    # ------------------------------------------------------------------

    @staticmethod
    def _encode_file(path: str, chunk_size: int = 65_536) -> str:
        """Liest eine Datei chunk-weise ein und gibt Base64-kodierten String zurueck."""
        chunks: list[bytes] = []
        with open(path, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)
        return base64.b64encode(b"".join(chunks)).decode("utf-8")


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class ImgBBUploadWorker(QThread):
    """QThread, der einen ImgBB-Upload asynchron durchfuehrt.

    Signals:
        progress(float):  Fortschritt 0.0 - 1.0.
        finished(str):    Display-URL nach erfolgreichem Upload.
        error(str):       Fehlermeldung bei Misserfolg.
    """

    progress = Signal(float)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, client: ImgBBClient, local_path: str) -> None:
        super().__init__()
        self.client = client
        self.local_path = local_path
        self._cancel_event = threading.Event()

    def cancel(self) -> None:
        """Signalisiert dem Worker, den Upload abzubrechen."""
        self._cancel_event.set()

    def run(self) -> None:
        self.progress.emit(0.0)

        if self._cancel_event.is_set():
            return

        def _progress_callback(value: float) -> None:
            if not self._cancel_event.is_set():
                self.progress.emit(value)

        try:
            result = self.client.upload_image(
                self.local_path,
                progress_callback=_progress_callback,
            )

            if self._cancel_event.is_set():
                return

            self.progress.emit(1.0)
            self.finished.emit(result.display_url)

        except ImgBBFileNotFoundError as exc:
            logger.error("Datei nicht gefunden: %s", exc)
            self.error.emit(str(exc))
        except ImgBBNetworkError as exc:
            logger.error("Netzwerkfehler beim Upload: %s", exc)
            self.error.emit(str(exc))
        except ImgBBApiError as exc:
            logger.error("ImgBB API-Fehler: %s", exc)
            self.error.emit(str(exc))
        except Exception as exc:
            logger.exception("Unerwarteter Fehler beim Upload: %s", exc)
            self.error.emit(f"Unerwarteter Fehler: {exc}")
