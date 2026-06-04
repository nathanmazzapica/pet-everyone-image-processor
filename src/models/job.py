import uuid
from dataclasses import dataclass
from typing import Mapping, Optional, Any
from src.models.status import JobStatus, JobType


@dataclass
class Job:
    id: int
    job_type: JobType
    status: JobStatus
    input_key: str
    pet_id: uuid.UUID
    created_at: str
    updated_at: str
    ready_at: str
    attempt_count: int = 0
    last_locked: int = 0
    output_key: Optional[str] = None

    @staticmethod
    def from_row(row: Mapping[str, Any]) -> "Job":
        return Job(
            id=row["job_id"],
            job_type=JobType(row["job_type"]),
            status=JobStatus(row["job_status"]),
            input_key=row["input_key"],
            output_key=row["output_key"],
            pet_id=uuid.UUID(row["pet_id"]),
            attempt_count=row["attempt_count"],
            last_locked=row["last_locked"],
            ready_at=row["ready_at"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "input_key": self.input_key,
            "output_key": self.output_key,
            "pet_id": str(self.pet_id),
            "attempt_count": self.attempt_count,
            "last_locked": self.last_locked,
            "ready_at": self.ready_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }