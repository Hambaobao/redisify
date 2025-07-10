import uuid

from redis.asyncio import Redis
from redisify.serializer import Serializer


class RedisSet:
    """
    A distributed set implementation using Redis.
    
    This class provides a Redis-backed set that can be used across multiple
    processes or servers. The set supports all standard set operations
    including add, remove, membership testing, and set operations like
    union, intersection, and difference.
    
    All items are automatically serialized and deserialized using the provided
    serializer, allowing storage of complex Python objects.
    
    Attributes:
        redis: The Redis client instance
        name: The Redis key name for this set
        serializer: Serializer instance for object serialization
    """

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        """
        Initialize a Redis-based distributed set.
        
        Args:
            redis: Redis client instance
            name: Unique name for this set (auto-generated if None)
            serializer: Serializer instance for object serialization
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:set:{_name}"
        self.serializer = serializer or Serializer()

    async def add(self, item):
        """
        Add an item to the set.
        
        Args:
            item: The item to add (will be serialized before storage)
        """
        await self.redis.sadd(self.name, self.serializer.serialize(item))

    async def remove(self, item):
        """
        Remove an item from the set.
        
        Args:
            item: The item to remove (will be serialized for comparison)
            
        Raises:
            KeyError: If the item is not in the set
        """
        removed = await self.redis.srem(self.name, self.serializer.serialize(item))
        if not removed:
            raise KeyError(item)

    async def discard(self, item):
        """
        Remove an item from the set if it exists.
        
        Unlike remove(), this method does not raise an exception if the
        item is not in the set.
        
        Args:
            item: The item to remove (will be serialized for comparison)
        """
        await self.redis.srem(self.name, self.serializer.serialize(item))

    async def pop(self):
        """
        Remove and return an arbitrary item from the set.
        
        Returns:
            An arbitrary item from the set
            
        Raises:
            KeyError: If the set is empty
        """
        val = await self.redis.spop(self.name)
        if val is None:
            raise KeyError('pop from an empty set')
        return self.serializer.deserialize(val)

    async def clear(self):
        """
        Remove all items from the set.
        
        This method deletes the entire set from Redis.
        """
        await self.redis.delete(self.name)

    async def size(self):
        """
        Get the number of items in the set.
        
        Returns:
            The number of items in the set
        """
        return await self.redis.scard(self.name)

    async def __contains__(self, item):
        """
        Check if an item is in the set.
        
        Args:
            item: The item to check (will be serialized for comparison)
            
        Returns:
            True if the item is in the set, False otherwise
        """
        return await self.redis.sismember(self.name, self.serializer.serialize(item))

    async def __len__(self):
        """
        Get the number of items in the set.
        
        Returns:
            The number of items in the set
        """
        return await self.redis.scard(self.name)

    async def to_set(self):
        """
        Convert the Redis set to a regular Python set.
        
        This method retrieves all items from the Redis set and returns
        them as a standard Python set.
        
        Returns:
            Python set containing all items from the Redis set
        """
        members = await self.redis.smembers(self.name)
        return set(self.serializer.deserialize(m) for m in members)

    def __aiter__(self):
        """
        Return an async iterator for the set.
        
        Returns:
            Self instance configured for async iteration
        """
        self._aiter_members = None
        self._aiter_index = 0
        return self

    async def __anext__(self):
        """
        Get the next item during async iteration.
        
        Returns:
            The next item in the set
            
        Raises:
            StopAsyncIteration: When iteration is complete
        """
        if self._aiter_members is None:
            self._aiter_members = list(await self.to_set())
        if self._aiter_index >= len(self._aiter_members):
            raise StopAsyncIteration
        item = self._aiter_members[self._aiter_index]
        self._aiter_index += 1
        return item

    async def update(self, *others):
        """
        Update the set with items from other sets.
        
        This method adds all items from the provided sets to this set.
        The others can be RedisSet instances or regular Python sets/iterables.
        
        Args:
            *others: Sets or iterables containing items to add
        """
        pipe = self.redis.pipeline()
        for other in others:
            if isinstance(other, RedisSet):
                other = await other.to_set()
            for item in other:
                pipe.sadd(self.name, self.serializer.serialize(item))
        await pipe.execute()

    async def difference(self, *others):
        """
        Return the difference of this set and others.
        
        This method returns a new set containing items that are in this set
        but not in any of the other sets.
        
        Args:
            *others: Sets or iterables to compute difference with
            
        Returns:
            Set containing items in this set but not in others
        """
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
        """
        Return the union of this set and others.
        
        This method returns a new set containing all items that are in this set
        or in any of the other sets.
        
        Args:
            *others: Sets or iterables to compute union with
            
        Returns:
            Set containing all items from this set and others
        """
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
        """
        Return the intersection of this set and others.
        
        This method returns a new set containing items that are in this set
        and in all of the other sets.
        
        Args:
            *others: Sets or iterables to compute intersection with
            
        Returns:
            Set containing items common to this set and all others
        """
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
        """
        Check if this set is a subset of another set.
        
        Args:
            other: Set or iterable to check against
            
        Returns:
            True if this set is a subset of other, False otherwise
        """
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.issubset(other)

    async def issuperset(self, other):
        """
        Check if this set is a superset of another set.
        
        Args:
            other: Set or iterable to check against
            
        Returns:
            True if this set is a superset of other, False otherwise
        """
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.issuperset(other)

    async def isdisjoint(self, other):
        """
        Check if this set has no elements in common with another set.
        
        Args:
            other: Set or iterable to check against
            
        Returns:
            True if this set has no elements in common with other, False otherwise
        """
        if isinstance(other, RedisSet):
            other = await other.to_set()
        this_set = await self.to_set()
        return this_set.isdisjoint(other)
