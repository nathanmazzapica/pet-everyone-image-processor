import sqlite3
import uuid
from datetime import datetime, timezone

import pytest

from src.models.errors import ErrorCode
from src.models.status import JobStatus, JobType
from src.repository.repository import Repository
from src.service.exceptions import FatalServiceError, JobFailedError
from src.service.preprocess_service import PreprocessService
from src.workers.preprocess_worker import Worker

FAKE_INPUT_KEY = "uploads/original/test_image"
FAKE_OUTPUT_KEY = "uploads/preprocessed/test_image"


def _seed_failure_code(conn: sqlite3.Connection, err_no: int) -> None:
    with conn:
        conn.execute(
            "INSERT OR IGNORE INTO FailureCodes (err_no, err_desc) VALUES (?, ?)",
            (err_no, f"Error {err_no}"),
        )


@pytest.fixture
def conn():
    return sqlite3.connect(":memory:")


@pytest.fixture
def repo(conn):
    r = Repository(conn)
    # Enable FK enforcement after schema is applied; FK checks only affect DML
    conn.execute("PRAGMA foreign_keys = ON")
    return r


@pytest.fixture
def mock_service(mocker):
    return mocker.MagicMock(spec=PreprocessService)


@pytest.fixture
def worker(repo, mock_service):
    return Worker(repo, mock_service)


@pytest.fixture
def pet_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def preprocess_job_id(repo, pet_id) -> int:
    return repo.create_preprocess_job(FAKE_INPUT_KEY, pet_id)


class TestPreprocessWorkerIntegration:

    def test_job_failed_error_marks_job_failed_and_creates_failedjobs_record(
        self, worker, repo, conn, preprocess_job_id, mock_service, mocker
    ):
        _seed_failure_code(conn, ErrorCode.ASSET_NOT_FOUND)
        mock_service.preprocess.side_effect = JobFailedError(
            "Image not found", status_code=ErrorCode.ASSET_NOT_FOUND
        )
        mocker.patch("src.workers.preprocess_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        job = repo.get_job_by_id(preprocess_job_id)
        assert job.status == JobStatus.FAILED

        row = conn.execute(
            "SELECT * FROM FailedJobs WHERE job_id = ?", (preprocess_job_id,)
        ).fetchone()
        assert row is not None
        assert row["job_id"] == preprocess_job_id
        assert row["err_no"] == ErrorCode.ASSET_NOT_FOUND

    def test_fatal_service_error_requeues_job_with_future_ready_at(
        self, worker, repo, conn, preprocess_job_id, mock_service
    ):
        mock_service.preprocess.side_effect = FatalServiceError(
            "Transient error", status_code=ErrorCode.UNKNOWN
        )

        with pytest.raises(FatalServiceError):
            worker.run()

        job = repo.get_job_by_id(preprocess_job_id)
        assert job.status == JobStatus.QUEUED
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        assert job.ready_at > now

    def test_fatal_service_error_fails_job_after_max_attempts(
        self, worker, repo, conn, preprocess_job_id, mock_service
    ):
        _seed_failure_code(conn, ErrorCode.UNKNOWN)
        # Set attempt_count so that after locking (which increments by 1) it reaches MAX_ATTEMPTS
        with conn:
            conn.execute(
                "UPDATE Job SET attempt_count = ? WHERE job_id = ?",
                (worker.MAX_ATTEMPTS - 1, preprocess_job_id),
            )

        mock_service.preprocess.side_effect = FatalServiceError(
            "Persistent fatal error", status_code=ErrorCode.UNKNOWN
        )

        with pytest.raises(FatalServiceError):
            worker.run()

        job = repo.get_job_by_id(preprocess_job_id)
        assert job.status == JobStatus.FAILED

        row = conn.execute(
            "SELECT * FROM FailedJobs WHERE job_id = ?", (preprocess_job_id,)
        ).fetchone()
        assert row is not None
        assert row["job_id"] == preprocess_job_id
        assert row["err_no"] == ErrorCode.UNKNOWN

    def test_successful_job_creates_bg_removal_job_sets_output_key_and_outbox_record(
        self, worker, repo, conn, preprocess_job_id, pet_id, mock_service, mocker
    ):
        mock_service.preprocess.return_value = FAKE_OUTPUT_KEY
        mocker.patch("src.workers.preprocess_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            rows = conn.execute("SELECT * FROM Job").fetchall()
            for row in rows:
                print(dict(row))
            worker.run()

        preprocess_job = repo.get_job_by_id(preprocess_job_id)
        assert preprocess_job.status == JobStatus.DONE
        assert preprocess_job.output_key == FAKE_OUTPUT_KEY

        bg_row = conn.execute(
            "SELECT * FROM Job WHERE job_type = ? AND input_key = ?",
            (JobType.BACKGROUND_REMOVAL.value, FAKE_OUTPUT_KEY),
        ).fetchone()
        assert bg_row is not None
        assert bg_row["job_status"] == JobStatus.QUEUED.value
        assert bg_row["pet_id"] == str(pet_id)

        outbox_row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (preprocess_job_id,)
        ).fetchone()
        assert outbox_row is not None