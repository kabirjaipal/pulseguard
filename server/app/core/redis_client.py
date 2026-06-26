import redis
import logging
import asyncio
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global broker for in-memory WebSocket Pub/Sub
class InMemoryPubSubBroker:
    def __init__(self):
        self.subscribers = set()

    def register(self, subscriber):
        self.subscribers.add(subscriber)

    def unregister(self, subscriber):
        self.subscribers.discard(subscriber)

    def publish(self, channel, message):
        for sub in list(self.subscribers):
            if channel in sub.channels:
                sub.queue.put_nowait({"type": "message", "channel": channel, "data": message})

in_memory_broker = InMemoryPubSubBroker()

class InMemoryPubSub:
    def __init__(self):
        self.channels = []
        self.queue = asyncio.Queue()

    async def subscribe(self, channel):
        self.channels.append(channel)
        in_memory_broker.register(self)

    async def unsubscribe(self, channel):
        if channel in self.channels:
            self.channels.remove(channel)
        in_memory_broker.unregister(self)

    async def listen(self):
        while True:
            yield await self.queue.get()

    async def close(self):
        in_memory_broker.unregister(self)


class InMemoryRedis:
    def __init__(self):
        self._store = {}

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value, *args, **kwargs):
        self._store[key] = str(value)
        return True

    def setex(self, key, time, value):
        self._store[key] = str(value)
        return True

    def incr(self, key, amount=1):
        current = int(self._store.get(key, 0))
        new_val = current + amount
        self._store[key] = str(new_val)
        return new_val

    def expire(self, key, time):
        return True

    def publish(self, channel, message):
        in_memory_broker.publish(channel, message)
        return 1

    def pubsub(self):
        return InMemoryPubSub()

    async def close(self):
        pass


# Test connection and initialize correct client
redis_available = False
try:
    test_client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=1)
    test_client.ping()
    redis_available = True
    logger.info("Successfully connected to Redis.")
except Exception:
    logger.warning("Redis is not available. Falling back to in-memory Mock Redis.")

if redis_available:
    redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
else:
    redis_client = InMemoryRedis()
