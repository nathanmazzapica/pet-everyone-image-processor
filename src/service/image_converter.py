"""
The image converter service handles converting input images and resizing them as a pre-processing step to background removal
"""
from enum import Enum

from src.service.exceptions import JobFailedError
import pyvips

class AspectRatio(Enum):
    SQUARE = 1
    WIDE = 2
    TALL = 3


def _get_aspect_ratio(img: pyvips.Image) -> AspectRatio:
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
            JobFailedError if an image cannot be verified
    """

    try:
        img: pyvips.Image = pyvips.Image.new_from_buffer(file, "") #pyright: ignore [reportAssignmentType]
        img.stats()
    except:
        raise JobFailedError(f"Invalid image data")

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
    img = _verify_image(image_data)
    img = _resize_image(img)
    return img.write_to_buffer(".webp", Q=80, strip=True)
