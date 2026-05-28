# Service Level Exceptions
The following exceptions can be raised from the background removal process:

1. `JobFailedError`
2. `JobRetryableError`
3. `FatalServiceError`

Services uses these exceptions to wrap errors from their underlying processor into ones the
worker can make decisions from.

## Descriptions

### JobFailedError
Raised when a job fails and should not be retried. E.g invalid file format.
The worker will mark the job as failed.

### JobRetryableError
Raised when a job fails and should be retried. 
The worker will return the job to the queue and increment the retry count.

TODO:
- [ ] Determine when to retry a job
- [ ] Determine priority of retrying a job over handling a new job

### FatalServiceError
Raised when the service encounters a fatal error.
The worker will mark the job as retryable, and then exit.

In the case that an OOM error occurs, the worker may not be able to
mark the job as retryable and release its lock. The startup process should
include a step that detects this and returns the jobs to the queue.

TODO:
- [ ] Add a step to the startup process that detects locked jobs and returns the jobs to the queue.
- [ ] Determine how to handle disk full errors.
