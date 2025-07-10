import asyncio
import time
import uuid
from redis.asyncio import Redis


class RedisLimiter:
    """
    A distributed rate limiter implementation using Redis.
    
    This class provides a token bucket rate limiter that can be used to control
    the rate of operations across multiple processes or servers. The limiter
    implements a token bucket algorithm with automatic refill over time.
    
    The rate limiter maintains a bucket of tokens that are consumed by operations
    and automatically refilled at a specified rate. Operations are only allowed
    when tokens are available.
    
    Attributes:
        redis: The Redis client instance
        key: The Redis key name for this limiter
        rate_limit: Maximum number of tokens (bucket capacity)
        time_period: Time period in seconds to fully refill the bucket
        refill_rate: Rate at which tokens are refilled (tokens per second)
        sleep: Sleep duration between acquisition attempts
    """

    def __init__(
        self,
        redis: Redis,
        name: str | None = None,
        rate_limit: int = 10,
        time_period: float = 60.0,
        sleep: float = 0.1,
    ):
        """
        Initialize a Redis-based distributed rate limiter.
        
        Args:
            redis: Redis client instance
            name: Unique name for this limiter (auto-generated if None)
            rate_limit: Maximum number of tokens (bucket capacity)
            time_period: Time period in seconds to fully refill the bucket
            sleep: Sleep duration between acquisition attempts in seconds
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.key = f"redisify:limiter:{_name}"
        self.rate_limit = rate_limit
        self.time_period = time_period
        self.refill_rate = rate_limit / time_period  # tokens per second
        self.sleep = sleep

    async def acquire(self) -> bool:
        """
        Try to acquire a token from the rate limiter.
        
        This method attempts to consume one token from the bucket. If tokens
        are available, one is consumed and True is returned. If no tokens
        are available, False is returned without blocking.
        
        The token bucket is automatically refilled based on the elapsed time
        since the last refill, up to the maximum capacity.
        
        Returns:
            True if a token was successfully acquired, False otherwise
        """
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local refill_rate = tonumber(ARGV[2])
        local now = tonumber(ARGV[3])

        local bucket = redis.call("HMGET", key, "tokens", "last_refill")
        local tokens = tonumber(bucket[1]) or capacity
        local last_refill = tonumber(bucket[2]) or now

        local delta = math.max(0, now - last_refill)
        local refill = delta * refill_rate
        tokens = math.min(capacity, tokens + refill)

        if tokens >= 1 then
            tokens = tokens - 1
            redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
            return 1
        else
            redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
            return 0
        end
        """
        now = time.time()
        allowed = await self.redis.eval(
            script,
            1,  # numkeys
            self.key,  # KEYS[1]
            self.rate_limit,  # ARGV[1]
            self.refill_rate,  # ARGV[2]
            now,  # ARGV[3]
        )
        return int(allowed) == 1

    async def release(self):
        """
        Manually return one token to the bucket.
        
        This method adds one token back to the bucket, up to the maximum
        capacity. This can be useful for implementing rollback mechanisms
        or compensating for operations that don't actually consume resources.
        
        Note:
            This method is typically used in exception handling scenarios
            to rollback token consumption.
        """
        script = """
        local key = KEYS[1]
        local capacity = tonumber(ARGV[1])
        local now = tonumber(ARGV[2])

        local bucket = redis.call("HMGET", key, "tokens", "last_refill")
        local tokens = tonumber(bucket[1]) or 0
        local last_refill = tonumber(bucket[2]) or now

        tokens = math.min(capacity, tokens + 1)
        redis.call("HMSET", key, "tokens", tokens, "last_refill", now)
        return tokens
        """
        now = time.time()
        await self.redis.eval(
            script,
            1,  # numkeys
            self.key,  # KEYS[1]
            self.rate_limit,  # ARGV[1]
            now,  # ARGV[2]
        )

    async def __aenter__(self):
        """
        Async context manager entry point.
        
        Acquires a token when entering the context, blocking until one
        becomes available.
        
        Returns:
            Self instance for use in async context manager
        """
        while True:
            if await self.acquire():
                return self
            await asyncio.sleep(self.sleep)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Async context manager exit point.
        
        Releases the token when exiting the context, but only if an
        exception occurred. This implements a rollback mechanism for
        failed operations.
        
        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        # Only release if an exception occurred (rollback)
        if exc_type is not None:
            await self.release()
