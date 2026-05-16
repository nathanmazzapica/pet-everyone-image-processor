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

    def __resize_image(self, img: pyvips.Image):
        aspect_ratio = get_aspect_ratio(img)

        if aspect_ratio == AspectRatio.SQUARE:
            if img.width <= 1024 and img.height <= 1024:
                return img
            return img.thumbnail_image(1024, height=1024)
        if aspect_ratio == AspectRatio.WIDE:
            if img.width <= 1280:
                return img
            return img.thumbnail_image(1280, height=720)
        if aspect_ratio == AspectRatio.TALL:
            if img.height <= 1280:
                return img
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

        image = self.storage.open_image(filepath)
        print(image.width, image.height)
        image = self.__resize_image(image)
        print(image.width, image.height)

        return self.storage.upload(filepath, image, pre=True)

