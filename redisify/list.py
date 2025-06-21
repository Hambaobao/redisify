from redis.asyncio import Redis
import uuid


class RedisList:

    def __init__(self, redis: Redis, name: str = None):
        self.redis = redis
        self.name = name or str(uuid.uuid4())

    async def append(self, item: str):
        await self.redis.rpush(self.name, item)

    async def pop(self) -> str | None:
        return await self.redis.rpop(self.name)

    async def __getitem__(self, index: int) -> str:
        val = await self.redis.lindex(self.name, index)
        if val is None:
            raise IndexError("RedisList index out of range")
        return val

    async def __setitem__(self, index: int, value: str):
        await self.redis.lset(self.name, index, value)

    async def __len__(self) -> int:
        return await self.redis.llen(self.name)

    async def clear(self):
        await self.redis.delete(self.name)

    async def range(self, start: int = 0, end: int = -1) -> list[str]:
        return await self.redis.lrange(self.name, start, end)

    async def remove(self, value: str, count: int = 1):
        await self.redis.lrem(self.name, count, value)

    async def insert(self, index: int, value: str):
        all_items = await self.redis.lrange(self.name, 0, -1)
        if index < 0:
            index += len(all_items)
        if index < 0 or index > len(all_items):
            raise IndexError("Insert index out of range")

        all_items.insert(index, value)
        pipeline = self.redis.pipeline()
        pipeline.delete(self.name)
        if all_items:
            pipeline.rpush(self.name, *all_items)
        await pipeline.execute()

    def __aiter__(self):
        self._aiter_index = 0
        return self

    async def __anext__(self):
        items = await self.redis.lrange(self.name, self._aiter_index, self._aiter_index)
        if not items:
            raise StopAsyncIteration
        self._aiter_index += 1
        return items[0]
