from typing import Dict, List, Tuple, Any
from redis.asyncio import Redis
import uuid

from redisify.serializer import Serializer


class RedisDict:

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:dict:{_name}"
        self.serializer = serializer or Serializer()

    async def __getitem__(self, key):
        key_s = self.serializer.serialize(key)
        val = await self.redis.hget(self.name, key_s)
        if val is None:
            raise KeyError(key)
        return self.serializer.deserialize(val)

    async def __setitem__(self, key, value):
        key_s = self.serializer.serialize(key)
        val_s = self.serializer.serialize(value)
        await self.redis.hset(self.name, key_s, val_s)

    async def __delitem__(self, key):
        key_s = self.serializer.serialize(key)
        await self.redis.hdel(self.name, key_s)

    async def keys(self):
        keys_raw = await self.redis.hkeys(self.name)
        return [self.serializer.deserialize(k) for k in keys_raw]

    async def values(self):
        vals_raw = await self.redis.hvals(self.name)
        return [self.serializer.deserialize(v) for v in vals_raw]

    async def items(self):
        return _AsyncItemsIterator(self)

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
        key_s = self.serializer.serialize(key)
        return await self.redis.hexists(self.name, key_s)

    async def __len__(self) -> int:
        return await self.redis.hlen(self.name)

    async def set(self, key, value):
        key_s = self.serializer.serialize(key)
        val_s = self.serializer.serialize(value)
        await self.redis.hset(self.name, key_s, val_s)

    async def get(self, key, default=None):
        key_s = self.serializer.serialize(key)
        val = await self.redis.hget(self.name, key_s)
        return self.serializer.deserialize(val) if val is not None else default

    async def delete(self, key):
        """Delete a single key-value pair by key."""
        key_s = self.serializer.serialize(key)
        await self.redis.hdel(self.name, key_s)

    async def setdefault(self, key, default):
        key_s = self.serializer.serialize(key)
        exists = await self.redis.hexists(self.name, key_s)
        if not exists:
            val_s = self.serializer.serialize(default)
            await self.redis.hset(self.name, key_s, val_s)
            return default
        val = await self.redis.hget(self.name, key_s)
        return self.serializer.deserialize(val)

    async def clear(self):
        await self.redis.delete(self.name)

    async def update(self, mapping: dict):
        pipe = self.redis.pipeline()
        for k, v in mapping.items():
            pipe.hset(self.name, self.serializer.serialize(k), self.serializer.serialize(v))
        await pipe.execute()


class _AsyncItemsIterator:

    def __init__(self, redis_dict: RedisDict):
        self.redis_dict = redis_dict
        self._keys = None
        self._index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._keys is None:
            self._keys = await self.redis_dict.keys()
        if self._index >= len(self._keys):
            raise StopAsyncIteration
        key = self._keys[self._index]
        self._index += 1
        val = await self.redis_dict.get(key)
        return key, val

    async def to_dict(self) -> Dict:
        d = {}
        async for k, v in self:
            d[k] = v
        return d

    def __repr__(self):
        return f"<AsyncItemsIterator over {self.redis_dict.name}>"
