import uuid

from redis.asyncio import Redis
from redisify.serializer import Serializer


class RedisSet:

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:set:{_name}"
        self.serializer = serializer or Serializer()

    async def add(self, item):
        await self.redis.sadd(self.name, self.serializer.serialize(item))

    async def remove(self, item):
        removed = await self.redis.srem(self.name, self.serializer.serialize(item))
        if not removed:
            raise KeyError(item)

    async def discard(self, item):
        await self.redis.srem(self.name, self.serializer.serialize(item))

    async def pop(self):
        val = await self.redis.spop(self.name)
        if val is None:
            raise KeyError('pop from an empty set')
        return self.serializer.deserialize(val)

    async def clear(self):
        await self.redis.delete(self.name)

    async def size(self):
        return await self.redis.scard(self.name)

    async def __contains__(self, item):
        return await self.redis.sismember(self.name, self.serializer.serialize(item))

    async def __len__(self):
        return await self.redis.scard(self.name)

    async def to_set(self):
        members = await self.redis.smembers(self.name)
        return set(self.serializer.deserialize(m) for m in members)

    def __aiter__(self):
        self._aiter_members = None
        self._aiter_index = 0
        return self

    async def __anext__(self):
        if self._aiter_members is None:
            self._aiter_members = list(await self.to_set())
        if self._aiter_index >= len(self._aiter_members):
            raise StopAsyncIteration
        item = self._aiter_members[self._aiter_index]
        self._aiter_index += 1
        return item

    async def update(self, *others):
        pipe = self.redis.pipeline()
        for other in others:
            if isinstance(other, RedisSet):
                other = await other.to_set()
            for item in other:
                pipe.sadd(self.name, self.serializer.serialize(item))
        await pipe.execute()

    async def difference(self, *others):
        sets = [self.name]
        for other in others:
            if isinstance(other, RedisSet):
                sets.append(other.name)
            else:
                # create a temp set for non-RedisSet
                temp_name = f"redisify:temp:{uuid.uuid4()}"
                await self.redis.sadd(temp_name, *[self.serializer.serialize(i) for i in other])
                sets.append(temp_name)
        diff = await self.redis.sdiff(*sets)
        # cleanup temp sets
        for name in sets[1:]:
            if name.startswith("redisify:temp:"):
                await self.redis.delete(name)
        return set(self.serializer.deserialize(m) for m in diff)

    async def union(self, *others):
        sets = [self.name]
        for other in others:
            if isinstance(other, RedisSet):
                sets.append(other.name)
            else:
                temp_name = f"redisify:temp:{uuid.uuid4()}"
                await self.redis.sadd(temp_name, *[self.serializer.serialize(i) for i in other])
                sets.append(temp_name)
        union = await self.redis.sunion(*sets)
        for name in sets[1:]:
            if name.startswith("redisify:temp:"):
                await self.redis.delete(name)
        return set(self.serializer.deserialize(m) for m in union)

    async def intersection(self, *others):
        sets = [self.name]
        for other in others:
            if isinstance(other, RedisSet):
                sets.append(other.name)
            else:
                temp_name = f"redisify:temp:{uuid.uuid4()}"
                await self.redis.sadd(temp_name, *[self.serializer.serialize(i) for i in other])
                sets.append(temp_name)
        inter = await self.redis.sinter(*sets)
        for name in sets[1:]:
            if name.startswith("redisify:temp:"):
                await self.redis.delete(name)
        return set(self.serializer.deserialize(m) for m in inter)

    async def issubset(self, other):
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.issubset(other)

    async def issuperset(self, other):
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.issuperset(other)

    async def isdisjoint(self, other):
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.isdisjoint(other)
