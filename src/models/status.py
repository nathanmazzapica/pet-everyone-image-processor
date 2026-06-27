from enum import Enum

class JobType(str, Enum):
    PREPROCESS = "PREPROCESS"
    BACKGROUND_REMOVAL = "BACKGROUND_REMOVAL"

class JobStatus(str, Enum):
    QUEUED="QUEUED"
    PROCESSING="PROCESSING"
    DONE="DONE"
    FAILED="FAILED"
    REJECTED="REJECTED"
