from src.repository.repository import JobRepository
from time import sleep;

class Worker():

    def __init__(self, repo: JobRepository):
        self.repo = repo
        self.processed_jobs = 0
        self.failed_jobs = 0 # for later accounting, not implemented atm
        self.run()

    def run(self):
        while (True):
            job = self.repo.get_next_in_queue()
            if job is None:
                sleep(1)
                continue
            
            if not self.repo.lock_job(job.id):
                continue

            try:
                raise NotImplementedError("TODO: IMPLEMENT JOB HANDLING")
            except Exception as e:
                raise NotImplementedError("TODO: IMPLEMENT JOB ERROR HANDLING")


