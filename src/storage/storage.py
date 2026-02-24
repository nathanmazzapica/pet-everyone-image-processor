from abc import ABC, abstractmethod
import os
from PIL import Image

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
    #@abstractmethod
    #def download(self, job: Job) -> None
    #   pass

    @abstractmethod
    def exists(self, job: Job) -> bool:
        pass


class LocalStorage(Storage):
    
    def __init__(self, base_path: str) -> None:
        self.base_path = base_path

    def __get_mime_type(self, input_path: str) -> str:
        raise NotImplementedError

    def generate_output_path(self, input_path: str) -> str:
        return f"{Storage.__clean_filepath(input_path)}-withoutbg.webp"

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
