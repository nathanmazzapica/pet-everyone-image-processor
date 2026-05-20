import pytest
from unittest.mock import MagicMock, patch

from src.security.virus_scanner import VirusScanner, VirusScannerError

EICAR = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
CLEAN = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def test_clean_file_passes():
    scanner = VirusScanner()
    assert scanner.scan(CLEAN) is True


def test_eicar_detected():
    scanner = VirusScanner()
    assert scanner.scan(EICAR) is False


def test_connection_error_on_init_raises_scanner_error():
    with patch("src.security.virus_scanner.pyclamd.ClamdUnixSocket", side_effect=ConnectionError):
        with pytest.raises(VirusScannerError):
            VirusScanner()


def test_connection_error_on_scan_raises_scanner_error():
    with patch("src.security.virus_scanner.pyclamd.ClamdUnixSocket") as mock_clamd:
        mock_clamd.return_value = MagicMock(scan_stream=MagicMock(side_effect=ConnectionError))
        scanner = VirusScanner()

    with pytest.raises(VirusScannerError):
        scanner.scan(CLEAN)
