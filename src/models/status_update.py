from dataclasses import asdict, dataclass
from json import dumps

from src.models.status import JobStatus, JobType


@dataclass(kw_only=True)
class JobStatusUpdate:
    id: int
    event_type: str
    job_type: JobType
    pet_id: str
    status: JobStatus

    def to_json(self) -> str:
        return dumps(asdict(self))

@dataclass(kw_only=True)
class JobSucceededUpdate(JobStatusUpdate):
    output_key: str
    event_type: str = "job_succeeded"

@dataclass(kw_only=True)
class JobFailedUpdate(JobStatusUpdate):
    error_code: int
    event_type: str = "job_failed"