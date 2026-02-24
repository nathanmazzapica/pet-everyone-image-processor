class InvalidJobError(Exception):
    """Exception raised when a job not in queue is passed into service"""
    pass


class JobFailedError(Exception):
    """Exception raised when a job fails and is marked FAILED"""
    pass


class JobRetryableError(Exception):
    """Exception raised when a job fails and is marked RETRY"""
    pass
