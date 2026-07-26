import logging
import sqlite3
import uuid

import pytest

from src.messaging.exceptions import (
    PublisherConfigurationError,
    PublisherConnectionError,
    PublisherInvalidPayloadError,
)
from src.messaging.publisher import Publisher
from src.models.errors import ErrorCode
from src.models.status import JobStatus
from src.models.status_update import JobFailedUpdate, JobSucceededUpdate
from src.repository.repository import Repository
from src.workers.outbox_worker import OutboxWorker

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
    conn.execute("PRAGMA foreign_keys = ON")
    return r


@pytest.fixture
def mock_publisher(mocker):
    return mocker.MagicMock(spec=Publisher)


@pytest.fixture
def worker(repo, mock_publisher):
    return OutboxWorker(mock_publisher, repo)


@pytest.fixture
def pet_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def image_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def done_job_id(repo, pet_id, image_id) -> int:
    job_id = repo.create_preprocess_job(FAKE_INPUT_KEY, pet_id, image_id)
    repo.complete_job(job_id, FAKE_OUTPUT_KEY)
    return job_id


@pytest.fixture
def failed_job_id(repo, conn, pet_id, image_id) -> int:
    _seed_failure_code(conn, ErrorCode.UNKNOWN)
    job_id = repo.create_preprocess_job(FAKE_INPUT_KEY, pet_id, image_id)
    repo.fail_job(job_id, ErrorCode.UNKNOWN)
    return job_id


class TestOutboxWorkerIntegration:

    def test_no_jobs_sleeps_for_idle_sleep_and_does_not_publish(
        self, worker, mock_publisher, mocker
    ):
        sleep_mock = mocker.patch("src.workers.outbox_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        mock_publisher.publish.assert_not_called()
        sleep_mock.assert_called_once_with(worker.IDLE_SLEEP)

    def test_done_job_publishes_job_succeeded_update_and_removes_outbox_row(
        self, worker, mock_publisher, conn, done_job_id, mocker
    ):
        mocker.patch("src.workers.outbox_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        mock_publisher.publish.assert_called_once()
        update = mock_publisher.publish.call_args[0][0]
        assert isinstance(update, JobSucceededUpdate)
        assert update.id == done_job_id
        assert update.output_key == FAKE_OUTPUT_KEY
        assert update.status == JobStatus.DONE

        row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (done_job_id,)
        ).fetchone()
        assert row is None

    def test_failed_job_publishes_job_failed_update_with_error_code_and_removes_outbox_row(
        self, worker, mock_publisher, conn, failed_job_id, mocker
    ):
        mocker.patch("src.workers.outbox_worker.sleep", side_effect=StopIteration)

        with pytest.raises(StopIteration):
            worker.run()

        mock_publisher.publish.assert_called_once()
        update = mock_publisher.publish.call_args[0][0]
        assert isinstance(update, JobFailedUpdate)
        assert update.id == failed_job_id
        assert update.error_code == ErrorCode.UNKNOWN
        assert update.status == JobStatus.FAILED

        row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (failed_job_id,)
        ).fetchone()
        assert row is None

    def test_connection_error_logs_warning_sleeps_retry_and_does_not_delete_outbox_row(
        self, worker, mock_publisher, conn, done_job_id, mocker, caplog
    ):
        mock_publisher.publish.side_effect = PublisherConnectionError
        sleep_mock = mocker.patch("src.workers.outbox_worker.sleep", side_effect=StopIteration)

        with caplog.at_level(logging.WARNING, logger="src.workers.outbox_worker"):
            with pytest.raises(StopIteration):
                worker.run()

        sleep_mock.assert_called_once_with(worker.RETRY_SLEEP)
        assert any("Connection error" in r.message for r in caplog.records)

        row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (done_job_id,)
        ).fetchone()
        assert row is not None

    def test_configuration_error_logs_error_raises_and_does_not_delete_outbox_row(
        self, worker, mock_publisher, conn, done_job_id, caplog
    ):
        mock_publisher.publish.side_effect = PublisherConfigurationError

        with caplog.at_level(logging.ERROR, logger="src.workers.outbox_worker"):
            with pytest.raises(PublisherConfigurationError):
                worker.run()

        assert any(r.levelno == logging.ERROR for r in caplog.records)

        row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (done_job_id,)
        ).fetchone()
        assert row is not None

    def test_invalid_payload_error_logs_error_raises_and_does_not_delete_outbox_row(
        self, worker, mock_publisher, conn, done_job_id, caplog
    ):
        mock_publisher.publish.side_effect = PublisherInvalidPayloadError

        with caplog.at_level(logging.ERROR, logger="src.workers.outbox_worker"):
            with pytest.raises(PublisherInvalidPayloadError):
                worker.run()

        assert any(r.levelno == logging.ERROR for r in caplog.records)

        row = conn.execute(
            "SELECT * FROM JobOutbox WHERE job_id = ?", (done_job_id,)
        ).fetchone()
        assert row is not None
