from dataclasses import dataclass
from typing import Mapping, Optional, Any
from src.models.status import JobStatus

@dataclass
class Job:
    id: int
    status: JobStatus
    input_url: str
    proc_url: Optional[str]
    output_url: Optional[str]
    attempt_count: int
    last_locked: Optional[float]
    created_at: float
    updated_at: float

    @staticmethod
    def from_row(row: Mapping[str, Any]):
        return Job(
                id=row["job_id"],
                status=JobStatus(row["job_status"]),
                input_url=row["input_url"],
                proc_url=row["proc_url"],
                output_url=row["output_url"],
                attempt_count=row["attempt_count"],
                last_locked=row["last_locked"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                )

    def to_dict(self):
        return {
                "id": self.id,
                "status": self.status,
                "input_url": self.input_url,
                "proc_url": self.proc_url,
                "output_url": self.output_url,
                "attempt_count": self.attempt_count,
                "last_locked": self.last_locked,
                "created_at": self.created_at,
                "updated_at": self.updated_at,
                }
