from dataclasses import dataclass
from typing import Optional
from status import JobStatus

@dataclass
class Job:
    id: int
    status: JobStatus
    input_url: str
    output_url: str
    attempt_count: int
    last_locked: Optional[float]

    @staticmethod
    def from_tuple(row: tuple):
        return Job(
                id=row[0],
                status=row[1],
                input_url=row[2],
                output_url=row[3],
                attempt_count=row[4],
                last_locked=row[5],
                )

    def to_dict(self):
        return {
                "id": self.id,
                "status": self.status,
                "input_url": self.input_url,
                "output_url": self.output_url,
                "attempt_count": self.attempt_count,
                "last_locked": self.last_locked
                }
