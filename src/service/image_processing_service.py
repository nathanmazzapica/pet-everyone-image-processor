import os
import uuid
from typing import Optional

import pyvips

from src.service.exceptions import JobRetryableError
from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.service.exceptions import JobFailedError
from src.models.job import Job
from src.models.status import JobStatus
from src.repository.job_repository import JobRepository
from src.service.background_remover import BackgroundRemover
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.image_converter import convert
from src.storage.storage import Storage


def _final_path(img_uuid: str) -> str:
    return f"uploads/final/{img_uuid}"


def _preprocessed_path(img_uuid: str) -> str:
    return f"uploads/preprocessed/{img_uuid}"


def _original_path(img_uuid: str) -> str:
    return f"uploads/original/{img_uuid}"


def _strip_path(path: str) -> str:
    return path.split("/")[-1]


def _is_supported_header(h: bytes) -> bool:
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return True
    if h[:3] == b"\xFF\xD8\xFF":
        return True
    if h.startswith(b"RIFF") and h[8:12] == b"WEBP":
        return True

    if len(h) >= 12 and h[4:8] == b"ftyp":
        brand = h[8:12]
        return brand in {b"heic", b"heix", b"mif1", b"msf1", b"heif"}

    return False

"""
Design note:
    This smells bad. Using one service to do three things isn't great. Especially when
    each operation is only ever used by one type of worker
    
    The api only ever uses `submit_upload()`
    pre_process worker only uses `preprocess()`
    background removal worker -> `remove_background()`
    
    This needs to be broken down into three services.
    
    I will get to this in a separate branch
"""

class ImageProcessingService:
    MAX_UPLOAD_SIZE = 1024 * 1024 * 25

    def __init__(self,
                 storage: Storage,
                 background_remover: Optional[BackgroundRemover],
                 job_repository: JobRepository,
                 preprocess_repository: PreprocessJobRepository):
        self.storage = storage
        self.background_remover = background_remover
        self.repository = job_repository
        self.preprocess_repository = preprocess_repository

    def _validate_upload(self, img: bytes) -> None:
        """
        Validates the uploaded image to ensure its size and format meet the requirements.

        The method is designed to check whether the provided image complies with the
        maximum allowed size and whether its file format is valid. Supported formats
        include PNG, JPEG, WebP, and specific HEIF/HEIC variations validated based on
        header bytes.

        Raises:
            InvalidImageFormatError: If the provided image exceeds the maximum
            allowed size or its format is invalid.

        Parameters:
            img (bytes): The binary data of the uploaded image.
        """
        if len(img) > self.MAX_UPLOAD_SIZE:
            raise InvalidImageFormatError("Image is too large")

        if not _is_supported_header(img[:16]):
            raise InvalidImageFormatError("Unsupported image format")


        try:
            i: pyvips.Image = pyvips.Image.new_from_buffer(img, "", access="sequential")
            i.avg()
        except pyvips.error.Error as e:
            raise InvalidImageFormatError("Invalid image format") from e

    def submit_upload(self, img: bytes, img_id: uuid.UUID) -> str:
        """
        Performs basic mime type validation, saves the image to storage and creates a job in the database.

        Args:
            img: the image bytes to be processed
            img_id: the id of the image

        Raises:
            InvalidImageFormatError: if the image is not a valid image format
        """
        try:
            self._validate_upload(img)
        except InvalidImageFormatError as e:
            raise JobFailedError("Invalid image") from e

        img_uuid = str(img_id)
        path = _original_path(img_uuid)
        job_id = self.preprocess_repository.create(path)
        if job_id is None:
            raise Exception("Failed to create job")

        try:
            self.storage.upload_bytes(path, img)
        except OSError as e:
            self.preprocess_repository.update_status(job_id, JobStatus.FAILED)
            raise JobFailedError("Failed to upload image") from e

        return path

    def preprocess(self, job: Job) -> str:
        img = self.storage.open_bytes(job.input_url)
        try:
            converted_img = convert(img)
        except InvalidImageFormatError as iife:
            self.preprocess_repository.update_status(job.id, JobStatus.FAILED)
            raise JobFailedError("Invalid image format") from iife

        path = _preprocessed_path(_strip_path(job.input_url))
        try:
            self.storage.upload_bytes(path, converted_img)
        except OSError as e:
            self.preprocess_repository.update_status(job.id, JobStatus.RETRY)
            raise JobRetryableError("Failed to upload image") from e
        self.preprocess_repository.update_output_url(job.id, path)
        self.preprocess_repository.update_status(job.id, JobStatus.DONE)

        return path

    def remove_background(self, job: Job) -> str:
        if self.background_remover is None:
            raise JobFailedError("Background removal is not available")
        img = self.storage.open_bytes(job.input_url)
        try:
            converted_img = self.background_remover.process(img)
        except Exception as e:
            self.preprocess_repository.update_status(job.id, JobStatus.RETRY)
            raise JobRetryableError("Failed to remove background") from e

        path = _final_path(_strip_path(job.input_url))
        try:
            self.storage.upload_bytes(path, converted_img)
        except OSError as e:
            self.repository.update_status(job.id, JobStatus.RETRY)
            raise JobRetryableError("Failed to upload image") from e
        self.repository.update_output_url(job.id, path)
        self.repository.update_status(job.id, JobStatus.DONE)

        return path
