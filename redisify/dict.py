from redis import Redis
import uuid


class RedisDict:

    def __init__(self, redis: Redis, name: str = None):
        self.redis = redis
        self.name = name or str(uuid.uuid4())

    async def __getitem__(self, key):
        val = await self.redis.hget(self.name, key)
        if val is None:
            raise KeyError(key)
        return val

    async def __setitem__(self, key, value):
        await self.redis.hset(self.name, key, value)

    async def __delitem__(self, key):
        await self.redis.hdel(self.name, key)

    async def keys(self):
        return await self.redis.hkeys(self.name)

    async def items(self):
        return await self.redis.hgetall(self.name)

    def __aiter__(self):
        self._iter_keys = None
        self._iter_index = 0
        return self

    async def __anext__(self):
        if self._iter_keys is None:
            self._iter_keys = await self.keys()
        if self._iter_index >= len(self._iter_keys):
            raise StopAsyncIteration
        key = self._iter_keys[self._iter_index]
        self._iter_index += 1
        return key

    async def __contains__(self, key) -> bool:
        return await self.redis.hexists(self.name, key)

    async def __len__(self) -> int:
        return await self.redis.hlen(self.name)

    async def get(self, key, default=None):
        val = await self.redis.hget(self.name, key)
        return val if val is not None else default

    async def setdefault(self, key, default):
        exists = await self.redis.hexists(self.name, key)
        if not exists:
            await self.redis.hset(self.name, key, default)
            return default
        return await self.redis.hget(self.name, key)

    async def values(self):
        return await self.redis.hvals(self.name)

    async def clear(self):
        await self.redis.delete(self.name)

    async def update(self, mapping: dict):
        if mapping:
            await self.redis.hset(self.name, mapping)
