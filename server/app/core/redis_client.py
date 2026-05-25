import redis
from app.core.config import settings

# Initialize a global Redis connection client
# 'decode_responses=True' parses bytes from Redis into standard UTF-8 strings automatically
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True
)
