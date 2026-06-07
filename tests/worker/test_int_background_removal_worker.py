import sqlite3
import uuid
from datetime import datetime, timezone

import pytest

from src.models.errors import ErrorCode
from src.models.status import JobStatus
from src.repository.repository import Repository
from src.service.background_removal_service import BackgroundRemovalService
from src.service.exceptions import FatalServiceError, JobFailedError
from src.workers.background_removal_worker import Worker

FAKE_INPUT_KEY = "uploads/preprocessed/test_image"
FAKE_OUTPUT_KEY = "uploads/final/test_image"


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
    conn.execute("PRAGMA foreign_keys = ON")
    return r


@pytest.fixture
def mock_service(mocker):
    return mocker.MagicMock(spec=BackgroundRemovalService)


@pytest.fixture
def worker(repo, mock_service):
    return Worker(repo, mock_service)


@pytest.fixture
def pet_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def bg_removal_job_id(repo, pet_id) -> int:
    return repo.create_background_removal_job(FAKE_INPUT_KEY, pet_id)


class TestBackgroundRemovalWorkerIntegration:

    def test_job_failed_error_marks_job_failed_and_creates_failedjobs_record(
        self, worker, repo, conn, bg_removal_job_id, mock_service, mocker
    ):
        _seed_failure_code(conn, ErrorCode.ASSET_NOT_FOUND)
        mock_service.remove_background.side_effect = JobFailedError(
            "Image not found", status_code=ErrorCode.ASSET_NOT_FOUND
        )
        mocker.patch("src.workers.background_removal_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        job = repo.get_job_by_id(bg_removal_job_id)
        assert job.status == JobStatus.FAILED

        row = conn.execute(
            "SELECT * FROM FailedJobs WHERE job_id = ?", (bg_removal_job_id,)
        ).fetchone()
        assert row is not None
        assert row["job_id"] == bg_removal_job_id
        assert row["err_no"] == ErrorCode.ASSET_NOT_FOUND

    def test_fatal_service_error_requeues_job_with_future_ready_at(
        self, worker, repo, conn, bg_removal_job_id, mock_service
    ):
        mock_service.remove_background.side_effect = FatalServiceError(
            "Transient error", status_code=ErrorCode.UNKNOWN
        )

        with pytest.raises(FatalServiceError):
            worker.run()

        job = repo.get_job_by_id(bg_removal_job_id)
        assert job.status == JobStatus.QUEUED
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        assert job.ready_at > now

    def test_fatal_service_error_fails_job_after_max_attempts(
        self, worker, repo, conn, bg_removal_job_id, mock_service
    ):
        _seed_failure_code(conn, ErrorCode.UNKNOWN)
        with conn:
            conn.execute(
                "UPDATE Job SET attempt_count = ? WHERE job_id = ?",
                (worker.MAX_ATTEMPTS - 1, bg_removal_job_id),
            )

        mock_service.remove_background.side_effect = FatalServiceError(
            "Persistent fatal error", status_code=ErrorCode.UNKNOWN
        )

        with pytest.raises(FatalServiceError):
            worker.run()

        job = repo.get_job_by_id(bg_removal_job_id)
        assert job.status == JobStatus.FAILED

        row = conn.execute(
            "SELECT * FROM FailedJobs WHERE job_id = ?", (bg_removal_job_id,)
        ).fetchone()
        assert row is not None
        assert row["job_id"] == bg_removal_job_id
        assert row["err_no"] == ErrorCode.UNKNOWN

    def test_successful_job_sets_output_key_and_creates_outbox_record(
        self, worker, repo, conn, bg_removal_job_id, mock_service, mocker
    ):
        mock_service.remove_background.return_value = FAKE_OUTPUT_KEY
        mocker.patch("src.workers.background_removal_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        job = repo.get_job_by_id(bg_removal_job_id)
        assert job.status == JobStatus.DONE
        assert job.output_key == FAKE_OUTPUT_KEY

        outbox_row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (bg_removal_job_id,)
        ).fetchone()
        assert outbox_row is not None