from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, asdict
from json import dumps

from src.models.status import JobStatus, JobType


@dataclass
class JobStatusUpdate:
    id: int
    event_type: str
    job_type: JobType
    pet_id: uuid.UUID
    status: JobStatus

    def to_json(self) -> str:
        return dumps(asdict(self))

@dataclass
class JobSucceededUpdate(JobStatusUpdate):
    output_key: str
    event_type: str = "job_succeeded"

@dataclass
class JobFailedUpdate(JobStatusUpdate):
    error_code: int
    event_type: str = "job_failed"