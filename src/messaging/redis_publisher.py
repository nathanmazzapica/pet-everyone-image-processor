import redis
from src.models.status_update import JobStatusUpdate
from src.messaging.exceptions import PublisherError, PublisherInvalidPayloadError, PublisherConnectionError, PublisherConfigurationError
from src.messaging.publisher import Publisher


class RedisPublisher(Publisher):
    def __init__(self,
                 host: str = 'localhost',
                 port: int = 6379
                 ):
        self.CHANNEL = "IMAGE_PROCESSING_EVENTS"
        self.conn = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def publish(self, evt: JobStatusUpdate):
        message = evt.to_json()
        try:
            self.conn.publish(self.CHANNEL, message)
        except (redis.exceptions.AuthenticationError, redis.exceptions.AuthorizationError) as e:
            raise PublisherConfigurationError("Invalid Redis credentials") from e
        except redis.exceptions.TimeoutError as e:
            raise PublisherConnectionError("Redis connection timed out") from e
        except (redis.exceptions.DataError, redis.exceptions.ResponseError) as e:
            raise PublisherInvalidPayloadError("Invalid payload") from e
        except Exception as e:
            raise PublisherError("Failed to publish message") from e
