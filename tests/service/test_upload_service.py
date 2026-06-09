import uuid

import pytest

from src.models.errors import ErrorCode
from src.service.upload_service import UploadService
from src.service.exceptions import JobFailedError, FatalServiceError
from src.storage.storage import FatalStorageUploadError


FAKE_IMAGE_UUID = uuid.UUID("12345678-1234-5678-1234-567812345678")
FAKE_PET_UUID = uuid.UUID("87654321-4321-8765-4321-876543218765")

VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


@pytest.fixture
def mock_storage(mocker):
    return mocker.MagicMock()


@pytest.fixture
def mock_repo(mocker):
    mock = mocker.MagicMock()
    mock.create_preprocess_job.return_value = 1
    return mock


@pytest.fixture
def service(mock_storage, mock_repo):
    return UploadService(mock_storage, mock_repo)


class TestSubmitUpload:
    def test_raises_fatal_service_error_when_storage_is_full(self, service, mock_storage, mock_repo, mocker):
        mocker.patch.object(service, "_validate_upload")
        original = FatalStorageUploadError("disk full")
        mock_storage.upload_bytes.side_effect = original

        with pytest.raises(FatalServiceError) as exc_info:
            service.submit_upload(VALID_PNG, FAKE_PET_UUID)

        assert exc_info.value.__cause__ is original

    def test_marks_job_failed_on_fatal_storage_error(self, service, mock_storage, mock_repo, mocker):
        mocker.patch.object(service, "_validate_upload")
        mock_storage.upload_bytes.side_effect = FatalStorageUploadError("disk full")

        with pytest.raises(FatalServiceError):
            service.submit_upload(VALID_PNG, FAKE_PET_UUID)

        mock_repo.fail_job.assert_called_once_with(1, ErrorCode.DISK_FULL)
