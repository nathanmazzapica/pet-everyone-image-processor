from enum import Enum

class JobStatus(Enum):
    QUEUED="QUEUED"
    DONE="DONE"
    FAILED="FAILED"
    RETRY="RETRY"
    REJECTED="REJECTED"
