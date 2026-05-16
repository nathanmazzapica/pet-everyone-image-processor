from abc import ABC, abstractmethod
import os

import pyvips
from PIL import Image, ImageFile

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
    def generate_preprocess_path(self, input_path: str) -> str:
        pass

    @abstractmethod
    def generate_output_path(self, input_path: str) -> str:
        pass

    @abstractmethod
    def upload(self, filepath: str, image: pyvips.Image, pre=False) -> str | None:
        pass

    # I'm not sure what this will look like yet...
    # If we're getting a file from S3 it needs to be downloaded first
    # If we're getting a file locally, we just need to open it?
    # Do we want to move image opening to this method instead of using Image.open in services? maybe... but
    # pyvips doesn't really work like that it seems
    @abstractmethod
    def open_image(self, filepath: str) -> bytes:
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

    def get_tmp_path(self) -> str:
        return os.path.join(self.base_path, "tmp")

    # authority decide who
    def __get_mime_type(self, input_path: str) -> str:
        raise NotImplementedError

    def generate_preprocess_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-pre.webp")

    def generate_output_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-out.webp")

    def open_image(self, filepath: str) -> bytes:
        with open(self.resolve(filepath), "rb") as f:
            file_bytes = f.read()
            return file_bytes

    def upload(self, filepath: str, image: pyvips.Image, pre=False) -> str | None:
        try:
            if pre:
                output_path = self.generate_preprocess_path(filepath)
            else:
                output_path = self.generate_output_path(filepath)
            print(output_path)
            image.write_to_file(output_path, strip=True)
            return output_path
        except OSError as ose:
            # raised if file cannot be fully written
            print(ose)
            pass

    def resolve(self, filepath: str) -> str:
        return os.path.join(self.base_path, filepath)

    def exists(self, filepath: str) -> bool:
        return os.path.exists(self.resolve(filepath))
