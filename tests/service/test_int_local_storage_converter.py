import os

import pyvips
import pytest

from service.exceptions import JobFailedError
from src.models.image_format import ImageFormat
from src.models.job import Job
from src.models.status import JobStatus
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.image_converter import ImageConverter
from storage.storage import LocalStorage


@pytest.fixture
def storage():
    return LocalStorage(base_path="tests/resources")


@pytest.fixture
def converter(mocker, storage):
    return ImageConverter(mocker.Mock(), storage)

def test_convert_raises_exception_on_invalid_format(converter, storage):
    job = Job(1, JobStatus.QUEUED, "sample.bin", None, None, 0, None, 0, 0)
    with pytest.raises(InvalidImageFormatError):
        converter.convert(job.input_url)

def test_convert_converts_to_webp(converter, storage):
    job = Job(1, JobStatus.QUEUED, "sample.jpg", None, None, 0, None, 0, 0)
    result = converter.convert(job.input_url)
    assert result == os.path.join(storage.base_path, "tmp", "sample-pre.webp")

def test_convert_resizes_image(converter, storage):
    job = Job(1, JobStatus.QUEUED, "sample.jpg", None, None, 0, None, 100, 100)
    result = converter.convert(job.input_url)
    assert result is not None
    original = pyvips.Image.new_from_file("tests/resources/sample.jpg")
    image = pyvips.Image.new_from_file(result)
    assert image.width <= 720
    assert image.height <= 1280
    assert original.width > image.width
    assert original.height > image.height

def test_small_image_does_not_resize(converter, storage):
    job = Job(1, JobStatus.QUEUED, "small.jpg", None, None, 0, None, 10, 10)
    result = converter.convert(job.input_url)
    assert result is not None
    original = pyvips.Image.new_from_file("tests/resources/small.jpg")
    image = pyvips.Image.new_from_file(result)
    assert image.width == original.width
    assert image.height == original.height


def test_invalid_image_raises_exception(converter, storage):
    job = Job(1, JobStatus.QUEUED, "fake.jpg", None, None, 0, None, 0, 0)
    with pytest.raises(InvalidImageFormatError):
        converter.convert(job.input_url)