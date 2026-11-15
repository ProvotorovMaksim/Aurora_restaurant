from redis import Redis

from settings import settings


class RedisProvider:
    def __init__(self):
        self.client = Redis.from_url(settings.redis_url, decode_responses=True)

    def get_client(self):
        return self.client


redis = RedisProvider()
