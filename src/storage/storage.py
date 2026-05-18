from abc import ABC, abstractmethod
import os

import pyvips

class Storage(ABC):
    @staticmethod
    def _clean_filepath(filepath: str) -> str:
        """Removes the file extension from a filepath"""
        if not filepath:
            return ""
        last_dot = filepath.rfind(".")
        last_sep = filepath.rfind("/")
        if last_dot == -1 or last_dot < last_sep:
            return filepath
        return filepath[:last_dot]

    @abstractmethod
    def upload_bytes(self, filepath: str, image: bytes):
        pass

    @abstractmethod
    def open_bytes(self, filepath: str) -> bytes:
        pass

    @abstractmethod
    def get_full_path(self, filepath: str) -> str:
        pass

    @abstractmethod
    def exists(self, filepath: str) -> bool:
        pass

class LocalStorage(Storage):

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _asset_path(self, filepath: str) -> str:
        return os.path.join(self.base_path, filepath)

    def _ensure_directory(self, filepath: str) -> None:
        directory = os.path.dirname(self._asset_path(filepath))
        os.makedirs(directory, exist_ok=True)

    def upload_bytes(self, filepath: str, image: bytes) -> str:
        full_path = self._asset_path(filepath)
        self._ensure_directory(filepath)
        with open(full_path, "wb") as f:
            f.write(image)
        return full_path

    def open_bytes(self, filepath: str) -> bytes:
        with open(self._asset_path(filepath), "rb") as f:
            return f.read()

    def get_full_path(self, filepath: str) -> str:
        return self._asset_path(filepath)

    def exists(self, filepath: str) -> bool:
        return os.path.exists(self._asset_path(filepath))
