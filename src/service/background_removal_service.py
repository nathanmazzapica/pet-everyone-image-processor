from typing import Optional

from src.repository.job_repository import JobRepository
from src.models.job import Job
from src.models.status import JobStatus
from src.service.exceptions import JobRetryableError, JobFailedError
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import Storage


def _final_path(img_uuid: str) -> str:
    return f"uploads/final/{img_uuid}"


def _strip_path(path: str) -> str:
    return path.split("/")[-1]


class BackgroundRemovalService:

    def __init__(self,
                 storage: Storage,
                 background_remover: Optional[BackgroundRemover],
                 job_repository: JobRepository):
        self.storage = storage
        self.background_remover = background_remover
        self.repository = job_repository

    def remove_background(self, job: Job) -> str:
        if self.background_remover is None:
            raise JobFailedError("Background removal is not available")
        img = self.storage.open_bytes(job.input_url)
        try:
            converted_img = self.background_remover.process(img)
        except Exception as e:
            self.repository.update_status(job.id, JobStatus.RETRY)
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
