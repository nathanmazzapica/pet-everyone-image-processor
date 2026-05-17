from typing import Protocol


class VirusScanner(Protocol):
    def scan(self, filepath: str) -> bool:
        pass