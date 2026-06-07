from typing import Optional

from src.models.errors import ErrorCode
from src.repository.job_repository import JobRepository
from src.models.job import Job
from src.service.exceptions import JobFailedError, FatalServiceError, InvalidImageFormatError
from src.service.processors.background_remover import BackgroundRemover, BackgroundRemoverError, BackgroundRemoverSetupError
from src.storage.storage import Storage, StorageError, FatalStorageUploadError, StorageConfigurationError


def _final_path(img_uuid: str) -> str:
    return f"uploads/final/{img_uuid}"


def _strip_path(path: str) -> str:
    return path.split("/")[-1]


class BackgroundRemovalService:

    def __init__(self,
                 storage: Storage,
                 background_remover: BackgroundRemover
    ):
        self.storage = storage
        self.background_remover = background_remover

    def remove_background(self, job: Job) -> str:
        try:
            img = self.storage.open_bytes(job.input_key)
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error", status_code=ErrorCode.STORAGE_CONFIG_ERROR) from e
        except StorageError as e:
            raise JobFailedError("Failed to open image", status_code=ErrorCode.STORAGE_ERROR) from e
        except MemoryError as e:
            raise FatalServiceError("Out of memory", status_code=ErrorCode.OUT_OF_MEMORY) from e

        try:
            converted_img = self.background_remover.process(img)
        except InvalidImageFormatError as e:
            raise JobFailedError("Invalid image format", status_code=ErrorCode.INVALID_FILE_FORMAT) from e
        except BackgroundRemoverSetupError as e:
            raise FatalServiceError("Background removal setup error", status_code=ErrorCode.MODEL_INIT_FAILED) from e
        except Exception as e:
            raise FatalServiceError("Unknown background removal error", status_code=ErrorCode.UNKNOWN) from e

        path = _final_path(_strip_path(job.input_key))
        try:
            self.storage.upload_bytes(path, converted_img)
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error", status_code=ErrorCode.STORAGE_CONFIG_ERROR) from e
        except FatalStorageUploadError as e:
            raise FatalServiceError("Image could not be uploaded", status_code=ErrorCode.DISK_FULL) from e
            # TODO: determine what to actually do when storage is full
        except OSError as e:
            raise FatalServiceError("Failed to upload image", status_code=ErrorCode.UNKNOWN) from e

        return path
