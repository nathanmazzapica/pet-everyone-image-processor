import pytest

from src.models.job import Job
from src.models.status import JobStatus
from src.service.exceptions import FatalServiceError, JobFailedError, JobRetryableError
from src.workers.preprocess_worker import Worker

FAKE_INPUT_URL = "uploads/original/abc123"
FAKE_OUTPUT_PATH = "uploads/preprocessed/abc123"


def make_job(attempt_count: int = 0) -> Job:
    return Job(1, JobStatus.QUEUED, FAKE_INPUT_URL, None, attempt_count, None, 0.0, 0.0)


@pytest.fixture
def mock_repo(mocker):
    repo = mocker.MagicMock()
    repo.lock_job.return_value = True
    return repo


@pytest.fixture
def mock_job_repo(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_service(mocker):
    return mocker.MagicMock()


@pytest.fixture
def worker(mock_repo, mock_job_repo, mock_service):
    return Worker(mock_repo, mock_job_repo, mock_service)


class TestWorkerRun:
    def test_increments_processed_count_after_successful_job(self, worker, mock_repo, mock_job_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.preprocess.return_value = FAKE_OUTPUT_PATH

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.update_output_url.assert_called_once_with(job.id, FAKE_OUTPUT_PATH)
        mock_repo.update_status.assert_called_once_with(job.id, JobStatus.DONE)
        mock_job_repo.create.assert_called_once_with(FAKE_OUTPUT_PATH)
        assert worker.processed_jobs == 1

    def test_increments_failed_count_on_job_failed_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.preprocess.side_effect = JobFailedError("bad image")

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.update_status.assert_called_once_with(job.id, JobStatus.FAILED)
        assert worker.failed_jobs == 1

    def test_requeues_retryable_error_and_increments_attempt_count(self, worker, mock_repo, mock_service):
        job = make_job(attempt_count=1)
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.preprocess.side_effect = JobRetryableError("transient failure")

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.update_attempt_count.assert_called_once_with(job.id, 2)
        mock_repo.update_status.assert_called_once_with(job.id, JobStatus.QUEUED)
        assert worker.failed_jobs == 1

    def test_marks_retryable_error_as_failed_after_max_attempts(self, worker, mock_repo, mock_service):
        job = make_job(attempt_count=3)
        mock_repo.get_next_in_queue.side_effect = [job, StopIteration()]
        mock_service.preprocess.side_effect = JobRetryableError("transient failure")

        with pytest.raises(StopIteration):
            worker.run()

        mock_repo.update_attempt_count.assert_not_called()
        mock_repo.update_status.assert_called_once_with(job.id, JobStatus.FAILED)
        assert worker.failed_jobs == 1

    def test_raises_fatal_service_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.get_next_in_queue.return_value = job
        mock_service.preprocess.side_effect = FatalServiceError("fatal!")

        with pytest.raises(FatalServiceError):
            worker.run()

        mock_repo.update_status.assert_called_once_with(job.id, JobStatus.QUEUED)
