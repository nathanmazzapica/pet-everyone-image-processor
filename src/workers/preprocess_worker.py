import logging
import sqlite3

from src.repository.exceptions import FatalDatabaseError
from src.models.status import JobStatus
from src.service.exceptions import JobFailedError, FatalServiceError
from src.service.preprocess_service import PreprocessService
from src.repository.repository import Repository
from src.models.status import JobType
from time import sleep

from src.storage.storage import LocalStorage

logger = logging.getLogger(__name__)


class Worker:

    def __init__(self, repo: Repository,
                 proc: PreprocessService, retry_delay=60):
        self.repo = repo
        self.proc = proc
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm
        self.MAX_ATTEMPTS = 3
        self.RETRY_DELAY = retry_delay

    def run(self):
        logger.info("Starting worker")
        while True:
            logger.debug("Checking for jobs")
            job = self.repo.next_preprocess_job()
            if job is None:
                logger.debug("No jobs to process")
                sleep(1)
                continue

            try:
                logger.info("Processing job %s", job.id)
                path = self.proc.preprocess(job)
                self.repo.complete_preprocess_job(job.id, path, job.pet_id, job.image_id)
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
        level=logging.INFO,
        format="[%(asctime)s] [PID %(process)d] %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("pyvips").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    conn = sqlite3.connect("jobs.db")
    r = Repository(conn)
    s = LocalStorage(base_path="storage")
    pp = PreprocessService(s)
    worker = Worker(r, pp)
    try:
        worker.run()
    except FatalServiceError as fse:
        logger.exception("Fatal service error")
        raise fse
    except KeyboardInterrupt:
        logger.info("Shutting down")
        conn.close()
        exit(0)
    except FatalDatabaseError as fde:
        logger.exception("Fatal database error")
        raise fde
