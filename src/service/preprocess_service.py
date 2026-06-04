from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.models.job import Job
from src.service.exceptions import JobRetryableError, JobFailedError, InvalidImageFormatError, FatalServiceError
from src.service.processors.image_converter import convert
from src.storage.storage import Storage, StorageError, FatalStorageUploadError, StorageConfigurationError, \
    AssetNotFoundError


def _preprocessed_path(img_uuid: str) -> str:
    return f"uploads/preprocessed/{img_uuid}"


def _strip_path(path: str) -> str:
    return path.split("/")[-1]


class PreprocessService:

    def __init__(self,
                 storage: Storage,
                 preprocess_repository: PreprocessJobRepository):
        self.storage = storage
        self.preprocess_repository = preprocess_repository

    def preprocess(self, job: Job) -> str:
        try:
            img = self.storage.open_bytes(job.input_key)
        except AssetNotFoundError as e:
            raise JobFailedError("Image not found") from e
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error") from e
        except StorageError as e:
            raise JobFailedError("Failed to open image") from e
        except MemoryError as e:
            raise FatalServiceError("Out of memory") from e

        try:
            converted_img = convert(img)
        except InvalidImageFormatError as iife:
            raise JobFailedError("Invalid image format") from iife
        except Exception as e:
            raise FatalServiceError("Unknown preprocessing error") from e

        path = _preprocessed_path(_strip_path(job.input_key))
        try:
            self.storage.upload_bytes(path, converted_img)
        except StorageConfigurationError as e:
            raise FatalServiceError("Storage configuration error") from e
        except FatalStorageUploadError as e:
            raise FatalServiceError("Image could not be uploaded") from e
        except OSError as e:
            raise JobRetryableError("Failed to upload image") from e

        return path
