import logging
from time import sleep

from src.messaging.exceptions import PublisherError, PublisherInvalidPayloadError, PublisherConnectionError, \
    PublisherConfigurationError
from src.messaging.publisher import Publisher
from src.models.errors import ErrorCode
from src.models.status import JobStatus
from src.models.status_update import JobStatusUpdate, JobSucceededUpdate, JobFailedUpdate
from src.repository.repository import Repository

logger = logging.getLogger(__name__)


class OutboxWorker:
    def __init__(
            self,
            publisher: Publisher,
            repo: Repository,
            idle_sleep: float = 1.0,
            retry_sleep: float = 5.0,
    ):
        self.publisher = publisher
        self.repo = repo
        self.IDLE_SLEEP = idle_sleep
        self.RETRY_SLEEP = retry_sleep

    @staticmethod
    def _build_update(job, error_code: int = ErrorCode.UNKNOWN) -> JobStatusUpdate:
        if job.status == JobStatus.DONE:
            return JobSucceededUpdate(
                id=job.id,
                job_type=job.job_type,
                pet_id=str(job.pet_id),
                status=job.status,
                output_key=job.output_key or "",
            )
        if job.status == JobStatus.FAILED:
            return JobFailedUpdate(
                id=job.id,
                job_type=job.job_type,
                pet_id=str(job.pet_id),
                status=job.status,
                error_code=error_code,
            )
        return JobStatusUpdate(
            id=job.id,
            event_type="job_status_changed",
            job_type=job.job_type,
            pet_id=str(job.pet_id),
            status=job.status,
        )

    def run(self):
        """
            Fetches jobs from the outbox and publishes them to the message bus. If publishing is successful,
            the job is removed from the outbox.

            If publishing fails due to a connection error, the worker will pause for a short time before retrying.

            If no jobs are found in the outbox, the worker will sleep for a short time before checking again.
        """
        logger.info("Starting outbox worker")
        while True:
            job = self.repo.get_next_job_in_outbox()
            if job is None:
                sleep(self.IDLE_SLEEP)
                continue

            try:
                error_code = ErrorCode.UNKNOWN
                if job.status == JobStatus.FAILED:
                    error_code = self.repo.get_error_code_for_job(job.id) or ErrorCode.UNKNOWN
                update = self._build_update(job, error_code)
                self.publisher.publish(update)
                self.repo.delete_job_from_outbox(job.id)
                logger.info("Published job %s", job.id)
            except PublisherConnectionError:
                logger.warning(
                    "Connection error publishing job %s, retrying in %.1fs",
                    job.id, self.RETRY_SLEEP,
                )
                sleep(self.RETRY_SLEEP)
            except (PublisherConfigurationError, PublisherError, PublisherInvalidPayloadError) as e:
                logger.error("Failed to publish job %s: %s", job.id, e)
                raise e
