import asyncio
import time
from redis.asyncio import Redis

LUA_SEMAPHORE_ACQUIRE = """
-- KEYS[1] = semaphore key
-- ARGV[1] = current timestamp
-- ARGV[2] = limit

local count = redis.call('LLEN', KEYS[1])
if count < tonumber(ARGV[2]) then
    redis.call('LPUSH', KEYS[1], ARGV[1])
    return 1
else
    return 0
end
"""

LUA_SEMAPHORE_CAN_ACQUIRE = """
-- KEYS[1] = semaphore key
-- ARGV[1] = limit

local count = redis.call('LLEN', KEYS[1])
if count < tonumber(ARGV[1]) then
    return 1
else
    return 0
end
"""


class RedisSemaphore:

    def __init__(self, redis: Redis, limit: int, name: str, sleep: float = 0.1):
        self.redis = redis
        self.name = f"redisify:semaphore:{name}"
        self.limit = limit
        self.sleep = sleep

        self._script_can_acquire = self.redis.register_script(LUA_SEMAPHORE_CAN_ACQUIRE)
        self._script_acquire = self.redis.register_script(LUA_SEMAPHORE_ACQUIRE)

    async def can_acquire(self) -> bool:
        ok = await self._script_can_acquire(keys=[self.name], args=[self.limit])
        return ok == 1

    async def acquire(self):
        while True:
            now = time.time()
            ok = await self._script_acquire(keys=[self.name], args=[now, self.limit])
            if ok == 1:
                return True
            await asyncio.sleep(self.sleep)

    async def release(self):
        await self.redis.rpop(self.name)

    async def value(self) -> int:
        """Get the current number of acquired semaphores."""
        return await self.redis.llen(self.name)

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
