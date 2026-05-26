import logging

from src.models.status import JobStatus
from src.repository.job_repository import JobRepository
from time import sleep

logger = logging.getLogger(__name__)


class Worker:

    def __init__(self, repo: JobRepository, proc):
        self.repo = repo
        self.proc = proc
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm

    def run(self):
        while True:
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
                self.proc.remove_background(job)
                self.processed_jobs += 1
            except Exception:
                logger.exception("Job %s failed", job.id)
                self.repo.update_status(job.id, JobStatus.FAILED)
                self.failed_jobs += 1