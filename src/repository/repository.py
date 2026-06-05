import sqlite3
import uuid
from typing import Optional

from src.repository.exceptions import (
    DatabaseNotInitialized,
    FatalDatabaseError,
    JobNotFoundError,
)
from src.models.job import Job
from src.models.status import JobStatus, JobType


class Repository:

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.conn.row_factory = sqlite3.Row
        self.__ensure_initialized()

    def __ensure_initialized(self, schema_path: str = "schema.sql") -> None:
        with self.conn:
            res = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND LOWER(name)='job'"
            )
            if res.fetchone() is not None:
                return

        try:
            with open(schema_path, "r", encoding="utf-8") as schema_file:
                schema_sql = schema_file.read()
        except FileNotFoundError as exc:
            raise DatabaseNotInitialized(
                "Database schema not found. Please run 'python -m src.repository.init_db' to initialize the database."
            ) from exc

        with self.conn:
            self.conn.executescript(schema_sql)

    def __create_job(self, input_key: str, job_type: JobType, pet_id: uuid.UUID) -> int:
        try:
            with self.conn:
                res = self.conn.execute(
                    "INSERT INTO Job (job_type, job_status, input_key, pet_id) VALUES (?, ?, ?, ?)",
                    (job_type.value, JobStatus.QUEUED.value, input_key, str(pet_id)),
                )
                return res.lastrowid
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.ProgrammingError as e:
            raise FatalDatabaseError("Database schema mismatch") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError("Corrupt database file") from e

    def create_preprocess_job(self, input_key: str, pet_id: uuid.UUID) -> int:
        return self.__create_job(input_key, JobType.PREPROCESS, pet_id)

    def create_background_removal_job(self, input_key: str, pet_id: uuid.UUID) -> int:
        return self.__create_job(input_key, JobType.BACKGROUND_REMOVAL, pet_id)

    def lock_job(self, job_id: int) -> bool:
        """Transitions a QUEUED job to PROCESSING, incrementing attempt_count. Returns False if the job was not in QUEUED state."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    """UPDATE Job
                       SET job_status    = ?,
                           last_locked   = CAST(strftime('%s', 'now') AS INTEGER),
                           attempt_count = attempt_count + 1
                       WHERE job_id = ? AND job_status = ?""",
                    (JobStatus.PROCESSING.value, job_id, JobStatus.QUEUED.value),
                )
                return cur.rowcount == 1
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to lock job {job_id}") from e

    def unlock_job(self, job_id: int) -> bool:
        """Transitions a PROCESSING job back to QUEUED. Returns False if the job was not in PROCESSING state."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET job_status = ? WHERE job_id = ? AND job_status = ?",
                    (JobStatus.QUEUED.value, job_id, JobStatus.PROCESSING.value),
                )
                return cur.rowcount == 1
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to unlock job {job_id}") from e

    def complete_job(self, job_id: int, output_key: str) -> bool:
        """Sets status to DONE, stores output_key, and inserts a JobOutbox record — all in one transaction."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET job_status = ?, output_key = ? WHERE job_id = ?",
                    (JobStatus.DONE.value, output_key, job_id),
                )
                if cur.rowcount == 0:
                    raise JobNotFoundError(f"Job {job_id} not found")
                self.conn.execute(
                    "INSERT INTO JobOutbox (job_id) VALUES (?)", (job_id,)
                )
                return True
        except JobNotFoundError:
            raise
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to complete job {job_id}") from e

    def complete_preprocess_job(self, job_id: int, output_key: str, pet_id: uuid.UUID) -> int:
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET job_status = ?, output_key = ? WHERE job_id = ?",
                    (JobStatus.DONE.value, output_key, job_id),
                )
                if cur.rowcount == 0:
                    raise JobNotFoundError(f"Job {job_id} not found")
                self.conn.execute(
                    "INSERT INTO JobOutbox (job_id) VALUES (?)", (job_id,)
                )
                res = self.conn.execute(
                    "INSERT INTO Job (job_type, job_status, input_key, pet_id) VALUES (?, ?, ?, ?)",
                    (JobType.BACKGROUND_REMOVAL.value, JobStatus.QUEUED.value, output_key, str(pet_id)),
                )
                return res.lastrowid
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.ProgrammingError as e:
            raise FatalDatabaseError("Database schema mismatch") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError("Corrupt database file") from e

    def retry_job(self, job_id: int, retry_delay: float) -> bool:
        """Requeues a PROCESSING job, scheduling it no earlier than now + retry_delay seconds."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    """UPDATE Job
                       SET job_status = ?,
                           ready_at   = strftime('%Y-%m-%dT%H:%M:%fZ', 'now', ? || ' seconds')
                       WHERE job_id = ? AND job_status = ?""",
                    (JobStatus.QUEUED.value, retry_delay, job_id, JobStatus.PROCESSING.value),
                )
                return cur.rowcount == 1
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to retry job {job_id}") from e

    def fail_job(self, job_id: int, err_no: int) -> bool:
        """Sets status to FAILED, inserts a FailedJobs record, and inserts a JobOutbox record — all in one transaction."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET job_status = ? WHERE job_id = ?",
                    (JobStatus.FAILED.value, job_id),
                )
                if cur.rowcount == 0:
                    raise JobNotFoundError(f"Job {job_id} not found")
                self.conn.execute(
                    "INSERT INTO FailedJobs (job_id, err_no) VALUES (?, ?)",
                    (job_id, err_no),
                )
                self.conn.execute(
                    "INSERT INTO JobOutbox (job_id) VALUES (?)", (job_id,)
                )
                return True
        except JobNotFoundError:
            raise
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to fail job {job_id}") from e

    def reject_job(self, job_id: int) -> bool:
        """Sets status to REJECTED and inserts a JobOutbox record — all in one transaction."""
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET job_status = ? WHERE job_id = ?",
                    (JobStatus.REJECTED.value, job_id),
                )
                if cur.rowcount == 0:
                    raise JobNotFoundError(f"Job {job_id} not found")
                self.conn.execute(
                    "INSERT INTO JobOutbox (job_id) VALUES (?)", (job_id,)
                )
                return True
        except JobNotFoundError:
            raise
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to reject job {job_id}") from e

    def get_job_by_id(self, job_id: int) -> Job:
        try:
            row = self.conn.execute(
                "SELECT * FROM Job WHERE job_id = ?", (job_id,)
            ).fetchone()
            if row is None:
                raise JobNotFoundError(f"Job {job_id} not found")
            return Job.from_row(row)
        except JobNotFoundError:
            raise
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to get job {job_id}") from e

    def __get_next_in_queue(self, job_type: JobType) -> Optional[Job]:
        """Atomically dequeues the next eligible job: SELECT + lock UPDATE in one transaction."""
        try:
            with self.conn:
                row = self.conn.execute(
                    """SELECT * FROM Job
                       WHERE job_status = ? AND job_type = ?
                         AND ready_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                       ORDER BY ready_at ASC
                       LIMIT 1""",
                    (JobStatus.QUEUED.value, job_type.value),
                ).fetchone()
                if row is None:
                    return None
                job_id = row["job_id"]
                self.conn.execute(
                    """UPDATE Job
                       SET job_status    = ?,
                           last_locked   = CAST(strftime('%s', 'now') AS INTEGER),
                           attempt_count = attempt_count + 1
                       WHERE job_id = ?""",
                    (JobStatus.PROCESSING.value, job_id),
                )
                updated = self.conn.execute(
                    "SELECT * FROM Job WHERE job_id = ?", (job_id,)
                ).fetchone()
                return Job.from_row(updated)
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError("Failed to get next job from queue") from e

    def next_preprocess_job(self) -> Optional[Job]:
        return self.__get_next_in_queue(JobType.PREPROCESS)

    def next_background_removal_job(self) -> Optional[Job]:
        return self.__get_next_in_queue(JobType.BACKGROUND_REMOVAL)

    def set_output_key(self, job_id: int, output_key: str) -> bool:
        try:
            with self.conn:
                cur = self.conn.execute(
                    "UPDATE Job SET output_key = ? WHERE job_id = ?",
                    (output_key, job_id),
                )
                if cur.rowcount == 0:
                    raise JobNotFoundError(f"Job {job_id} not found")
                return True
        except JobNotFoundError:
            raise
        except sqlite3.OperationalError as e:
            raise FatalDatabaseError("Malformed SQL") from e
        except sqlite3.DatabaseError as e:
            raise FatalDatabaseError(f"Failed to set output key for job {job_id}") from e
