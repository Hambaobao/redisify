import time
import uuid
import asyncio

from redisify.config import get_redis

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
        namespace: The namespace prefix for Redis keys
        id: The Redis key id for this semaphore
        limit: Maximum number of permits that can be acquired
        sleep: Sleep duration between acquisition attempts
        _script_can_acquire: Registered Lua script for checking availability
        _script_acquire: Registered Lua script for acquiring permits
    """

    namespace: str = "redisify:semaphore"

    def __init__(self, id: str = None, limit: int = 1, sleep: float = 0.1) -> None:
        """
        Initialize a Redis-based distributed semaphore.
        
        Args:
            id: Unique id for this semaphore
            limit: Maximum number of permits that can be acquired
            sleep: Sleep duration between acquisition attempts in seconds
        """
        self.redis = get_redis()
        _id = id or str(uuid.uuid4())
        self.id = f"{self.namespace}:{_id}"
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
        ok = await self._script_can_acquire(keys=[self.id], args=[self.limit])
        return ok == 1

    async def acquire(self, timeout: float = None) -> bool:
        """
        Acquire a permit, blocking until one becomes available or timeout is reached.
        
        This method will continuously attempt to acquire a permit until
        successful or until the specified timeout is reached. The acquisition 
        is performed atomically using a Lua script to ensure consistency 
        across concurrent operations.
        
        Args:
            timeout: Maximum time to wait for a permit in seconds.
                    If None, wait indefinitely.
        
        Returns:
            True when a permit is successfully acquired, False if timeout is reached
            
        Note:
            If timeout is None, this method blocks indefinitely until a permit is acquired.
            If timeout is specified, it will return False if a permit cannot be acquired
            within the specified time.
        """
        if timeout is None:
            # Wait indefinitely
            while True:
                now = time.time()
                ok = await self._script_acquire(keys=[self.id], args=[now, self.limit])
                if ok == 1:
                    return True
                await asyncio.sleep(self.sleep)
        else:
            # Wait with timeout
            start_time = time.time()
            while True:
                now = time.time()
                ok = await self._script_acquire(keys=[self.id], args=[now, self.limit])
                if ok == 1:
                    return True

                # Check if timeout has been reached
                if time.time() - start_time >= timeout:
                    return False

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
        await self.redis.rpop(self.id)

    async def value(self) -> int:
        """
        Get the current number of acquired permits.
        
        Returns:
            The number of currently acquired permits
        """
        return await self.redis.llen(self.id)

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
