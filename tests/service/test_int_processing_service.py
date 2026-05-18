import os

import pyvips
import pytest

from src.service.exceptions import JobFailedError
from src.models.job import Job
from src.models.status import JobStatus
from src.service.image_processing_service import ImageProcessingService
from storage.storage import LocalStorage


@pytest.fixture
def storage():
    return LocalStorage(base_path="tests/resources")


@pytest.fixture
def converter(mocker, storage):
    return ImageProcessingService(storage, mocker.Mock(), mocker.Mock())

def test_processing_service_saves_valid_image(converter, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    p = converter.submit_upload(b)

    assert storage.exists(p)

def test_processing_service_rejects_invalid_image(converter, storage):
    with pytest.raises(JobFailedError):
        converter.submit_upload(b"\x10")


def test_rejects_fake_jpeg_with_valid_magic_bytes(converter):
    fake_jpeg = b"\xFF\xD8\xFF" + b"not actually image data"

    with pytest.raises(JobFailedError):
        converter.submit_upload(fake_jpeg)

def test_preprocesses_image(converter, storage):
    with open("tests/resources/sample.jpg", "rb") as f:
        b = f.read()
    p = converter.submit_upload(b)
    uuid = p.split("/")[-1]
    assert storage.exists(p)
    j = Job(1, JobStatus.QUEUED, p, "", "",  0, None, 0, 0)
    np = converter.run_preprocessing(j)
    assert np == f"uploads/preprocessed/{uuid}"
    assert storage.exists(f"uploads/preprocessed/{uuid}")

    b2 = storage.open_bytes(np)
    orig = pyvips.Image.new_from_buffer(b, "")
    res = pyvips.Image.new_from_buffer(b2, "")
    assert res.get("vips-loader") == "webpload_buffer"

    assert b != b2

    assert res.width != orig.width
    assert res.height != orig.height

    # cleanup
    storage.delete(np)
    storage.delete(p)