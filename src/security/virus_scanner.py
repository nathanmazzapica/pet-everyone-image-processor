from typing import Any

import pyclamd

class VirusScannerError(Exception):
    pass

class VirusScanner:
    def __init__(self):
        self.scanner = pyclamd.ClamdUnixSocket("/tmp/clamd.sock")
        if not self.scanner.ping():
            raise VirusScannerError("Failed to connect to clamd")

    def scan(self, stream: bytes) -> dict[Any, Any]:
        try:
            res = self.scanner.scan_stream(stream)
        except ConnectionError as ce:
            raise VirusScannerError("Failed to connect to clamd") from ce
        except pyclamd.BufferTooLongError as bte:
            raise VirusScannerError("input buffer too large") from bte
        return res