from withoutbg import WithoutBG, exceptions
import time

from src.models.job import Job
from src.models.status import JobStatus
from src.repository.repository import JobRepository
from src.service.exceptions import InvalidJobError, JobFailedError, JobRetryableError
from src.storage.storage import Storage

class BackgroundRemover:

    def __init__(self, repository: JobRepository, storage: Storage) -> None:
        self.repository = repository
        self.storage = storage
        self.model = WithoutBG.opensource()

    def __lock_job(self, job: Job) -> None:
        job.status = JobStatus.PROCESSING
        self.repository.update_status(job.id, JobStatus.PROCESSING)
        self.repository.update_last_locked(job.id, time.time())

    def __unlock_job(self, job: Job, status: JobStatus):
        job.status = status
        job.attempt_count = job.attempt_count + 1
        self.repository.update_status(job.id, status)
        self.repository.update_attempt_count(job.id, job.attempt_count)

    def __mark_job_complete(self, job: Job):
        self.__unlock_job(job, JobStatus.DONE)

    def __mark_job_failed(self, job: Job):
        self.__unlock_job(job, JobStatus.FAILED)

    def __mark_job_for_retry(self, job: Job):
        self.__unlock_job(job, JobStatus.RETRY)

    def __remove_background(self, job: Job) -> None:
        result = self.model.remove_background(job.input_url)
        output_path = self.storage.upload(job, result)
        job.output_url = output_path
        self.repository.update_output_url(job.id, output_path)

    def process(self, job: Job):
        """
        TODO: Add high-level description.

        Args:
            job: the job to be processed

        Raises:
            InvalidJobError: TODO
            JobFailedError: TODO
            JobRetryableError: TODO
        """
        if job.status != JobStatus.QUEUED:
            raise InvalidJobError(f"Job {job.id} is not queued at this time {job}")

        if not self.storage.exists(job):
            self.__mark_job_failed(job)
            raise FileNotFoundError(f"no image found at {job.input_url}")

        self.__lock_job(job)

        try:
            self.__remove_background(job)
        except exceptions.InvalidImageError as ime:
            # InvalidImageError is NOT recoverable.
            self.__mark_job_failed(job)
            print(ime)
            raise JobFailedError(
                f"Job {job.id} failed with invalid input"
            ) from ime
        except OSError as ose:
            # raised if file cannot be FULLY written. File *may* have been created
            print(ose)
            self.__mark_job_for_retry(job)
            raise JobRetryableError(
                f"Job {job.id} failed due to processing error"
            ) from ose

        self.__mark_job_complete(job)
