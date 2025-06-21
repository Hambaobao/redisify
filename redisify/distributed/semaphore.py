import uuid
import time
import asyncio
from redis.asyncio import Redis


class RedisSemaphore:

    def __init__(
        self,
        redis: Redis,
        name: str,
        limit: int,
        timeout: int | None = None,
        sleep: float = 0.1,
    ):
        self.redis = redis
        self.name = name
        self.limit = limit
        self.timeout = timeout
        self.token = str(uuid.uuid4())
        self.sleep = sleep

    async def acquire(self) -> bool:
        now = time.time()

        if self.timeout is not None:
            await self.redis.zremrangebyscore(self.name, 0, now - self.timeout)

        await self.redis.zadd(self.name, {self.token: now})
        rank = await self.redis.zrank(self.name, self.token)
        if rank is not None and rank < self.limit:
            return True

        await self.redis.zrem(self.name, self.token)
        return False

    async def release(self):
        await self.redis.zrem(self.name, self.token)

    async def __aenter__(self):
        while not await self.acquire():
            await asyncio.sleep(self.sleep)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
