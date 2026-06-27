import sqlite3

from src.service.exceptions import JobFailedError, FatalServiceError
from src.models.status import JobStatus
from src.service.processors.background_remover import BackgroundRemover
from src.service.background_removal_service import BackgroundRemovalService
from src.repository.repository import Repository
from time import sleep
import logging

from src.storage.storage import LocalStorage

logger = logging.getLogger(__name__)

class Worker():

    def __init__(self, repo: Repository, proc: BackgroundRemovalService):
        self.repo = repo
        self.proc = proc
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm
        self.MAX_ATTEMPTS = 3
        self.IDLE_SLEEP = 1.0
        self.RETRY_DELAY = 60

    def run(self):
        logger.info("Starting worker")
        while True:
            logger.debug("Checking for jobs")
            job = self.repo.next_background_removal_job()
            if job is None:
                logger.debug("No jobs to process")
                sleep(self.IDLE_SLEEP)
                continue

            try:
                logger.info("Processing job %s", job.id)
                path = self.proc.remove_background(job)
                self.repo.complete_job(job.id, path)
                logger.info("Job %s processed", job.id)
                self.processed_jobs += 1
            except JobFailedError as jfe:
                logger.exception("Job %s failed", job.id)
                self.repo.fail_job(job.id, jfe.status_code)
                self.failed_jobs += 1
            except FatalServiceError as fse:
                logger.exception("Fatal service error")
                if job.attempt_count >= self.MAX_ATTEMPTS:
                    logger.error("Job %s failed too many times, marking as failed", job.id)
                    self.repo.fail_job(job.id, fse.status_code)
                    self.failed_jobs += 1
                else:
                    self.repo.retry_job(job.id, self.RETRY_DELAY)
                raise fse



if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("pyvips").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    conn = sqlite3.connect("jobs.db")
    r = Repository(conn)
    s = LocalStorage(base_path="storage")
    logging.info("Loading background remover model")
    br = BackgroundRemover()
    logging.info("Background remover model loaded")
    service = BackgroundRemovalService(s, br)
    logging.info("Background removal service initialized")
    w = Worker(r, service)
    logging.info("Worker initialized")
    w.run()
