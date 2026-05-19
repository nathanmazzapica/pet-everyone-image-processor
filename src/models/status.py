from enum import Enum

class JobStatus(Enum):
    QUEUED="QUEUED"
    PROCESSING="PROCESSING"
    DONE="DONE"
    FAILED="FAILED"
    RETRY="RETRY"
    REJECTED="REJECTED"
