class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 99):
        super().__init__(message)
        self.status_code = status_code

class InvalidJobError(ServiceError):
    """Exception raised when a job not in queue is passed into service"""
    pass


class JobFailedError(ServiceError):
    """Exception raised when a job fails and is marked FAILED"""
    pass

class InvalidImageFormatError(JobFailedError, ValueError):
    """Exception raised when an image format cannot be detected """
    pass

class FatalServiceError(ServiceError):
    """Exception raised when a fatal error occurs in the service"""
    pass