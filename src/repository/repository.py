import sqlite3

from src.models.job import Job

class JobRepository():

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, input_url: str) -> int | None:
        with self.conn:
            res = self.conn.execute("INSERT INTO job(input_url) VALUES (?)", (input_url,))
            return res.lastrowid

    def get_by_id(self, id: int) -> Job:
        with self.conn:
            res = self.conn.execute("SELECT * FROM job WHERE job_id=(?)", (id,))
            row = res.fetchone()
            return Job.from_tuple(row)
