import sqlite3
import pytest
from src.models.job import Job
from src.models.status import JobStatus
from src.repository.repository import JobRepository

@pytest.fixture
def repository():
    conn = sqlite3.connect(":memory:")
    repo = JobRepository(conn)

    return repo

def test_repository_get_queued_job(repository):
    id1 = repository.create("1.png")
    id2 = repository.create("2.png")

    repository.update_status(id1, JobStatus.QUEUED)
    repository.update_status(id2, JobStatus.QUEUED)

    next = repository.get_next_in_queue()

    assert next.id == id1


    
