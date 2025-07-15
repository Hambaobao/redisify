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


class RedisRWLock:
    """
    A distributed read-write lock using Redis.
    
    - Multiple readers can hold the lock simultaneously if no writer holds it.
    - Only one writer can hold the lock, and no readers can hold it at the same time.
    
    Attributes:
        redis: The Redis client instance
        name: The base Redis key name for this lock
        token: Unique identifier for this lock instance (for write lock)
        sleep: Sleep duration between acquisition attempts
    """

    def __init__(self, redis: Redis, name: str, sleep: float = 0.1):
        self.redis = redis
        self.name = f"redisify:rwlock:{name}"
        self.write_key = f"{self.name}:write"
        self.readers_key = f"{self.name}:readers"
        self.token = str(uuid.uuid4())
        self.sleep = sleep
        self._is_writer = False
        self._is_reader = False

    async def acquire_read(self) -> bool:
        """
        Acquire the read lock. Multiple readers are allowed if no writer holds the lock.
        """
        while True:
            # Lua: if no write lock, increment readers and allow
            script = """
            if redis.call('EXISTS', KEYS[1]) == 0 then
                return redis.call('INCR', KEYS[2])
            else
                return 0
            end
            """
            result = await self.redis.eval(script, 2, self.write_key, self.readers_key)
            if result:
                self._is_reader = True
                return True
            await asyncio.sleep(self.sleep)

    async def release_read(self) -> None:
        """
        Release the read lock (decrement readers count).
        """
        if not self._is_reader:
            return
        await self.redis.decr(self.readers_key)
        self._is_reader = False

    async def acquire_write(self) -> bool:
        """
        Acquire the write lock. Only one writer allowed, and no readers.
        """
        while True:
            # Lua: if no write lock and no readers, set write lock
            script = """
            if redis.call('EXISTS', KEYS[1]) == 0 and (redis.call('GET', KEYS[2]) == false or redis.call('GET', KEYS[2]) == '0') then
                return redis.call('SET', KEYS[1], ARGV[1], 'NX') and 1 or 0
            else
                return 0
            end
            """
            result = await self.redis.eval(script, 2, self.write_key, self.readers_key, self.token)
            if result:
                self._is_writer = True
                return True
            await asyncio.sleep(self.sleep)

    async def release_write(self) -> None:
        """
        Release the write lock if held by this instance.
        """
        if not self._is_writer:
            return
        # Only delete if token matches
        script = """
        if redis.call('GET', KEYS[1]) == ARGV[1] then
            return redis.call('DEL', KEYS[1])
        else
            return 0
        end
        """
        await self.redis.eval(script, 1, self.write_key, self.token)
        self._is_writer = False

    async def __aenter__(self):
        """
        By default, acquire write lock in context manager.
        """
        await self.acquire_write()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release_write()

    # Optionally, context managers for read lock
    async def read_lock(self):

        class _ReadCtx:

            async def __aenter__(inner):
                await self.acquire_read()
                return self

            async def __aexit__(inner, exc_type, exc_val, exc_tb):
                await self.release_read()

        return _ReadCtx()
