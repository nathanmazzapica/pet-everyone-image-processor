import sqlite3
import uuid

import pyvips
import pytest

from src.messaging.publisher import Publisher
from src.models.status import JobStatus, JobType
from src.models.status_update import JobSucceededUpdate
from src.repository.repository import Repository
from src.service.background_removal_service import BackgroundRemovalService
from src.service.preprocess_service import PreprocessService
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage
from src.workers.background_removal_worker import Worker as BGRemovalWorker
from src.workers.outbox_worker import OutboxWorker
from src.workers.preprocess_worker import Worker as PreprocessWorker

ORIGINAL_INPUT_KEY = "uploads/original/sample_original"


@pytest.fixture
def conn():
    return sqlite3.connect(":memory:")


@pytest.fixture
def repo(conn):
    r = Repository(conn)
    conn.execute("PRAGMA foreign_keys = ON")
    return r


@pytest.fixture
def storage():
    return LocalStorage(base_path="tests/resources")


@pytest.fixture
def mock_publisher(mocker):
    return mocker.MagicMock(spec=Publisher)


class TestFullPipelineIntegration:

    def test_full_pipeline_preprocess_bg_removal_outbox(
        self, repo, conn, storage, mock_publisher, mocker
    ):
        mocker.patch("src.workers.preprocess_worker.sleep", side_effect=StopIteration)
        mocker.patch("src.workers.background_removal_worker.sleep", side_effect=StopIteration)
        mocker.patch("src.workers.outbox_worker.sleep", side_effect=StopIteration)

        pet_id = uuid.uuid4()
        image_id = uuid.uuid4()
        preprocessed_key = f"uploads/pet_images/{pet_id}/{image_id}/preprocessed.webp"
        final_key = f"uploads/pet_images/{pet_id}/{image_id}/final.webp"

        try:
            # --- Step 1: Create and process preprocess job ---
            preprocess_job_id = repo.create_preprocess_job(ORIGINAL_INPUT_KEY, pet_id, image_id)

            with pytest.raises(StopIteration):
                PreprocessWorker(repo, PreprocessService(storage)).run()

            preprocess_job = repo.get_job_by_id(preprocess_job_id)
            assert preprocess_job.status == JobStatus.DONE
            assert preprocess_job.output_key == preprocessed_key
            assert storage.exists(preprocessed_key)
            preprocessed_img = pyvips.Image.new_from_buffer(storage.open_bytes(preprocessed_key), "")
            assert preprocessed_img.get("vips-loader") == "webpload_buffer"

            bg_row = conn.execute(
                "SELECT * FROM Job WHERE job_type = ? AND input_key = ?",
                (JobType.BACKGROUND_REMOVAL.value, preprocessed_key),
            ).fetchone()
            assert bg_row is not None
            bg_job_id = bg_row["job_id"]

            assert conn.execute(
                "SELECT 1 FROM JobOutbox WHERE job_id = ?", (preprocess_job_id,)
            ).fetchone() is not None

            # --- Step 2: Outbox publishes preprocess completion ---
            outbox_worker = OutboxWorker(mock_publisher, repo)
            with pytest.raises(StopIteration):
                outbox_worker.run()

            mock_publisher.publish.assert_called_once()
            update = mock_publisher.publish.call_args[0][0]
            assert isinstance(update, JobSucceededUpdate)
            assert update.id == preprocess_job_id
            assert conn.execute(
                "SELECT 1 FROM JobOutbox WHERE job_id = ?", (preprocess_job_id,)
            ).fetchone() is None

            # --- Step 3: Process BG removal job ---
            with pytest.raises(StopIteration):
                BGRemovalWorker(repo, BackgroundRemovalService(storage, BackgroundRemover())).run()

            bg_job = repo.get_job_by_id(bg_job_id)
            assert bg_job.status == JobStatus.DONE
            assert bg_job.output_key == final_key
            assert storage.exists(final_key)
            final_img = pyvips.Image.new_from_buffer(storage.open_bytes(final_key), "")
            assert final_img.get("vips-loader") == "webpload_buffer"
            assert final_img.hasalpha()

            assert conn.execute(
                "SELECT 1 FROM JobOutbox WHERE job_id = ?", (bg_job_id,)
            ).fetchone() is not None

            # --- Step 4: Outbox publishes BG removal completion ---
            mock_publisher.reset_mock()
            with pytest.raises(StopIteration):
                outbox_worker.run()

            mock_publisher.publish.assert_called_once()
            update = mock_publisher.publish.call_args[0][0]
            assert isinstance(update, JobSucceededUpdate)
            assert update.id == bg_job_id
            assert conn.execute(
                "SELECT 1 FROM JobOutbox WHERE job_id = ?", (bg_job_id,)
            ).fetchone() is None

        finally:
            if storage.exists(preprocessed_key):
                storage.delete(preprocessed_key)
            if storage.exists(final_key):
                storage.delete(final_key)
