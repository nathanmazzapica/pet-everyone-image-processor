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
    def get_tmp_path(self) -> str:
        """returns a temporary filepath for intra-processing steps"""
        pass

    @abstractmethod
    def exists(self, filepath: str) -> bool:
        pass

class LocalStorage(Storage):

    def __init__(self, base_path: str) -> None:
        self.base_path = base_path
        os.makedirs(self.get_tmp_path(), exist_ok=True)

    def get_tmp_path(self) -> str:
        return os.path.join(self.base_path, "tmp")

    def generate_preprocess_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-pre.webp")

    def generate_output_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-out.webp")

    def upload_bytes(self, filepath: str, image: bytes):
        with open(self.resolve(filepath), "wb") as f:
            f.write(image)

    def open_bytes(self, filepath: str) -> bytes:
        with open(self.resolve(filepath), "rb") as f:
            return f.read()

    def resolve(self, filepath: str) -> str:
        return os.path.join(self.base_path, filepath)

    def exists(self, filepath: str) -> bool:
        return os.path.exists(self.resolve(filepath))
