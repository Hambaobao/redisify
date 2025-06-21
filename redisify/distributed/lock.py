import uuid
from redis.asyncio import Redis


class RedisLock:

    def __init__(
        self,
        redis: Redis,
        name: str = None,
        timeout: int | None = None,
        sleep: float = 0.1,
        blocking: bool = True,
        blocking_timeout: float | None = None,
    ):
        self._lock = redis.lock(
            name=name or str(uuid.uuid4()),
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )

    async def acquire(self) -> bool:
        return await self._lock.acquire()

    async def release(self) -> None:
        await self._lock.release()

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
