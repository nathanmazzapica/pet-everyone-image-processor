The following exceptions may be raised by the messaging layer:

1. PublisherError
2. PublisherConfigurationError
3. PublisherConnectionError
4. PublisherInvalidPayloadError

## Descriptions

### PublisherError
Generic base class for all publisher errors.

### PublisherConfigurationError
Raised when the publisher is not configured properly, ie: invalid password or authorization.

If raised, the outbox worker will stop. The rest of the application will continue to run, but events will not be published.

**Edge case to consider:**
What happens if the outbox worker is down and a job completes both preprocess and background removal stages? Will the order they're sent matter?
I don't really think so. Consumer can switch on JobType and handle it accordingly.

### PublisherConnectionError
Raised when the publisher is not connected to the server.

### PublisherInvalidPayloadError
Raised when the payload is not valid. This is unlikely to happen, and may be removed in the future.