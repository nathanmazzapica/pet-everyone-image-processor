import redis
from src.models.status_update import JobStatusUpdate
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
        self.conn.publish(self.CHANNEL, message)
