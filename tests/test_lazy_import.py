import subprocess
import sys


def _run(code: str) -> str:
    # Eigener Prozess: in diesem hier haben andere Tests requests längst geladen.
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            timeout=60, check=True)
    return result.stdout.strip()


def test_paketimport_laedt_requests_nicht():
    assert _run("import sys, qt_controls_pyrs; print('requests' in sys.modules)") == "False"


def test_upload_teile_kommen_beim_ersten_zugriff():
    out = _run(
        "import sys\n"
        "from qt_controls_pyrs import ReferenceThumb, ImgBBClient\n"
        "print(ReferenceThumb.__name__, ImgBBClient.__name__, 'requests' in sys.modules)"
    )
    assert out == "ReferenceThumb ImgBBClient True"


def test_alle_exportierten_namen_sind_erreichbar():
    import qt_controls_pyrs

    fehlend = [name for name in qt_controls_pyrs.__all__ if not hasattr(qt_controls_pyrs, name)]
    assert fehlend == []
    assert "ReferenceThumb" in dir(qt_controls_pyrs)


def test_unbekannter_name_meldet_attributeerror():
    import pytest
    import qt_controls_pyrs

    with pytest.raises(AttributeError):
        qt_controls_pyrs.GibtEsNicht  # noqa: B018
