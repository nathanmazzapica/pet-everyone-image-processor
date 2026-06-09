import uuid

import pyvips
import pytest

from src.models.job import Job
from src.models.status import JobStatus, JobType
from src.service.exceptions import JobFailedError
from src.service.upload_service import UploadService
from src.service.preprocess_service import PreprocessService
from src.service.background_removal_service import BackgroundRemovalService
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage

_TS = "2024-01-01T00:00:00.000Z"
_PET_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_IMAGE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


@pytest.fixture
def storage():
    return LocalStorage(base_path="tests/resources")


@pytest.fixture
def background_remover():
    return BackgroundRemover()


@pytest.fixture
def upload_service(mocker, storage):
    return UploadService(storage, mocker.Mock())


@pytest.fixture
def preprocess_service(storage):
    return PreprocessService(storage)


@pytest.fixture
def background_removal_service(mocker, storage, background_remover):
    return BackgroundRemovalService(storage, background_remover)


def test_processing_service_saves_valid_image(upload_service, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    p = upload_service.submit_upload(b, uuid.uuid4())

    assert storage.exists(p)


def test_processing_service_rejects_invalid_image(upload_service, storage):
    with pytest.raises(JobFailedError):
        upload_service.submit_upload(b"\x10", uuid.uuid4())


def test_rejects_fake_jpeg_with_valid_magic_bytes(upload_service):
    fake_jpeg = b"\xFF\xD8\xFF" + b"not actually image data"

    with pytest.raises(JobFailedError):
        upload_service.submit_upload(fake_jpeg, uuid.uuid4())


def test_preprocess_image(preprocess_service, storage):
    path = "uploads/original/sample_original"
    assert storage.exists(path)
    job = Job(
        id=1,
        job_type=JobType.PREPROCESS,
        status=JobStatus.QUEUED,
        input_key=path,
        pet_id=_PET_ID,
        image_id=_IMAGE_ID,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
    )
    assert preprocess_service.preprocess(job) == f"uploads/pet_images/{_PET_ID}/{_IMAGE_ID}/preprocessed.webp"


def test_remove_background(background_removal_service, storage):
    path = "uploads/preprocessed/sample_preprocessed"
    assert storage.exists(path)
    job = Job(
        id=1,
        job_type=JobType.BACKGROUND_REMOVAL,
        status=JobStatus.QUEUED,
        input_key=path,
        pet_id=_PET_ID,
        image_id=_IMAGE_ID,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
    )
    assert background_removal_service.remove_background(job) == f"uploads/pet_images/{_PET_ID}/{_IMAGE_ID}/final.webp"


def test_full_pipeline(upload_service, preprocess_service, background_removal_service, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    pet_id = uuid.uuid4()
    p = upload_service.submit_upload(b, pet_id)
    assert storage.exists(p)

    # path format: uploads/pet_images/{pet_id}/{image_id}/original
    image_id = uuid.UUID(p.split("/")[-2])

    preprocess_job = Job(
        id=1,
        job_type=JobType.PREPROCESS,
        status=JobStatus.QUEUED,
        input_key=p,
        pet_id=pet_id,
        image_id=image_id,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
    )
    np = preprocess_service.preprocess(preprocess_job)
    assert np == f"uploads/pet_images/{pet_id}/{image_id}/preprocessed.webp"
    assert storage.exists(np)

    b2 = storage.open_bytes(np)
    orig = pyvips.Image.new_from_buffer(b, "")
    res = pyvips.Image.new_from_buffer(b2, "")
    assert res.get("vips-loader") == "webpload_buffer"
    assert b != b2
    assert res.width != orig.width
    assert res.height != orig.height

    bg_job = Job(
        id=1,
        job_type=JobType.BACKGROUND_REMOVAL,
        status=JobStatus.QUEUED,
        input_key=np,
        pet_id=pet_id,
        image_id=image_id,
        created_at=_TS,
        updated_at=_TS,
        ready_at=_TS,
    )
    final = background_removal_service.remove_background(bg_job)

    assert final == f"uploads/pet_images/{pet_id}/{image_id}/final.webp"
    assert storage.exists(final)
    assert storage.open_bytes(final) != b2
    assert storage.open_bytes(final) != b

    img = pyvips.Image.new_from_buffer(storage.open_bytes(final), "")
    assert img.get("vips-loader") == "webpload_buffer"
    assert img.hasalpha()

    # cleanup
    storage.delete(np)
    storage.delete(p)
