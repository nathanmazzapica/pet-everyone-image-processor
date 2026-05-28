# Storage Level Exceptions
The following exceptions are thrown by the storage level:

1. StorageConfigurationError
2. FatalStorageUploadError
3. AssetNotFoundError
4. StorageError
5. MemoryError

## Descriptions

### StorageConfigurationError
In LocalStorage, this exception is thrown when permissions are incorrectly set for the storage's base_path directory

### FatalStorageUploadError
In LocalStorage, this is raised when the disk is full

### AssetNotFoundError
Raised when an asset cannot be found with the provided object key/filepath

### StorageError
Raised when an error occurs in the storage layer

### MemoryError
Raised if a MemoryError is raised when attempting to read a file into memory

## Future Thoughts
- S3 exception handling