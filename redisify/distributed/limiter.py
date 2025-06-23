import asyncio
import time
import uuid
from redis.asyncio import Redis


class RedisLimiter:

    def __init__(
        self,
        redis: Redis,
        name: str | None = None,
        rate_limit: int = 10,
        time_period: float = 60.0,
        sleep: float = 0.1,
    ):
        """
        :param redis: Redis client
        :param name: Unique name for this limiter
        :param rate_limit: Max number of tokens (bucket capacity)
        :param time_period: Seconds to fully refill the bucket
        :param sleep: Sleep time between retries
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.key = f"redisify:limiter:{_name}"
        self.rate_limit = rate_limit
        self.time_period = time_period
        self.refill_rate = rate_limit / time_period  # tokens per second
        self.sleep = sleep

    async def acquire(self) -> bool:
        """Try to acquire a token. Return True if granted, else False."""
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
        """Manually return one token."""
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
        while True:
            if await self.acquire():
                return self
            await asyncio.sleep(self.sleep)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Only release if an exception occurred (rollback)
        if exc_type is not None:
            await self.release()
