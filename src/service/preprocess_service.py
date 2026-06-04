from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.models.job import Job
from src.models.errors import ErrorCode
from src.service.exceptions import JobFailedError, InvalidImageFormatError, FatalServiceError
from src.service.processors.image_converter import convert
from src.storage.storage import Storage, StorageError, FatalStorageUploadError, StorageConfigurationError, \
    AssetNotFoundError


def _preprocessed_path(img_uuid: str) -> str:
    return f"uploads/preprocessed/{img_uuid}"


def _strip_path(path: str) -> str:
    return path.split("/")[-1]


class PreprocessService:

    def __init__(self, storage: Storage):
        self.storage = storage

    def preprocess(self, job: Job) -> str:
        try:
            img = self.storage.open_bytes(job.input_key)
        except AssetNotFoundError as e:
            raise JobFailedError("Image not found", status_code=ErrorCode.ASSET_NOT_FOUND) from e
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error", status_code=ErrorCode.STORAGE_CONFIG_ERROR) from e
        except StorageError as e:
            raise JobFailedError("Failed to open image", status_code=ErrorCode.STORAGE_ERROR) from e
        except MemoryError as e:
            raise FatalServiceError("Out of memory", status_code=ErrorCode.OUT_OF_MEMORY) from e

        try:
            converted_img = convert(img)
        except InvalidImageFormatError as iife:
            raise JobFailedError("Invalid image format", status_code=ErrorCode.INVALID_FILE_FORMAT) from iife

        path = _preprocessed_path(_strip_path(job.input_key))
        try:
            self.storage.upload_bytes(path, converted_img)
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error", status_code=ErrorCode.STORAGE_CONFIG_ERROR) from e
        except FatalStorageUploadError as e:
            # note: reconsider this name for s3
            raise FatalServiceError("Image could not be uploaded", status_code=ErrorCode.DISK_FULL) from e
        except OSError as e:
            raise FatalServiceError("Failed to upload image", status_code=ErrorCode.UNKNOWN) from e

        return path
