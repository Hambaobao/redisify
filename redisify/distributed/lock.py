import uuid
import asyncio
from redis.asyncio import Redis


class RedisLock:
    """
    A distributed lock implementation using Redis.
    
    This class provides a distributed locking mechanism that can be used across
    multiple processes or servers. The lock is implemented using Redis SET with
    NX (only set if not exists) and includes proper cleanup on release.
    
    The lock uses a unique token to ensure that only the process that acquired
    the lock can release it, preventing accidental releases by other processes.
    
    Attributes:
        redis: The Redis client instance
        name: The Redis key name for this lock
        token: Unique identifier for this lock instance
        sleep: Sleep duration between acquisition attempts
    """

    def __init__(self, redis: Redis, name: str, sleep: float = 0.1):
        """
        Initialize a Redis-based distributed lock.
        
        Args:
            redis: Redis client instance
            name: Unique name for this lock
            sleep: Sleep duration between acquisition attempts in seconds
        """
        self.redis = redis
        self.name = f"redisify:lock:{name}"
        self.token = str(uuid.uuid4())
        self.sleep = sleep

    async def acquire(self) -> bool:
        """
        Acquire the lock, blocking until it becomes available.
        
        This method will continuously attempt to acquire the lock until successful.
        The lock is acquired using Redis SET with NX (only set if not exists)
        to ensure atomicity.
        
        Returns:
            True when the lock is successfully acquired
            
        Note:
            This method blocks indefinitely until the lock is acquired.
        """
        while True:
            ok = await self.redis.set(self.name, self.token, nx=True)
            if ok:
                return True
            await asyncio.sleep(self.sleep)

    async def release(self) -> None:
        """
        Release the lock if it was acquired by this instance.
        
        This method uses a Lua script to ensure that only the process that
        acquired the lock can release it. The script checks if the current
        value matches this instance's token before deleting the key.
        
        Note:
            Only the process that acquired the lock can release it safely.
        """
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(script, 1, self.name, self.token)

    async def __aenter__(self):
        """
        Async context manager entry point.
        
        Acquires the lock when entering the context.
        
        Returns:
            Self instance for use in async context manager
        """
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit point.
        
        Releases the lock when exiting the context, regardless of whether
        an exception occurred.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        await self.release()
