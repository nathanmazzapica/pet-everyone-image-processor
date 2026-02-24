from withoutbg import WithoutBG, exceptions

from src.models.job import Job
from src.models.status import JobStatus
from src.repository.repository import JobRepository

class BackgroundRemover:

    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository
        self.model = WithoutBG.opensource()

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

    def process(self, job: Job):
        if job.status != JobStatus.QUEUED:
            raise ValueError(f"Job {job.id} cannot be processed at this time {job}")

        try:
            result = self.model.remove_background(job.input_url)
            #TODO: filepath handling should move to the Storage layer to support s3 and local storage modularity
            output_filepath = f"{BackgroundRemover.__clean_filepath(job.input_url)}-transparent.webp"
            result.save(output_filepath)
        except exceptions.InvalidImageError as ime:
            # InvalidImageError is NOT recoverable.
            self.repository.update_status(job.id, JobStatus.FAILED)
            print(ime)
        except OSError as ose:
            # raised if file cannot be FULLY written. File *may* have been created
            print(ose)
