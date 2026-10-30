import pytest
import requests

from qt_controls_pyrs import imgbb
from qt_controls_pyrs.imgbb import ImgBBApiError, ImgBBClient, ImgBBNetworkError


@pytest.fixture
def bild(tmp_path):
    pfad = tmp_path / "referenz.png"
    pfad.write_bytes(b"\x89PNG" + b"\x00" * 2_000_000)   # 2 MB
    return str(pfad)


class Antwort:
    def __init__(self, status_code=200, body=None, text="", reason="OK"):
        self.status_code = status_code
        self.reason = reason
        self._body = body
        self.text = text or (str(body) if body is not None else "")

    def json(self):
        if self._body is None:
            raise ValueError("kein JSON")
        return self._body


def test_url_und_zeitlimit_kommen_von_aussen(monkeypatch, bild):
    gesendet = {}

    def post(url, data, timeout):
        gesendet.update(url=url, timeout=timeout, key=data["key"])
        return Antwort(body={"success": True, "data": {"display_url": "https://i.ibb.co/x.png"}})

    monkeypatch.setattr(imgbb.requests, "post", post)
    client = ImgBBClient("geheim", timeout=75, upload_endpoint="https://example.org/upload")
    assert client.upload_image(bild).display_url == "https://i.ibb.co/x.png"
    assert gesendet == {"url": "https://example.org/upload", "timeout": 75, "key": "geheim"}


def test_voreinstellungen_bleiben():
    client = ImgBBClient("k")
    assert client.upload_endpoint == ImgBBClient.UPLOAD_ENDPOINT == "https://api.imgbb.com/1/upload"
    assert client.timeout == ImgBBClient.DEFAULT_TIMEOUT == 30


def werfe(exc):
    def post(*args, **kwargs):
        raise exc
    return post


@pytest.mark.parametrize("fehler, erste_zeile", [
    (requests.exceptions.ReadTimeout("Read timed out. (read timeout=45)"),
     "Upload-Timeout: der Server hat nicht innerhalb von 45 s geantwortet."),
    (requests.exceptions.ConnectTimeout("Connect timed out"),
     "Upload-Timeout: keine Verbindung zum Server innerhalb von 45 s."),
    (requests.exceptions.ConnectionError("Name or service not known"),
     "Verbindungsfehler beim Upload."),
])
def test_netzwerkfehler_sind_ausfuehrlich(monkeypatch, bild, fehler, erste_zeile):
    monkeypatch.setattr(imgbb.requests, "post", werfe(fehler))
    client = ImgBBClient("geheim", timeout=45, upload_endpoint="https://example.org/upload")
    with pytest.raises(ImgBBNetworkError) as info:
        client.upload_image(bild)

    zeilen = str(info.value).splitlines()
    assert zeilen[0] == erste_zeile
    text = str(info.value)
    assert "Datei: referenz.png (2.0 MB, gesendet als Base64 2.7 MB)" in text
    assert "Ziel: https://example.org/upload" in text
    assert "Zeitlimit: 45 s je Netzwerkschritt, Dauer bis zum Fehler:" in text
    assert f"Ursache: {type(fehler).__name__}: {fehler}" in text
    assert "Hinweis:" in text
    assert "geheim" not in text            # der API-Key steht nie in der Meldung


def test_timeout_hinweis_nennt_die_einstellung(monkeypatch, bild):
    monkeypatch.setattr(imgbb.requests, "post", werfe(requests.exceptions.ReadTimeout("x")))
    with pytest.raises(ImgBBNetworkError, match="upload_timeout_s in der config.ini"):
        ImgBBClient("k").upload_image(bild)


def test_http_fehler_mit_status_und_antwort(monkeypatch, bild):
    antwort = Antwort(400, body={"error": {"message": "Invalid API v1 key."}}, reason="Bad Request")
    monkeypatch.setattr(imgbb.requests, "post", lambda *a, **k: antwort)
    with pytest.raises(ImgBBNetworkError) as info:
        ImgBBClient("k").upload_image(bild)
    zeilen = str(info.value).splitlines()
    assert zeilen[0] == "HTTP 400 Bad Request: Invalid API v1 key."
    assert any(z.startswith("Antwort: ") for z in zeilen)


def test_antwort_ohne_json(monkeypatch, bild):
    monkeypatch.setattr(imgbb.requests, "post", lambda *a, **k: Antwort(200, text="<html>Wartung</html>"))
    with pytest.raises(ImgBBApiError, match="kein JSON"):
        ImgBBClient("k").upload_image(bild)


def test_api_meldet_misserfolg(monkeypatch, bild):
    monkeypatch.setattr(imgbb.requests, "post", lambda *a, **k: Antwort(200, body={"success": False}))
    with pytest.raises(ImgBBApiError, match="success = false"):
        ImgBBClient("k").upload_image(bild)


def test_lange_antworten_werden_gekuerzt(monkeypatch, bild):
    antwort = Antwort(500, text="x" * 5000, reason="Internal Server Error")
    monkeypatch.setattr(imgbb.requests, "post", lambda *a, **k: antwort)
    with pytest.raises(ImgBBNetworkError) as info:
        ImgBBClient("k").upload_image(bild)
    assert len(str(info.value)) < 1200


def test_html_fehlerseite_steht_nicht_in_der_ersten_zeile(monkeypatch, bild):
    """Ein QLabel deutet Tags in der ersten Zeile als Rich Text."""
    antwort = Antwort(503, text="<html><body>Wartung</body></html>", reason="Service Unavailable")
    monkeypatch.setattr(imgbb.requests, "post", lambda *a, **k: antwort)
    with pytest.raises(ImgBBNetworkError) as info:
        ImgBBClient("k").upload_image(bild)
    zeilen = str(info.value).splitlines()
    assert zeilen[0] == "HTTP 503 Service Unavailable"
    assert "Antwort: <html><body>Wartung</body></html>" in zeilen
