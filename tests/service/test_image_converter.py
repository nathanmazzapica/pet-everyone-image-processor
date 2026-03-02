import pytest

from src.models.image_format import ImageFormat
from src.models.job import Job
from src.models.status import JobStatus
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.image_converter import ImageConverter


@pytest.fixture
def converter(mocker):
    return ImageConverter(mocker.Mock(), mocker.Mock())


def _make_job(path):
    return Job(1, JobStatus.QUEUED, str(path), None, 0, None, 0, 0)


@pytest.mark.parametrize(
    "header,expected",
    [
        (b"\x89PNG\r\n\x1a\n" + b"\x00" * 4, ImageFormat.PNG),
        (b"\xFF\xD8\xFF" + b"\x00" * 9, ImageFormat.JPEG),
        (b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP", ImageFormat.WEBP),
        (b"\x00\x00\x00\x18ftypheic", ImageFormat.HEIF),
        (b"\x00\x00\x00\x18ftypheif", ImageFormat.HEIF),
    ],
)
def test_get_mime_type_returns_expected_format(tmp_path, converter, header, expected):
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(header)

    job = _make_job(file_path)

    assert converter._get_mime_type(job) == expected


@pytest.mark.parametrize(
    "header",
    [
        b"",
        b"\x01\x02\x03\x04" * 3,
        b"\x00\x00\x00\x18ftyphevc",
        b"\x00\x00\x00\x18ftyphevx",
    ],
)
def test_get_mime_type_raises_for_invalid_or_video_heif(tmp_path, converter, header):
    file_path = tmp_path / "sample.bin"
    file_path.write_bytes(header)

    job = _make_job(file_path)

    with pytest.raises(InvalidImageFormatError):
        converter._get_mime_type(job)
