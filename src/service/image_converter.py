"""
The image converter service handles converting input images and resizing them as a pre-processing step to background removal
"""
from enum import Enum

from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.exceptions import JobFailedError
import pyvips

class AspectRatio(Enum):
    SQUARE = 1
    WIDE = 2
    TALL = 3


def _get_aspect_ratio(img: pyvips.Image) -> AspectRatio:
    if img.width == 0 or img.height == 0:
        raise InvalidImageFormatError("Invalid image dimensions")
    raw = img.width / img.height
    if raw > 1:
        return AspectRatio.WIDE
    if raw == 1:
        return AspectRatio.SQUARE
    return AspectRatio.TALL


def _verify_image(file: bytes) -> pyvips.Image:
    """
        Verifies a file is actually an image

        Raises:
            InvalidImageFormatError if an image cannot be verified
    """

    try:
        img: pyvips.Image = pyvips.Image.new_from_buffer(file, "") #pyright: ignore [reportAssignmentType]
        img.stats()
    except pyvips.error.Error as e:
        raise InvalidImageFormatError("Invalid image data") from e

    return img


def _resize_image(img: pyvips.Image):
    aspect_ratio = _get_aspect_ratio(img)

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


def convert(image_data: bytes) -> bytes:
    """
    Convert an image from its input format to the WEBP format.

    This function processes the provided image data, verifies if it is a valid
    image, resizes it to a specific dimension, and converts it to the WEBP format
    with specific compression settings. Only valid images are processed.

    Args:
        image_data (bytes): The binary content of the input image.

    Returns:
        bytes: The binary content of the converted WEBP image.
    Raises:
        InvalidImageFormatError if the provided image is not a valid image.
        ValueError if the provided image has an invalid aspect ratio.
    """
    img = _verify_image(image_data)
    img = _resize_image(img)
    return img.write_to_buffer(".webp", Q=80, strip=True)
