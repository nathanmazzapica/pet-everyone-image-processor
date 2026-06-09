import uuid

import pytest

from src.models.job import Job
from src.models.status import JobStatus, JobType
from src.service.background_removal_service import BackgroundRemovalService
from src.service.exceptions import JobFailedError, FatalServiceError
from src.storage.storage import StorageError, FatalStorageUploadError, StorageConfigurationError


FAKE_INPUT_KEY = "uploads/preprocessed/abc123"
FAKE_OUTPUT_PATH = "uploads/final/abc123"
FAKE_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
FAKE_RESULT_BYTES = b"\x89PNG\r\n\x1a\n" + b"\xFF" * 64
_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_IMAGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_TS = "2024-01-01T00:00:00.000Z"


def make_job(input_key: str = FAKE_INPUT_KEY) -> Job:
    return Job(
        id=1,
        job_type=JobType.BACKGROUND_REMOVAL,
        status=JobStatus.QUEUED,
        input_key=input_key,
        pet_id=_PET_ID,
        image_id=_IMAGE_ID,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
    )


@pytest.fixture
def mock_storage(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_remover(mocker):
    remover = mocker.MagicMock()
    remover.process.return_value = FAKE_RESULT_BYTES
    return remover


@pytest.fixture
def service(mock_storage, mock_remover, mocker):
    return BackgroundRemovalService(mock_storage, mock_remover)


class TestRemoveBackground:
    def test_returns_final_path(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        job = make_job()

        result = service.remove_background(job)

        assert result == FAKE_OUTPUT_PATH

    def test_uploads_to_final_path(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        job = make_job()

        service.remove_background(job)

        mock_storage.upload_bytes.assert_called_once_with(FAKE_OUTPUT_PATH, FAKE_RESULT_BYTES)

    def test_strips_directory_prefix_from_input_key(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        job = make_job(input_key="uploads/preprocessed/some/nested/image_id")

        result = service.remove_background(job)

        assert result == "uploads/final/image_id"

    def test_raises_fatal_error_when_no_background_remover(self, mock_storage, mocker):
        svc = BackgroundRemovalService(mock_storage, None)

        with pytest.raises(FatalServiceError):
            svc.remove_background(make_job())

    def test_raises_job_failed_when_storage_open_raises_storage_error(self, service, mock_storage):
        mock_storage.open_bytes.side_effect = StorageError("disk read error")

        with pytest.raises(JobFailedError):
            service.remove_background(make_job())

    def test_job_failed_wraps_original_storage_error(self, service, mock_storage):
        original = StorageError("disk read error")
        mock_storage.open_bytes.side_effect = original

        with pytest.raises(JobFailedError) as exc_info:
            service.remove_background(make_job())

        assert exc_info.value.__cause__ is original

    def test_raises_fatal_error_when_storage_open_raises_memory_error(self, service, mock_storage):
        mock_storage.open_bytes.side_effect = MemoryError()

        with pytest.raises(FatalServiceError):
            service.remove_background(make_job())

    def test_raises_retryable_error_when_remover_raises(self, service, mock_storage, mock_remover):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mock_remover.process.side_effect = RuntimeError("model failure")

        with pytest.raises(FatalServiceError):
            service.remove_background(make_job())

    def test_retryable_error_wraps_remover_exception(self, service, mock_storage, mock_remover):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        original = RuntimeError("model failure")
        mock_remover.process.side_effect = original

        with pytest.raises(FatalServiceError) as exc_info:
            service.remove_background(make_job())

        assert exc_info.value.__cause__ is original

    def test_raises_retryable_error_when_upload_raises_os_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mock_storage.upload_bytes.side_effect = OSError("no space left on device")

        with pytest.raises(FatalServiceError):
            service.remove_background(make_job())

    def test_retryable_error_wraps_upload_os_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        original = OSError("no space left on device")
        mock_storage.upload_bytes.side_effect = original

        with pytest.raises(FatalServiceError) as exc_info:
            service.remove_background(make_job())

        assert exc_info.value.__cause__ is original

    def test_raises_fatal_error_when_upload_raises_storage_configuration_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mock_storage.upload_bytes.side_effect = StorageConfigurationError("bad permissions")

        with pytest.raises(FatalServiceError):
            service.remove_background(make_job())

    def test_fatal_error_wraps_storage_configuration_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        original = StorageConfigurationError("bad permissions")
        mock_storage.upload_bytes.side_effect = original

        with pytest.raises(FatalServiceError) as exc_info:
            service.remove_background(make_job())

        assert exc_info.value.__cause__ is original

    def test_raises_fatal_error_when_upload_raises_fatal_storage_upload_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mock_storage.upload_bytes.side_effect = FatalStorageUploadError("disk full")

        with pytest.raises(FatalServiceError):
            service.remove_background(make_job())

    def test_fatal_error_wraps_fatal_storage_upload_error(self, service, mock_storage):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        original = FatalStorageUploadError("disk full")
        mock_storage.upload_bytes.side_effect = original

        with pytest.raises(FatalServiceError) as exc_info:
            service.remove_background(make_job())

        assert exc_info.value.__cause__ is original
