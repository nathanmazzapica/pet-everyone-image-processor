import sqlite3

from src.models.status import JobStatus
from src.service.image_processing_service import ImageProcessingService
from src.repository.preprocess_job_repository import PreprocessJobRepository
from src.repository.job_repository import JobRepository
from time import sleep

from src.storage.storage import LocalStorage


class Worker:

    def __init__(self, repo: PreprocessJobRepository,
                 job_repo: JobRepository,
                 proc: ImageProcessingService):
        self.repo = repo
        self.job_repo = job_repo
        self.proc = proc
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm
        self.run()

    def run(self):
        while True:
            job = self.repo.get_next_in_queue()
            if job is None:
                print("No jobs to process")
                sleep(1)
                continue
            
            if not self.repo.lock_job(job.id):
                print(f"Job {job.id} is already locked")
                continue

            try:
                print(f"Processing job {job.id}")
                path = self.proc.preprocess(job)
            except Exception as e:
                print(f"Job {job.id} failed with error {e}")
                self.repo.update_status(job.id, JobStatus.FAILED)
                continue

            self.job_repo.create(path)



if __name__ == "__main__":
    conn = sqlite3.connect("jobs.db")
    r = PreprocessJobRepository(conn)
    jr = JobRepository(conn)
    s = LocalStorage(base_path="storage")
    pp = ImageProcessingService(s, None, jr, r)
    worker = Worker(r, jr, pp)

