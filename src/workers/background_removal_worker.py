import sqlite3

from src.service.exceptions import JobRetryableError, JobFailedError, FatalServiceError
from src.models.status import JobStatus
from src.service.processors.background_remover import BackgroundRemover
from src.service.background_removal_service import BackgroundRemovalService
from src.repository.job_repository import JobRepository
from time import sleep
import logging

from src.storage.storage import LocalStorage

logger = logging.getLogger(__name__)

class Worker():

    def __init__(self, repo: JobRepository, proc: BackgroundRemovalService):
        self.repo = repo
        self.proc = proc
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm

    def run(self):
        logger.info("Starting worker")
        while True:
            logger.debug("Checking for jobs")
            job = self.repo.get_next_in_queue()
            if job is None:
                logger.debug("No jobs to process")
                sleep(1)
                continue

            if not self.repo.lock_job(job.id):
                logger.warning("Job %s is already locked", job.id)
                continue

            try:
                logger.info("Processing job %s", job.id)
                path = self.proc.remove_background(job)
                self.repo.update_output_url(job.id, path)
                self.repo.update_status(job.id, JobStatus.DONE)
                logger.info("Job %s processed", job.id)
                self.processed_jobs += 1
            except JobRetryableError as jre:
                logger.exception("Job %s failed, retrying", job.id)
                logger.exception(jre)
                if job.attempt_count >= 3:
                    logger.error("Job %s failed too many times, marking as failed", job.id)
                    self.repo.update_status(job.id, JobStatus.FAILED)
                    continue
                logger.warning("Job %s failed, retrying", job.id)
                self.repo.update_attempt_count(job.id, job.attempt_count + 1)
                self.repo.update_status(job.id, JobStatus.QUEUED)
                self.failed_jobs += 1
            except JobFailedError as jfe:
                logger.exception("Job %s failed", job.id)
                logger.exception(jfe)
                self.repo.update_status(job.id, JobStatus.FAILED)
                self.failed_jobs += 1
            except FatalServiceError as fse:
                logger.exception("Fatal service error")
                logger.exception(fse)
                self.repo.update_status(job.id, JobStatus.QUEUED)
                raise fse



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("pyvips").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    conn = sqlite3.connect("jobs.db")
    r = JobRepository(conn)
    s = LocalStorage(base_path="storage")
    logging.info("Loading background remover model")
    br = BackgroundRemover()
    logging.info("Background remover model loaded")
    service = BackgroundRemovalService(s, br, r)
    logging.info("Background removal service initialized")
    w = Worker(r, service)
    logging.info("Worker initialized")
    w.run()
