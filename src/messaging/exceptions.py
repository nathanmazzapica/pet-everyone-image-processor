class PublisherError(Exception):
    pass

class PublisherConfigurationError(PublisherError):
    pass

class PublisherConnectionError(PublisherError):
    pass

# note: to be honest, i dont think this will ever be raised. Keeping it just incase though
class PublisherInvalidPayloadError(PublisherError):
    pass
