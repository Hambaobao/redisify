import asyncio
import uuid
from redis.asyncio import Redis
from redisify.distributed.lock import RedisLock


class RedisLimiter:

    def __init__(
        self,
        redis: Redis,
        name: str = None,
        rate_limit: int = 10,
        time_period: float = 60,
        sleep: float = 0.1,
    ):
        """
        :param redis: Redis client
        :param name: Name of the limiter
        :param rate_limit: Max allowed actions per time_period
        :param time_period: Window in seconds
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:limiter:{_name}"

        self.rate_limit = rate_limit
        self.time_period = time_period
        self.sleep = sleep
        self._lock = RedisLock(redis, name=self.name)

    async def acquire(self) -> bool:
        async with self._lock:
            tx = self.redis.pipeline()
            tx.incr(self.name)
            tx.expire(self.name, int(self.time_period))
            count, _ = await tx.execute()
            return count <= self.rate_limit

    async def __aenter__(self):
        while True:
            allowed = await self.acquire()
            if allowed:
                return self
            await asyncio.sleep(self.sleep)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
