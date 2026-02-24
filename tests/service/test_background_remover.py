import pytest
from src.models.job import Job 
from src.models.status import JobStatus
from src.repository.repository import JobRepository
from src.service.background_remover import BackgroundRemover
from src.service.exceptions import InvalidJobError

@pytest.fixture
def service(mocker):
    mock_repository = mocker.Mock()
    mock_storage = mocker.Mock()
    mock_storage.exists.return_value = False

    service = BackgroundRemover(mock_repository, mock_storage)
    return service

@pytest.fixture
def dummy_job():
    return Job(1, JobStatus.QUEUED, "apple.jpg", None, 0, None, 0, 0)

@pytest.fixture
def rejected_job():
    return Job(2, JobStatus.REJECTED, "apple.jpg", None, 0, None, 0, 0)


def test_process_raises_exception_on_file_not_exists(service, dummy_job):
    with pytest.raises(FileNotFoundError):
        service.process(dummy_job)

def test_proccess_raises_invalid_job_exception_on_not_queued_job(service, rejected_job):
    with pytest.raises(InvalidJobError):
        service.process(rejected_job)



