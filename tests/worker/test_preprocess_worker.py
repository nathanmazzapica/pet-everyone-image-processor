import uuid

import pytest

from src.models.job import Job
from src.models.status import JobStatus, JobType
from src.service.exceptions import FatalServiceError, JobFailedError
from src.workers.preprocess_worker import Worker

FAKE_INPUT_KEY = "uploads/original/abc123"
FAKE_OUTPUT_PATH = "uploads/preprocessed/abc123"
_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_IMAGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_TS = "2024-01-01T00:00:00.000Z"


def make_job(attempt_count: int = 0) -> Job:
    return Job(
        id=1,
        job_type=JobType.PREPROCESS,
        status=JobStatus.QUEUED,
        input_key=FAKE_INPUT_KEY,
        pet_id=_PET_ID,
        image_id=_IMAGE_ID,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
        attempt_count=attempt_count,
    )


@pytest.fixture
def mock_repo(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def worker(mock_repo, mock_service):
    return Worker(mock_repo, mock_service)


class TestWorkerRun:
    def test_increments_processed_count_after_successful_job(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.next_preprocess_job.side_effect = [job, StopIteration()]
        mock_service.preprocess.return_value = FAKE_OUTPUT_PATH

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.complete_preprocess_job.assert_called_once_with(job.id, FAKE_OUTPUT_PATH, job.pet_id, job.image_id)
        assert worker.processed_jobs == 1

    def test_increments_failed_count_on_job_failed_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.next_preprocess_job.side_effect = [job, StopIteration()]
        mock_service.preprocess.side_effect = JobFailedError("bad image", status_code=4)

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.fail_job.assert_called_once_with(job.id, 4)
        assert worker.failed_jobs == 1

    def test_fatal_service_error_retries_when_below_max_attempts(self, worker, mock_repo, mock_service):
        job = make_job(attempt_count=1)
        mock_repo.next_preprocess_job.return_value = job
        mock_service.preprocess.side_effect = FatalServiceError("transient failure", status_code=9)

        with pytest.raises(FatalServiceError):
            worker.run()

        mock_repo.retry_job.assert_called_once_with(job.id, worker.RETRY_DELAY)
        mock_repo.fail_job.assert_not_called()

    def test_fatal_service_error_fails_job_after_max_attempts(self, worker, mock_repo, mock_service):
        job = make_job(attempt_count=3)
        mock_repo.next_preprocess_job.return_value = job
        mock_service.preprocess.side_effect = FatalServiceError("persistent failure", status_code=9)

        with pytest.raises(FatalServiceError):
            worker.run()

        mock_repo.fail_job.assert_called_once_with(job.id, 9)
        mock_repo.retry_job.assert_not_called()
        assert worker.failed_jobs == 1
