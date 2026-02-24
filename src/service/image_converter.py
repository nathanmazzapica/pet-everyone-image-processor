"""
The image converter service handles converting input images and resizing them as a pre-processing step to background removal
"""

from src.models.job import Job
from src.repository.repository import JobRepository
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.exceptions import JobFailedError
from src.storage.storage import Storage
from wand.image import Image


class ImageConverter:
    def __init__(self, repository: JobRepository, storage: Storage) -> None:
        self.repository = repository
        self.storage = storage
        # initialize imagemagick & libsvip as needed
        pass

    def __get_mime_type(self, job: Job) -> str:
        with Image(filename=job.input_url) as img:
            try:
                format = img.format
                if format is None:
                    # todo: understand what causes this and how to handle it
                    pass
            except ValueError as ve: 
               raise InvalidImageFormatError from ve

            return str(img.format)

    def __resize_image(self, job: Job):
        raise NotImplementedError

    def __convert_to_webp(self, job: Job):
        raise NotImplementedError

    def convert(self, job: Job):
        if not self.storage.exists(job):
            raise JobFailedError(f"Image does not exists at {job.input_url}")
        raise NotImplementedError
