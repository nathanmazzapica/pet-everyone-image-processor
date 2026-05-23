from abc import ABC, abstractmethod
from typing import Optional
class VirusScanner(ABC):
    @abstractmethod
    def __init__(self):
        pass

    def scan(self, stream: bytes) -> Optional[str]:
        pass
