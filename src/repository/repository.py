import sqlite3

from typing import List
from src.models.job import Job, JobStatus

class JobRepository():

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, input_url: str) -> int | None:
        """creates a job in the database and returns its id"""
        with self.conn:
            res = self.conn.execute("INSERT INTO job(input_url) VALUES (?)", (input_url,))
            return res.lastrowid

    def get_by_id(self, id: int) -> Job | None:
        with self.conn:
            res = self.conn.execute("SELECT * FROM job WHERE job_id=(?)", (id,))
            row = res.fetchone()
            if row is None:
                return None

            return Job.from_tuple(row)
    
    def __get_all_by_status(self, status: JobStatus) -> List[Job]:
        jobs: List[Job] = []
        with self.conn:
            res = self.conn.execute("SELECT * FROM job WHERE job_status=(?)", (status,))
            for job in res.fetchall():
                jobs.append(Job.from_tuple(job))
            return jobs

    def get_all_pending(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.PENDING)

    def get_all_queued(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.QUEUED)

    def get_all_processing(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.PROCESSING)

    def get_all_done(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.DONE)

    def get_all_failed(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.FAILED)

    def get_all_retry(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.RETRY)

    def get_all_rejected(self) -> List[Job]:
        return self.__get_all_by_status(JobStatus.REJECTED)


    
