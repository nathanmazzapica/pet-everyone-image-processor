from abc import ABC, abstractmethod
import os
from PIL import Image, ImageFile

from src.models.job import Job

class Storage(ABC):
    @staticmethod
    def __clean_filepath(filepath: str) -> str:
        """Removes the file extension from a filepath"""
        if not filepath:
            return ""
        last_dot = filepath.rfind(".")
        last_sep = filepath.rfind("/")
        if last_dot == -1 or last_dot < last_sep:
            return filepath
        return filepath[:last_dot]

    @abstractmethod
    def generate_output_path(self, input_path: str) -> str:
        pass

    @abstractmethod
    def upload(self, job: Job, image: Image.Image) -> str | None:
        pass

    # I'm not sure what this will look like yet...
    # If we're getting a file from S3 it needs to be downloaded first
    # If we're getting a file locally, we just need to open it?
    # Do we want to move image opening to this method instead of using Image.open in services? maybe... but
    # pyvips doesn't really work like that it seems
    @abstractmethod
    def open_image(self, job: Job) -> bytes:
        pass

    @abstractmethod
    def get_tmp_path(self) -> str:
        """returns a temporary filepath for intra-processing steps"""
        pass

    @abstractmethod
    def exists(self, job: Job) -> bool:
        pass


class LocalStorage(Storage):
    
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    # authority decide who
    def __get_mime_type(self, input_path: str) -> str:
        raise NotImplementedError

    def generate_output_path(self, input_path: str) -> str:
        return f"{Storage.__clean_filepath(input_path)}-withoutbg.webp"

    def open_image(self, job: Job) -> bytes:
        with open(job.input_url, "rb") as f:
            file_bytes = f.read()
            return file_bytes

    def upload(self, job: Job, image: Image.Image) -> str | None:
        try:
            output_path = self.generate_output_path(job.input_url)
            image.save(output_path)
            return output_path
        except OSError as ose:
            # raised if file cannot be fully written
            print(ose)
            pass

    def exists(self, job: Job) -> bool:
        return os.path.isfile(job.input_url)
