import uuid
import asyncio
from redis.asyncio import Redis


class RedisLock:

    def __init__(self, redis: Redis, name: str, sleep: float = 0.1):
        self.redis = redis
        self.name = f"redisify:lock:{name}"
        self.token = str(uuid.uuid4())
        self.sleep = sleep

    async def acquire(self) -> bool:
        while True:
            ok = await self.redis.set(self.name, self.token, nx=True)
            if ok:
                return True
            await asyncio.sleep(self.sleep)

    async def release(self) -> None:
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(script, 1, self.name, self.token)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
