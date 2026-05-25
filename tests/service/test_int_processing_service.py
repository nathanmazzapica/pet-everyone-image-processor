import os

import pyvips
import pytest
import uuid

from src.service.exceptions import JobFailedError
from src.models.job import Job
from src.models.status import JobStatus
from src.service.image_processing_service import ImageProcessingService
from src.service.background_remover import BackgroundRemover
from src.storage.storage import LocalStorage


@pytest.fixture
def storage():
    return LocalStorage(base_path="tests/resources")

@pytest.fixture
def background_remover():
    return BackgroundRemover()

@pytest.fixture
def converter(mocker, storage, background_remover):
    return ImageProcessingService(storage, background_remover, mocker.Mock(), mocker.Mock())

def test_processing_service_saves_valid_image(converter, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    p = converter.submit_upload(b, uuid.uuid4())

    assert storage.exists(p)

def test_processing_service_rejects_invalid_image(converter, storage):
    with pytest.raises(JobFailedError):
        converter.submit_upload(b"\x10", uuid.uuid4())


def test_rejects_fake_jpeg_with_valid_magic_bytes(converter):
    fake_jpeg = b"\xFF\xD8\xFF" + b"not actually image data"

    with pytest.raises(JobFailedError):
        converter.submit_upload(fake_jpeg, uuid.uuid4())

def test_preprocess_image(converter, storage):
    path = "uploads/original/sample_original"
    assert storage.exists(path)
    job = Job(1, JobStatus.QUEUED, path, "", 0, None, 0, 0)
    assert converter.preprocess(job) == "uploads/preprocessed/sample_original"


def test_remove_background(converter, storage, background_remover):
    path = "uploads/preprocessed/sample_preprocessed"
    assert storage.exists(path)
    job = Job(1, JobStatus.QUEUED, path, "", 0, None, 0, 0)
    assert converter.remove_background(job) == "uploads/final/sample_preprocessed"

def test_full_pipeline(converter, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    img_id = uuid.uuid4()
    p = converter.submit_upload(b, img_id)
    assert storage.exists(p)
    j = Job(1, JobStatus.QUEUED, p, "", "",  0, None, 0)
    np = converter.preprocess(j)
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
    final = converter.remove_background(job)

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


