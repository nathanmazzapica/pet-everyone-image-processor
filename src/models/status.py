from enum import Enum

class JobStatus(Enum):
    PENDING="PENDING"
    QUEUED="QUEUED"
    PROCESSING="PROCESSING"
    DONE="DONE"
    FAILED="FAILED"
    RETRY="RETRY"
    REJECTED="REJECTED"
