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
    """
    A distributed semaphore implementation using Redis.
    
    This class provides a distributed semaphore that can be used to limit
    concurrent access to a resource across multiple processes or servers.
    The semaphore is implemented using Redis lists and Lua scripts for
    atomic operations.
    
    The semaphore maintains a count of acquired permits and only allows
    acquisition when the count is below the specified limit.
    
    Attributes:
        redis: The Redis client instance
        name: The Redis key name for this semaphore
        limit: Maximum number of permits that can be acquired
        sleep: Sleep duration between acquisition attempts
        _script_can_acquire: Registered Lua script for checking availability
        _script_acquire: Registered Lua script for acquiring permits
    """

    def __init__(self, redis: Redis, limit: int, name: str, sleep: float = 0.1):
        """
        Initialize a Redis-based distributed semaphore.
        
        Args:
            redis: Redis client instance
            limit: Maximum number of permits that can be acquired
            name: Unique name for this semaphore
            sleep: Sleep duration between acquisition attempts in seconds
        """
        self.redis = redis
        self.name = f"redisify:semaphore:{name}"
        self.limit = limit
        self.sleep = sleep

        self._script_can_acquire = self.redis.register_script(LUA_SEMAPHORE_CAN_ACQUIRE)
        self._script_acquire = self.redis.register_script(LUA_SEMAPHORE_ACQUIRE)

    async def can_acquire(self) -> bool:
        """
        Check if a permit can be acquired without blocking.
        
        This method checks if the current number of acquired permits is
        less than the limit, allowing for non-blocking permit checking.
        
        Returns:
            True if a permit can be acquired, False otherwise
        """
        ok = await self._script_can_acquire(keys=[self.name], args=[self.limit])
        return ok == 1

    async def acquire(self):
        """
        Acquire a permit, blocking until one becomes available.
        
        This method will continuously attempt to acquire a permit until
        successful. The acquisition is performed atomically using a Lua script
        to ensure consistency across concurrent operations.
        
        Returns:
            True when a permit is successfully acquired
            
        Note:
            This method blocks indefinitely until a permit is acquired.
        """
        while True:
            now = time.time()
            ok = await self._script_acquire(keys=[self.name], args=[now, self.limit])
            if ok == 1:
                return True
            await asyncio.sleep(self.sleep)

    async def release(self):
        """
        Release a previously acquired permit.
        
        This method removes one permit from the semaphore, making it
        available for other processes to acquire.
        
        Note:
            It's important to release permits that were previously acquired
            to prevent resource exhaustion.
        """
        await self.redis.rpop(self.name)

    async def value(self) -> int:
        """
        Get the current number of acquired permits.
        
        Returns:
            The number of currently acquired permits
        """
        return await self.redis.llen(self.name)

    async def __aenter__(self):
        """
        Async context manager entry point.
        
        Acquires a permit when entering the context.
        
        Returns:
            Self instance for use in async context manager
        """
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit point.
        
        Releases the permit when exiting the context, regardless of whether
        an exception occurred.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self.release()
