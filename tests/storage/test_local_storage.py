import os
import tempfile

import pytest

from src.storage.storage import LocalStorage


def test_init_creates_tmp_directory():
    with tempfile.TemporaryDirectory() as base_path:
        tmp_path = os.path.join(base_path, "tmp")
        assert not os.path.exists(tmp_path)
        LocalStorage(base_path=base_path)
        assert os.path.isdir(tmp_path)


def test_init_succeeds_when_tmp_directory_already_exists():
    with tempfile.TemporaryDirectory() as base_path:
        tmp_path = os.path.join(base_path, "tmp")
        os.makedirs(tmp_path)
        # Should not raise even though the directory already exists
        LocalStorage(base_path=base_path)
        assert os.path.isdir(tmp_path)


def test_init_raises_on_uncreateable_tmp_directory(mocker):
    with tempfile.TemporaryDirectory() as base_path:
        mocker.patch("os.makedirs", side_effect=OSError("permission denied"))
        with pytest.raises(OSError):
            LocalStorage(base_path=base_path)
