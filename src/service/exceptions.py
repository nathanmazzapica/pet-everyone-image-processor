class InvalidJobError(Exception):
    """Exception raised when a job not in queue is passed into service"""
    pass


class JobFailedError(Exception):
    """Exception raised when a job fails and is marked FAILED"""
    pass


class JobRetryableError(Exception):
    """Exception raised when a job fails and is marked RETRY"""
    pass


class InvalidImageFormatError(JobFailedError, ValueError):
    """Exception raised when an image format cannot be detected """
    pass

class FatalServiceError(Exception):
    """Exception raised when a fatal error occurs in the service"""
    pass