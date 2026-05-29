import shutil
import sqlite3

import pytest

from src.models.status import JobStatus
from src.repository.job_repository import JobRepository
from src.service.background_removal_service import BackgroundRemovalService
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage
from src.workers.background_removal_worker import Worker

SAMPLE_PREPROCESSED = "tests/resources/uploads/preprocessed/sample_preprocessed"
INPUT_URL = "uploads/preprocessed/test_job"
EXPECTED_OUTPUT_URL = "uploads/final/test_job"


@pytest.fixture(scope="module")
def background_remover():
    return BackgroundRemover()


@pytest.fixture
def storage(tmp_path):
    dest = tmp_path / "uploads" / "preprocessed"
    dest.mkdir(parents=True)
    shutil.copy(SAMPLE_PREPROCESSED, dest / "test_job")
    return LocalStorage(base_path=str(tmp_path))


@pytest.fixture
def repo():
    conn = sqlite3.connect(":memory:")
    return JobRepository(conn)


@pytest.fixture
def worker(repo, storage, background_remover):
    service = BackgroundRemovalService(storage, background_remover, repo)
    return Worker(repo, service)


def test_worker_processes_queued_job(worker, repo, storage, mocker):
    job_id = repo.create(INPUT_URL)

    mocker.patch("src.workers.background_removal_worker.sleep", side_effect=StopIteration)

    with pytest.raises(StopIteration):
        worker.run()

    job = repo.get_by_id(job_id)
    assert job.status == JobStatus.DONE
    assert job.output_url == EXPECTED_OUTPUT_URL
    assert storage.exists(EXPECTED_OUTPUT_URL)
