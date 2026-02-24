import sqlite3

from typing import Any, List, Optional
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

            return Job.from_row(row)

    def __get_field(self, job_id: int, column: str) -> Any | None:
        with self.conn:
            res = self.conn.execute(
                f"SELECT {column} FROM job WHERE job_id=(?)",
                (job_id,),
            )
            row = res.fetchone()
            if row is None:
                return None
            return row[column]
    
    def __get_all_by_status(self, status: JobStatus) -> List[Job]:
        jobs: List[Job] = []
        with self.conn:
            res = self.conn.execute(
                "SELECT * FROM job WHERE job_status=(?)",
                (status.value,),
            )
            for job in res.fetchall():
                jobs.append(Job.from_row(job))
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

    def get_status(self, job_id: int) -> Optional[JobStatus]:
        value = self.__get_field(job_id, "job_status")
        if value is None:
            return None
        return JobStatus(value)

    def get_input_url(self, job_id: int) -> Optional[str]:
        value = self.__get_field(job_id, "input_url")
        if value is None:
            return None
        return str(value)

    def get_output_url(self, job_id: int) -> Optional[str]:
        value = self.__get_field(job_id, "output_url")
        if value is None:
            return None
        return str(value)

    def get_attempt_count(self, job_id: int) -> Optional[int]:
        value = self.__get_field(job_id, "attempt_count")
        if value is None:
            return None
        return int(value)

    def get_last_locked(self, job_id: int) -> Optional[float]:
        value = self.__get_field(job_id, "last_locked")
        if value is None:
            return None
        return float(value)

    def get_created_at(self, job_id: int) -> Optional[float]:
        value = self.__get_field(job_id, "created_at")
        if value is None:
            return None
        return float(value)

    def get_updated_at(self, job_id: int) -> Optional[float]:
        value = self.__get_field(job_id, "updated_at")
        if value is None:
            return None
        return float(value)

    def update_status(self, job_id: int, status: JobStatus) -> bool:
        with self.conn:
            res = self.conn.execute(
                "UPDATE job SET job_status=(?) WHERE job_id=(?)",
                (status.value, job_id),
            )
            return res.rowcount > 0

    def update_last_locked(self, job_id: int, last_locked: float | None) -> bool:
        with self.conn:
            res = self.conn.execute(
                "UPDATE job SET job_last_locked=(?) WHERE job_id=(?)",
                (last_locked, job_id),
            )
            return res.rowcount > 0

    def update_attempt_count(self, job_id: int, attempt_count: int) -> bool:
        with self.conn:
            res = self.conn.execute(
                "UPDATE job SET job_attempt_count=(?) WHERE job_id=(?)",
                (attempt_count, job_id),
            )
            return res.rowcount > 0


    
