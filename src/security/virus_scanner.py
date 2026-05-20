from typing import Optional

import pyclamd

class VirusScannerError(Exception):
    pass

class VirusScanner:
    def __init__(self, sock: str):
        try:
            self.scanner = pyclamd.ClamdUnixSocket(sock)
            if not self.scanner.ping():
                raise VirusScannerError("Failed to connect to clamd")
        except pyclamd.ConnectionError as ce:
            raise VirusScannerError("Failed to connect to clamd") from ce

    def scan(self, stream: bytes) -> Optional[str]:
        try:
            res = self.scanner.scan_stream(stream)
        except pyclamd.ConnectionError as ce:
            raise VirusScannerError("Failed to connect to clamd") from ce
        except pyclamd.BufferTooLongError as bte:
            raise VirusScannerError("input buffer too large") from bte

        if res is None:
            return None

        return res['stream'][1]