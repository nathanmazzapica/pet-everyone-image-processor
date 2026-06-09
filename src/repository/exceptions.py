class DatabaseError(Exception):
    pass

class DatabaseNotInitialized(DatabaseError):
    """Exception raised when database schema is not initialized."""
    pass

class JobNotFoundError(DatabaseError):
    """Exception raised when job is not found in database."""
    pass


class FatalDatabaseError(DatabaseError):
    """Exception raised when a fatal error occurs in the database"""
    pass