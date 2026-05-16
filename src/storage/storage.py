from abc import ABC, abstractmethod
import os

import pyvips
from PIL import Image, ImageFile

from models.image_format import ImageFormat
from service.conversion_exceptions import InvalidImageFormatError


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
    def _validate_mime_type(self, filepath: str) -> str:
        pass

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
    @abstractmethod
    def open_image(self, filepath: str) -> pyvips.Image:
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

    def _validate_mime_type(self, filepath: str) -> ImageFormat:
        """Verifies the image has a valid file format and returns the format.

            Raises:
                InvalidImageFormatError if file format is not a whitelisted image.
        """
        with (open(self.resolve(filepath), "rb")) as f:
            header = f.read(16)
            if header.startswith(b"\x89PNG\r\n\x1a\n"):
                return ImageFormat.PNG

            if header[:3] == b"\xFF\xD8\xFF":
                return ImageFormat.JPEG

            if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
                return ImageFormat.WEBP

            if len(header) >= 12 and header[4:8] == b"ftyp":
                brand = header[8:12]
                if brand in {b"heic", b"heix", b"mif1", b"msf1", b"heif"}:
                    return ImageFormat.HEIF

            raise InvalidImageFormatError

    def generate_preprocess_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-pre.webp")

    def generate_output_path(self, input_path: str) -> str:
        return os.path.join(self.get_tmp_path(), f"{Storage._clean_filepath(input_path)}-out.webp")

    def open_image(self, filepath: str) -> pyvips.Image:
        """Opens an image file and returns the bytes"""
        self._validate_mime_type(filepath)
        return pyvips.Image.new_from_file(self.resolve(filepath))




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
