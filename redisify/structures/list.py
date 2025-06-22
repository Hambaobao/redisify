from redis.asyncio import Redis
import uuid

from redisify.serializer import Serializer


class RedisList:

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:list:{_name}"
        self.serializer = serializer or Serializer()

    async def append(self, item):
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def pop(self):
        val = await self.redis.rpop(self.name)
        return self.serializer.deserialize(val) if val else None

    async def __getitem__(self, index):
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop
            step = index.step or 1

            # redis lrange is inclusive, so we need to subtract 1 from the stop
            end = (stop - 1) if stop is not None else -1

            vals = await self.redis.lrange(self.name, start, end)
            deserialized = [self.serializer.deserialize(v) for v in vals]
            return deserialized[::step]
        else:
            val = await self.redis.lindex(self.name, index)
            if val is None:
                raise IndexError("RedisList index out of range")
            return self.serializer.deserialize(val)

    async def __setitem__(self, index, value):
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop
            step = index.step or 1

            all_vals = await self.redis.lrange(self.name, 0, -1)
            all_items = [self.serializer.deserialize(v) for v in all_vals]

            if step != 1 and len(value) != len(range(start, stop or len(all_items), step)):
                raise ValueError("attempt to assign sequence of size {} to extended slice of size {}".format(len(value), len(range(start, stop or len(all_items), step))))

            all_items[index] = value

            pipeline = self.redis.pipeline()
            pipeline.delete(self.name)
            if all_items:
                pipeline.rpush(self.name, *[self.serializer.serialize(v) for v in all_items])
            await pipeline.execute()
        else:
            await self.redis.lset(self.name, index, self.serializer.serialize(value))

    async def __len__(self):
        return await self.redis.llen(self.name)

    async def clear(self):
        await self.redis.delete(self.name)

    async def range(self, start: int = 0, end: int = -1):
        vals = await self.redis.lrange(self.name, start, end)
        return [self.serializer.deserialize(v) for v in vals]

    async def remove(self, value, count: int = 1):
        # match serialized value
        serialized = self.serializer.serialize(value)
        await self.redis.lrem(self.name, count, serialized)

    async def insert(self, index: int, value):
        all_items = await self.redis.lrange(self.name, 0, -1)
        deserialized = [self.serializer.deserialize(v) for v in all_items]

        if index < 0:
            index += len(deserialized)
        if index < 0 or index > len(deserialized):
            raise IndexError("Insert index out of range")

        deserialized.insert(index, value)
        serialized = [self.serializer.serialize(v) for v in deserialized]

        pipeline = self.redis.pipeline()
        pipeline.delete(self.name)
        if serialized:
            pipeline.rpush(self.name, *serialized)
        await pipeline.execute()

    def __aiter__(self):
        self._aiter_index = 0
        return self

    async def __anext__(self):
        val = await self.redis.lindex(self.name, self._aiter_index)
        if val is None:
            raise StopAsyncIteration
        self._aiter_index += 1
        return self.serializer.deserialize(val)
