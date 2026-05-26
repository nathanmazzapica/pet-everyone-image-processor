import pytest

from src.models.job import Job
from src.models.status import JobStatus
from src.workers.background_removal_worker import Worker


def test_worker_pulls_and_processes_queued_job(mocker):
    repo = mocker.Mock()
    proc = mocker.Mock()
    job = Job(1, JobStatus.QUEUED, "uploads/preprocessed/image", "", 0, None, 0, 0)
    repo.get_next_in_queue.side_effect = [job, StopIteration]
    repo.lock_job.return_value = True

    worker = Worker(repo, proc)
    with pytest.raises(StopIteration):
        worker.run()

    repo.lock_job.assert_called_once_with(job.id)
    proc.remove_background.assert_called_once_with(job)
    assert worker.processed_jobs == 1


def test_worker_skips_processing_when_job_lock_fails(mocker):
    repo = mocker.Mock()
    proc = mocker.Mock()
    job = Job(1, JobStatus.QUEUED, "uploads/preprocessed/image", "", 0, None, 0, 0)
    repo.get_next_in_queue.side_effect = [job, StopIteration]
    repo.lock_job.return_value = False

    worker = Worker(repo, proc)
    with pytest.raises(StopIteration):
        worker.run()

    proc.remove_background.assert_not_called()


def test_worker_marks_failed_jobs(mocker):
    repo = mocker.Mock()
    proc = mocker.Mock()
    job = Job(1, JobStatus.QUEUED, "uploads/preprocessed/image", "", 0, None, 0, 0)
    repo.get_next_in_queue.side_effect = [job, StopIteration]
    repo.lock_job.return_value = True
    proc.remove_background.side_effect = Exception("boom")

    worker = Worker(repo, proc)
    with pytest.raises(StopIteration):
        worker.run()

    repo.update_status.assert_called_once_with(job.id, JobStatus.FAILED)
    assert worker.failed_jobs == 1

