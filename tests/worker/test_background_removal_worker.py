import uuid

import pytest

from src.models.job import Job
from src.models.status import JobStatus, JobType
from src.service.exceptions import FatalServiceError, JobFailedError
from src.workers.background_removal_worker import Worker

FAKE_INPUT_URL = "uploads/preprocessed/abc123"
FAKE_OUTPUT_PATH = "uploads/final/abc123"
_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_IMAGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_TS = "2024-01-01T00:00:00.000Z"


def make_job(attempt_count: int = 0) -> Job:
    return Job(
        id=1,
        job_type=JobType.BACKGROUND_REMOVAL,
        status=JobStatus.QUEUED,
        input_key=FAKE_INPUT_URL,
        pet_id=_PET_ID,
        image_id=_IMAGE_ID,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
        attempt_count=attempt_count,
    )


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
        mock_repo.next_background_removal_job.side_effect = [job, StopIteration()]
        mock_service.remove_background.return_value = FAKE_OUTPUT_PATH

        with pytest.raises(StopIteration):
            worker.run()

        assert worker.processed_jobs == 1

    def test_increments_failed_count_on_job_failed_error(self, worker, mock_repo, mock_service):
        job = make_job()
        mock_repo.next_background_removal_job.side_effect = [job, StopIteration()]
        mock_service.remove_background.side_effect = JobFailedError("bad image")

        with pytest.raises(StopIteration):
            worker.run()

        assert worker.failed_jobs == 1


    def test_raises_fatal_service_error(self, worker, mock_repo, mock_service):
        mock_repo.next_background_removal_job.return_value = make_job()
        mock_service.remove_background.side_effect = FatalServiceError("fatal!")

        with pytest.raises(FatalServiceError):
            worker.run()
