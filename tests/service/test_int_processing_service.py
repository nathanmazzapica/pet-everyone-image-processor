import os

import pyvips
import pytest
import uuid

from src.service.exceptions import JobFailedError
from src.models.job import Job
from src.models.status import JobStatus
from src.service.upload_service import UploadService
from src.service.preprocess_service import PreprocessService
from src.service.background_removal_service import BackgroundRemovalService
from src.service.processors.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage


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
def preprocess_service(mocker, storage):
    return PreprocessService(storage, mocker.Mock())

@pytest.fixture
def background_removal_service(mocker, storage, background_remover):
    return BackgroundRemovalService(storage, background_remover, mocker.Mock())

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
    job = Job(1, JobStatus.QUEUED, path, "", 0, None, 0, 0)
    assert preprocess_service.preprocess(job) == "uploads/preprocessed/sample_original"


def test_remove_background(background_removal_service, storage, background_remover):
    path = "uploads/preprocessed/sample_preprocessed"
    assert storage.exists(path)
    job = Job(1, JobStatus.QUEUED, path, "", 0, None, 0, 0)
    assert background_removal_service.remove_background(job) == "uploads/final/sample_preprocessed"

def test_full_pipeline(upload_service, preprocess_service, background_removal_service, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    img_id = uuid.uuid4()
    p = upload_service.submit_upload(b, img_id)
    assert storage.exists(p)
    j = Job(1, JobStatus.QUEUED, p, "", "",  0, None, 0)
    np = preprocess_service.preprocess(j)
    assert np == f"uploads/preprocessed/{img_id}"
    assert storage.exists(f"uploads/preprocessed/{img_id}")

    b2 = storage.open_bytes(np)
    orig = pyvips.Image.new_from_buffer(b, "")
    res = pyvips.Image.new_from_buffer(b2, "")
    assert res.get("vips-loader") == "webpload_buffer"

    assert b != b2

    assert res.width != orig.width
    assert res.height != orig.height

    job = Job(1, JobStatus.QUEUED, np, "", 0, None, 0, 0)
    final = background_removal_service.remove_background(job)

    assert final == f"uploads/final/{img_id}"
    assert storage.exists(f"uploads/final/{img_id}")
    assert storage.open_bytes(final) != b2
    assert storage.open_bytes(final) != b

    img = pyvips.Image.new_from_buffer(storage.open_bytes(final), "")
    assert img.get("vips-loader") == "webpload_buffer"
    assert img.hasalpha()



    # cleanup
    storage.delete(np)
    storage.delete(p)
