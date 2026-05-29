from abc import ABC, abstractmethod
import os

import errno
import pyvips

class StorageError(Exception):
    """Storage layer exception"""
    pass

class StorageConfigurationError(StorageError):
    pass

class FatalStorageUploadError(StorageError):
    """Raised when storage encounters an error that cannot be recovered from. e.g disk/quota full"""
    pass

class AssetNotFoundError(StorageError):
    """Raised when an asset cannot be found"""
    pass

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
    def delete(self, filepath: str) -> None:
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
        try:
            with open(full_path, "wb") as f:
                f.write(image)
        except PermissionError as pe:
            raise StorageConfigurationError(f"Invalid permission settings for base path: {self.base_path}!")
        except OSError as ose:
            if ose.errno == errno.ENOSPC:
                raise FatalStorageUploadError("Disk full!")
        return full_path

    def open_bytes(self, filepath: str) -> bytes:
        try:
            with open(self._asset_path(filepath), "rb") as f:
                return f.read()
        except (FileNotFoundError, IsADirectoryError) as e:
            raise AssetNotFoundError(f"Asset {filepath} could not be located") from e
        except MemoryError:
            raise
        except OSError as ose:
            raise StorageError("Unknown storage error") from ose

    def delete(self, filepath: str) -> None:
        os.remove(self._asset_path(filepath))

    def get_full_path(self, filepath: str) -> str:
        return self._asset_path(filepath)

    def exists(self, filepath: str) -> bool:
        return os.path.exists(self._asset_path(filepath))
