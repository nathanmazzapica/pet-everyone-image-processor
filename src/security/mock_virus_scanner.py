import warnings
from typing import Optional

from src.security.virus_scanner import VirusScanner

class MockVirusScanner(VirusScanner):
    def __init__(self):
        warnings.warn("Using mock virus scanner", RuntimeWarning, stacklevel=2)

    def scan(self, stream: bytes) -> Optional[str]:
        return None