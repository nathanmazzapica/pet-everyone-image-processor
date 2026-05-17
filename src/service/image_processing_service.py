import os
import uuid

from src.models.status import JobStatus
from repository.repository import JobRepository
from service.background_remover import BackgroundRemover
from service.conversion_exceptions import InvalidImageFormatError
from service.image_converter import ImageConverter
from storage.storage import Storage


def _final_path(img_uuid: str) -> str:
    return f"uploads/final/{img_uuid}"


def _preprocessed_path(img_uuid: str) -> str:
    return f"uploads/preprocessed/{img_uuid}"


def _original_path(img_uuid: str) -> str:
    return f"uploads/original/{img_uuid}"


class ImageProcessingService:
    MAX_UPLOAD_SIZE = 1024 * 1024 * 25
    def __init__(self,
                 storage: Storage,
                 converter: ImageConverter,
                 background_remover: BackgroundRemover,
                 repository: JobRepository):
        self.storage = storage
        self.converter = converter
        self.background_remover = background_remover
        self.repository = repository

        os.makedirs("uploads/original", exist_ok=True)
        os.makedirs("uploads/preprocessed", exist_ok=True)
        os.makedirs("uploads/final", exist_ok=True)

    def _validate_upload(self, img: bytes):
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

        header = img[:16]
        if (header.startswith(b"\x89PNG\r\n\x1a\n") or
            header[:3] == b"\xFF\xD8\xFF" or
            header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            return

        if len(header) >= 12 and header[4:8] == b"ftyp":
            brand = header[8:12]
            if brand in {b"heic", b"heix", b"mif1", b"msf1", b"heif"}:
                return


        raise InvalidImageFormatError("Invalid image format")

    def submit_upload(self, img: bytes):
        """
        Performs basic mime type validation, saves the image to storage and creates a job in the database.

        Args:
            img: the image bytes to be processed

        Raises:
            InvalidImageFormatError: if the image is not a valid image format
        """
        self._validate_upload(img)
        img_uuid = str(uuid.uuid4())
        path = _original_path(img_uuid)
        job_id = self.repository.create(path)
        if job_id is None:
            raise Exception("Failed to create job")

        try:
            self.storage.upload_bytes(path, img)
        except OSError as e:
            self.repository.update_status(job_id, JobStatus.FAILED)
            raise e

    def run_preprocessing(self, job_id: int):
        raise NotImplementedError

    def run_background_removal(self, job_id: int):
        raise NotImplementedError