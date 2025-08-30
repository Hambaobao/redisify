import uuid

from typing import List, Optional

from redisify.serializer import Serializer
from redisify.config import get_redis


class RedisList:
    """
    A distributed list implementation using Redis.
    
    This class provides a Redis-backed list that can be used across multiple
    processes or servers. The list supports all standard list operations
    including append, pop, indexing, slicing, and iteration.
    
    All items are automatically serialized and deserialized using the provided
    serializer, allowing storage of complex Python objects.
    
    Attributes:
        namespace: The namespace prefix for Redis keys
        id: The Redis key id for this list
        serializer: Serializer instance for object serialization
    """

    namespace: str = "redisify:list"

    def __init__(self, id: str = None, serializer: Serializer = None):
        """
        Initialize a Redis-based distributed list.
        
        Args:
            id: Unique id for this list (auto-generated if None)
            serializer: Serializer instance for object serialization
        """
        self.redis = get_redis()
        _id = id or str(uuid.uuid4())
        self.id = f"{self.namespace}:{_id}"
        self.serializer = serializer or Serializer()

    async def append(self, item):
        """
        Append an item to the end of the list.
        
        Args:
            item: The item to append (will be serialized before storage)
        """
        await self.redis.rpush(self.id, self.serializer.serialize(item))

    async def pop(self):
        """
        Remove and return the last item from the list.
        
        Returns:
            The last item from the list, or None if the list is empty
        """
        val = await self.redis.rpop(self.id)
        return self.serializer.deserialize(val) if val else None

    async def __getitem__(self, index):
        """
        Get an item or slice from the list by index.
        
        Supports both single index access and slice operations. For slices,
        the behavior matches Python's standard list slicing.
        
        Args:
            index: Integer index or slice object
            
        Returns:
            The item at the specified index or a list of items for slices
            
        Raises:
            IndexError: If the index is out of range
        """
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop
            step = index.step or 1

            # redis lrange is inclusive, so we need to subtract 1 from the stop
            end = (stop - 1) if stop is not None else -1

            vals = await self.redis.lrange(self.id, start, end)
            deserialized = [self.serializer.deserialize(v) for v in vals]
            return deserialized[::step]
        else:
            val = await self.redis.lindex(self.id, index)
            if val is None:
                raise IndexError("RedisList index out of range")
            return self.serializer.deserialize(val)

    async def __setitem__(self, index, value):
        """
        Set an item or slice in the list by index.
        
        Supports both single index assignment and slice assignment. For slices,
        the behavior matches Python's standard list slicing.
        
        Args:
            index: Integer index or slice object
            value: The value to assign (will be serialized before storage)
            
        Raises:
            ValueError: If slice assignment size mismatch occurs
        """
        if isinstance(index, slice):
            start = index.start or 0
            stop = index.stop
            step = index.step or 1

            all_vals = await self.redis.lrange(self.id, 0, -1)
            all_items = [self.serializer.deserialize(v) for v in all_vals]

            if step != 1 and len(value) != len(range(start, stop or len(all_items), step)):
                raise ValueError("attempt to assign sequence of size {} to extended slice of size {}".format(len(value), len(range(start, stop or len(all_items), step))))

            all_items[index] = value

            pipeline = self.redis.pipeline()
            pipeline.delete(self.id)
            if all_items:
                pipeline.rpush(self.id, *[self.serializer.serialize(v) for v in all_items])
            await pipeline.execute()
        else:
            await self.redis.lset(self.id, index, self.serializer.serialize(value))

    async def __len__(self):
        """
        Get the length of the list.
        
        Returns:
            The number of items in the list
        """
        return await self.redis.llen(self.id)

    async def get(self, index: int):
        """
        Get an item from the list by index.
        
        This is an alias for __getitem__ for explicit method calls.
        
        Args:
            index: Integer index
            
        Returns:
            The item at the specified index
            
        Raises:
            IndexError: If the index is out of range
        """
        return await self.__getitem__(index)

    async def set(self, index: int, value):
        """
        Set an item in the list by index.
        
        This is an alias for __setitem__ for explicit method calls.
        
        Args:
            index: Integer index
            value: The value to assign (will be serialized before storage)
            
        Raises:
            IndexError: If the index is out of range
        """
        return await self.__setitem__(index, value)

    async def delete(self, index: int):
        """
        Delete an item from the list by index.
        
        This method removes the item at the specified index and shifts
        the remaining items to fill the gap.
        
        Args:
            index: Integer index of the item to delete
            
        Raises:
            IndexError: If the index is out of range
        """
        # Get the current length
        length = await self.redis.llen(self.id)
        if index < 0:
            index = length + index
        if index < 0 or index >= length:
            raise IndexError("RedisList index out of range")

        # Remove the item by index
        # Redis doesn't have a direct LREM by index, so we need to reconstruct
        all_items = await self.redis.lrange(self.id, 0, -1)
        if index < len(all_items):
            del all_items[index]
            # Clear and repopulate
            await self.redis.delete(self.id)
            if all_items:
                await self.redis.rpush(self.id, *all_items)

    async def size(self) -> int:
        """
        Get the number of items in the list.
        
        This is an alias for __len__ for explicit method calls.
        
        Returns:
            The number of items in the list
        """
        return await self.__len__()

    async def clear(self):
        """
        Remove all items from the list.
        
        This method deletes the entire list from Redis.
        """
        await self.redis.delete(self.id)

    async def range(self, start: int = 0, end: int = -1):
        """
        Get a range of items from the list.
        
        Args:
            start: Starting index (inclusive)
            end: Ending index (inclusive, -1 for end of list)
            
        Returns:
            List of items in the specified range
        """
        vals = await self.redis.lrange(self.id, start, end)
        return [self.serializer.deserialize(v) for v in vals]

    async def remove(self, value, count: int = 1):
        """
        Remove occurrences of a value from the list.
        
        Args:
            value: The value to remove (will be serialized for comparison)
            count: Number of occurrences to remove (0 for all)
        """
        # match serialized value
        serialized = self.serializer.serialize(value)
        await self.redis.lrem(self.id, count, serialized)

    async def insert(self, index: int, value):
        """
        Insert an item at a specific position in the list.
        
        Args:
            index: Position where to insert the item
            value: The item to insert (will be serialized before storage)
            
        Raises:
            IndexError: If the index is out of range
        """
        all_items = await self.redis.lrange(self.id, 0, -1)
        deserialized = [self.serializer.deserialize(v) for v in all_items]

        if index < 0:
            index += len(deserialized)
        if index < 0 or index > len(deserialized):
            raise IndexError("Insert index out of range")

        deserialized.insert(index, value)
        serialized = [self.serializer.serialize(v) for v in deserialized]

        pipeline = self.redis.pipeline()
        pipeline.delete(self.id)
        if serialized:
            pipeline.rpush(self.id, *serialized)
        await pipeline.execute()

    def __aiter__(self):
        """
        Return an async iterator for the list.
        
        Returns:
            Self instance configured for async iteration
        """
        self._aiter_index = 0
        return self

    async def __anext__(self):
        """
        Get the next item during async iteration.
        
        Returns:
            The next item in the list
            
        Raises:
            StopAsyncIteration: When iteration is complete
        """
        val = await self.redis.lindex(self.id, self._aiter_index)
        if val is None:
            raise StopAsyncIteration
        self._aiter_index += 1
        return self.serializer.deserialize(val)
