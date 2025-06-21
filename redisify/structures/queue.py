from redis.asyncio import Redis
import uuid
from redisify.serializer import Serializer


class RedisQueue:

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        self.redis = redis
        self.name = name or str(uuid.uuid4())
        self.serializer = serializer or Serializer()

    async def put(self, item):
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def get(self):
        val = await self.redis.lpop(self.name)
        return self.serializer.deserialize(val) if val else None

    async def get_block(self, timeout: int = 0):
        result = await self.redis.blpop(self.name, timeout=timeout)
        return self.serializer.deserialize(result[1]) if result else None

    async def size(self) -> int:
        return await self.redis.llen(self.name)

    async def clear(self):
        await self.redis.delete(self.name)

    async def peek(self):
        items = await self.redis.lrange(self.name, 0, 0)
        return self.serializer.deserialize(items[0]) if items else None

    async def is_empty(self) -> bool:
        return await self.size() == 0

    def __aiter__(self):
        self._iter_index = 0
        return self

    async def __anext__(self):
        item = await self.redis.lindex(self.name, self._iter_index)
        if item is None:
            raise StopAsyncIteration
        self._iter_index += 1
        return self.serializer.deserialize(item)
