import pytest

from src.models.job import Job
from src.models.status import JobStatus
from src.service.exceptions import FatalServiceError, JobFailedError, JobRetryableError
from src.workers.background_removal_worker import Worker

FAKE_INPUT_URL = "uploads/preprocessed/abc123"
FAKE_OUTPUT_PATH = "uploads/final/abc123"


def make_job(attempt_count: int = 0) -> Job:
    return Job(1, JobStatus.QUEUED, FAKE_INPUT_URL, None, attempt_count, None, 0.0, 0.0)


@pytest.fixture
def mock_repo(mocker):
    repo = mocker.MagicMock()
    repo.lock_job.return_value = True
    return repo


@pytest.fixture
def mock_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def worker(mock_repo, mock_service):
    return Worker(mock_repo, mock_service)


class TestWorkerRun:
    def test_increments_processed_count_after_successful_job(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.remove_background.return_value = FAKE_OUTPUT_PATH

        with pytest.raises(StopIteration):
            worker.run()

        assert worker.processed_jobs == 1

    def test_increments_failed_count_on_job_failed_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.remove_background.side_effect = JobFailedError("bad image")

        with pytest.raises(StopIteration):
            worker.run()

        assert worker.failed_jobs == 1

    def test_increments_failed_count_on_job_retryable_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.remove_background.side_effect = JobRetryableError("transient failure")

        with pytest.raises(StopIteration):
            worker.run()

        assert worker.failed_jobs == 1

    def test_raises_fatal_service_error(self, worker, mock_repo, mock_service):
        mock_repo.get_next_in_queue.return_value = make_job()
        mock_service.remove_background.side_effect = FatalServiceError("fatal!")

        with pytest.raises(FatalServiceError):
            worker.run()
