from redis import Redis
import uuid


class RedisQueue:

    def __init__(self, redis: Redis, name: str = None):
        self.redis = redis
        self.name = name or str(uuid.uuid4())

    async def put(self, item: str):
        await self.redis.rpush(self.name, item)

    async def get(self) -> str | None:
        return await self.redis.lpop(self.name)

    async def size(self) -> int:
        return await self.redis.llen(self.name)

    async def clear(self):
        await self.redis.delete(self.name)

    async def peek(self) -> str | None:
        items = await self.redis.lrange(self.name, 0, 0)
        return items[0] if items else None

    async def is_empty(self) -> bool:
        return await self.size() == 0

    async def get_block(self, timeout: int = 0) -> str | None:
        result = await self.redis.blpop(self.name, timeout=timeout)
        return result[1] if result else None

    def __aiter__(self):
        self._iter_index = 0
        return self

    async def __anext__(self):
        items = await self.redis.lrange(self.name, self._iter_index, self._iter_index)
        if not items:
            raise StopAsyncIteration
        self._iter_index += 1
        return items[0]
