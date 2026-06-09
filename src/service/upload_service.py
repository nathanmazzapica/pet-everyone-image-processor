import uuid

import pyvips

from src.models.errors import ErrorCode
from src.service.exceptions import FatalServiceError, JobFailedError, InvalidImageFormatError
from src.repository.repository import Repository
from src.storage.storage import FatalStorageUploadError, Storage


def _object_key(img_uuid: str, pet_id: str) -> str:
    """Returns an object key for the original image."""
    return f"uploads/pet_images/{pet_id}/{img_uuid}/original"

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


class UploadService:
    MAX_UPLOAD_SIZE = 1024 * 1024 * 25

    def __init__(self,
                 storage: Storage,
                 repo: Repository):
        self.storage = storage
        self.repo = repo

    def _validate_upload(self, img: bytes) -> None:
        """
        Validates the image data.

        Args:
            img (bytes): The image data to validate

        Raises:
            InvalidImageFormatError: if the image is invalid
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

    def submit_upload(self, img: bytes, pet_id: uuid.UUID) -> str:
        try:
            self._validate_upload(img)
        except InvalidImageFormatError as e:
            raise JobFailedError("Invalid image", status_code=ErrorCode.INVALID_FILE_FORMAT) from e

        image_id = uuid.uuid4()
        path = _object_key(str(image_id), str(pet_id))
        job_id = self.repo.create_preprocess_job(path, pet_id, image_id)

        try:
            self.storage.upload_bytes(path, img)
        except FatalStorageUploadError as e:
            self.repo.fail_job(job_id, ErrorCode.DISK_FULL)
            raise FatalServiceError(f"Fatal storage error: {e}") from e
        except OSError as e:
            self.repo.fail_job(job_id, ErrorCode.STORAGE_ERROR)
            raise JobFailedError("Failed to upload image") from e

        return path
