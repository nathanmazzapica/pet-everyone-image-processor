from enum import Enum

class JobStatus(Enum):
    QUEUED="QUEUED"
    DONE="DONE"
    PROCESSING="PROCESSING"
    FAILED="FAILED"
    RETRY="RETRY"
    REJECTED="REJECTED"
