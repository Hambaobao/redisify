import uuid
import asyncio
from redis.asyncio import Redis
from redisify.serializer import Serializer


class RedisQueue:

    def __init__(
        self,
        redis: Redis,
        name: str = None,
        maxsize: int = None,
        serializer: Serializer = None,
        sleep: float = 0.1,
    ):
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:queue:{_name}"
        self.serializer = serializer or Serializer()
        self.maxsize = maxsize
        self.sleep = sleep

    async def put(self, item):
        """Put item into the queue. Blocks if maxsize is reached."""
        if self.maxsize is not None:
            while await self.qsize() >= self.maxsize:
                await asyncio.sleep(self.sleep)
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def put_nowait(self, item):
        """Put item only if space is available, else raise."""
        if self.maxsize is not None and await self.qsize() >= self.maxsize:
            raise asyncio.QueueFull("RedisQueue is full")
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def get(self):
        """Blocking get. Waits until an item is available."""
        result = await self.redis.blpop(self.name, timeout=0)
        return self.serializer.deserialize(result[1]) if result else None

    async def get_nowait(self):
        """Non-blocking get. Return None if queue is empty."""
        val = await self.redis.lpop(self.name)
        return self.serializer.deserialize(val) if val else None

    async def peek(self):
        """Peek at the first item without removing."""
        items = await self.redis.lrange(self.name, 0, 0)
        return self.serializer.deserialize(items[0]) if items else None

    async def qsize(self) -> int:
        return await self.redis.llen(self.name)

    async def empty(self) -> bool:
        return await self.qsize() == 0

    async def clear(self):
        await self.redis.delete(self.name)

    def __aiter__(self):
        self._iter_index = 0
        return self

    async def __anext__(self):
        item = await self.redis.lindex(self.name, self._iter_index)
        if item is None:
            raise StopAsyncIteration
        self._iter_index += 1
        return self.serializer.deserialize(item)
