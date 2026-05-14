"""
The image converter service handles converting input images and resizing them as a pre-processing step to background removal
"""

from PIL import Image
from src.models.job import Job
from src.repository.repository import JobRepository
from src.models.image_format import ImageFormat
from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.exceptions import JobFailedError
from src.storage.storage import Storage
import pyvips

class ImageConverter:
    def __init__(self, repository: JobRepository, storage: Storage) -> None:
        self.repository = repository
        self.storage = storage
        # initialize libvips as needed
        pass
    
    def _get_mime_type(self, job: Job) -> ImageFormat:
        """Gets the mime type of an image
        
            Raises:
                InvalidImageFormatError if file format is not a whitelisted image.
        """
        try:
            with open(job.input_url, "rb") as file:
                header = file.read(12)
        except OSError as exc:
            raise InvalidImageFormatError from exc

        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return ImageFormat.PNG

        if header[:3] == b"\xFF\xD8\xFF":
            return ImageFormat.JPEG

        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return ImageFormat.WEBP

        if len(header) >= 12 and header[4:8] == b"ftyp":
            brand = header[8:12]
            if brand in {b"heic", b"heix", b"mif1", b"msf1", b"heif"}:
                return ImageFormat.HEIF

        raise InvalidImageFormatError

    def __resize_image(self, job: Job):
        raise NotImplementedError

    def __convert_to_webp(self, job: Job):
        raise NotImplementedError

    def __verify_image(self, job: Job) -> None:
        """
            Verifies a file is actually an image

            Raises:
                JobFailedError if an image cannot be verified
        """

        try:
            img: pyvips.Image = pyvips.Image.new_from_buffer(self.storage.open_image(job), "") #pyright: ignore [reportAssignmentType]
            img.stats() 
        except:
            pass

    def convert(self, job: Job):
        if not self.storage.exists(job):
            raise JobFailedError(f"Image does not exists at {job.input_url}")

        img_format = self._get_mime_type(job)

        self.__verify_image(job)

        

        raise NotImplementedError
