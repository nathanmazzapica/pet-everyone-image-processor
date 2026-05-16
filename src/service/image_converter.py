"""
The image converter service handles converting input images and resizing them as a pre-processing step to background removal
"""
from enum import Enum

from src.repository.repository import JobRepository
from src.models.image_format import ImageFormat
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.exceptions import JobFailedError
from src.storage.storage import Storage
import pyvips

class AspectRatio(Enum):
    SQUARE = 1
    WIDE = 2
    TALL = 3


def get_aspect_ratio(img: pyvips.Image) -> AspectRatio:
    raw = img.width / img.height
    if raw > 1:
        return AspectRatio.WIDE
    if raw == 1:
        return AspectRatio.SQUARE
    return AspectRatio.TALL


class ImageConverter:
    def __init__(self, repository: JobRepository, storage: Storage) -> None:
        self.repository = repository
        self.storage = storage
        # initialize libvips as needed
        pass

    def _get_mime_type(self, filepath: str) -> ImageFormat:
        """Verifies the image has a valid file format and returns the format.

            Raises:
                InvalidImageFormatError if file format is not a whitelisted image.
        """
        try:
            header = self.storage.open_image(filepath)[:12]
        except OSError as exc:
            raise InvalidImageFormatError from exc

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

    def __resize_image(self, img: pyvips.Image):
        aspect_ratio = get_aspect_ratio(img)

        if aspect_ratio == AspectRatio.SQUARE:
            return img.thumbnail_image(1024, height=1024)
        if aspect_ratio == AspectRatio.WIDE:
            return img.thumbnail_image(1280, height=720)
        if aspect_ratio == AspectRatio.TALL:
            return img.thumbnail_image(720, height=1280)

        raise ValueError("Invalid aspect ratio")

    def __verify_image(self, filepath: str) -> pyvips.Image:
        """
            Verifies a file is actually an image

            Raises:
                JobFailedError if an image cannot be verified
        """

        try:
            img: pyvips.Image = pyvips.Image.new_from_buffer(self.storage.open_image(filepath), "") #pyright: ignore [reportAssignmentType]
            img.stats()
        except:
            raise JobFailedError(f"Image does not appear to be an image at {filepath}")

        return img

    def convert(self, filepath: str) -> str | None:
        if not self.storage.exists(filepath):
            raise JobFailedError(f"Image does not exist at {filepath}")

        img_format = self._get_mime_type(filepath)
        image = self.__verify_image(filepath)
        image = self.__resize_image(image)

        return self.storage.upload(filepath, image, pre=True)

