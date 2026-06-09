import uuid

import pytest

from src.models.job import Job
from src.models.status import JobStatus, JobType
from src.service.preprocess_service import PreprocessService
from src.service.exceptions import JobFailedError, FatalServiceError, InvalidImageFormatError
from src.storage.storage import StorageError, FatalStorageUploadError, StorageConfigurationError, AssetNotFoundError


FAKE_INPUT_KEY = "uploads/original/abc123"
FAKE_OUTPUT_PATH = "uploads/preprocessed/abc123"
FAKE_IMAGE_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
FAKE_RESULT_BYTES = b"\x89PNG\r\n\x1a\n" + b"\xFF" * 64
_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_IMAGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
_TS = "2024-01-01T00:00:00.000Z"


def make_job(input_key: str = FAKE_INPUT_KEY) -> Job:
    return Job(
        id=1,
        job_type=JobType.PREPROCESS,
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
def service(mock_storage):
    return PreprocessService(mock_storage)


class TestPreprocess:
    def test_returns_preprocessed_path(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)

        result = service.preprocess(make_job())

        assert result == FAKE_OUTPUT_PATH

    def test_uploads_to_preprocessed_path(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)

        service.preprocess(make_job())

        mock_storage.upload_bytes.assert_called_once_with(FAKE_OUTPUT_PATH, FAKE_RESULT_BYTES)

    def test_raises_job_failed_when_storage_open_raises_storage_error(self, service, mock_storage):
        mock_storage.open_bytes.side_effect = StorageError("disk read error")

        with pytest.raises(JobFailedError):
            service.preprocess(make_job())

    def test_raises_fatal_error_when_storage_open_raises_memory_error(self, service, mock_storage):
        mock_storage.open_bytes.side_effect = MemoryError()

        with pytest.raises(FatalServiceError):
            service.preprocess(make_job())

    def test_raises_job_failed_when_convert_raises_invalid_image_error(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch(
            "src.service.preprocess_service.convert",
            side_effect=InvalidImageFormatError("invalid"),
        )

        with pytest.raises(JobFailedError):
            service.preprocess(make_job())

    def test_raises_fatal_error_when_upload_raises_os_error(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)
        mock_storage.upload_bytes.side_effect = OSError("temporary failure")

        with pytest.raises(FatalServiceError):
            service.preprocess(make_job())

    def test_raises_fatal_error_when_upload_raises_storage_configuration_error(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)
        mock_storage.upload_bytes.side_effect = StorageConfigurationError("bad permissions")

        with pytest.raises(FatalServiceError):
            service.preprocess(make_job())

    def test_raises_fatal_error_when_upload_raises_fatal_storage_upload_error(self, service, mock_storage, mocker):
        mock_storage.open_bytes.return_value = FAKE_IMAGE_BYTES
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)
        mock_storage.upload_bytes.side_effect = FatalStorageUploadError("disk full")

        with pytest.raises(FatalServiceError):
            service.preprocess(make_job())

    def test_raises_job_failed_error_when_storage_open_raises_asset_not_found_error(self, service, mock_storage, mocker):
        mock_storage.open_bytes.side_effect = AssetNotFoundError("file not found")
        mocker.patch("src.service.preprocess_service.convert", return_value=FAKE_RESULT_BYTES)
        with pytest.raises(JobFailedError):
            service.preprocess(make_job())
