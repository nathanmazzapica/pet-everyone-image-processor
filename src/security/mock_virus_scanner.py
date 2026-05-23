from typing import Optional

from src.security.virus_scanner import VirusScanner

class MockVirusScanner(VirusScanner):
    def __init__(self):
        print("[WARNING] Using mock virus scanner")
        pass

    def scan(self, stream: bytes) -> Optional[str]:
        return None