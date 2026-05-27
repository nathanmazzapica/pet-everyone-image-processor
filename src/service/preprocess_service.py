from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.models.job import Job
from src.models.status import JobStatus
from src.service.exceptions import JobRetryableError, JobFailedError
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.processors.image_converter import convert
from src.storage.storage import Storage


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
