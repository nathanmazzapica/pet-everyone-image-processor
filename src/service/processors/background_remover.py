from withoutbg import WithoutBG, exceptions as wbg_exception

from io import BytesIO

from src.service.conversion_exceptions import InvalidImageFormatError
from src.service.exceptions import JobFailedError, JobRetryableError


class BackgroundRemoverError(Exception):
    pass

class BackgroundRemoverSetupError(JobRetryableError):
    pass

class BackgroundRemover:

    def __init__(self):
        self.model = WithoutBG.opensource()

    def process(self, image_data: bytes) -> bytes:
        try:
            result = self.model.remove_background(image_data)
        except wbg_exception.InvalidImageError as e:
            raise InvalidImageFormatError("Invalid image format") from e
        except wbg_exception.ConfigurationError as e:
            raise BackgroundRemoverSetupError("Failed to setup background remover") from e
        except wbg_exception.ModelNotFoundError as e:
            raise BackgroundRemoverSetupError("Background remover not found") from e

        buffer = BytesIO()
        result.save(buffer, format="WEBP")

        return buffer.getvalue()
