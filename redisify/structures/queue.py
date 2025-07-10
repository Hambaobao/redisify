import uuid
import asyncio
from redis.asyncio import Redis
from redisify.serializer import Serializer


class RedisQueue:
    """
    A distributed queue implementation using Redis.
    
    This class provides a Redis-backed queue that can be used across multiple
    processes or servers. The queue supports both blocking and non-blocking
    operations for putting and getting items.
    
    All items are automatically serialized and deserialized using the provided
    serializer, allowing storage of complex Python objects.
    
    The queue can optionally enforce a maximum size limit, causing put operations
    to block when the queue is full.
    
    Attributes:
        redis: The Redis client instance
        name: The Redis key name for this queue
        serializer: Serializer instance for object serialization
        maxsize: Maximum number of items in the queue (None for unlimited)
        sleep: Sleep duration between blocking operations
    """

    def __init__(
        self,
        redis: Redis,
        name: str = None,
        maxsize: int = None,
        serializer: Serializer = None,
        sleep: float = 0.1,
    ):
        """
        Initialize a Redis-based distributed queue.
        
        Args:
            redis: Redis client instance
            name: Unique name for this queue (auto-generated if None)
            maxsize: Maximum number of items in the queue (None for unlimited)
            serializer: Serializer instance for object serialization
            sleep: Sleep duration between blocking operations in seconds
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:queue:{_name}"
        self.serializer = serializer or Serializer()
        self.maxsize = maxsize
        self.sleep = sleep

    async def put(self, item):
        """
        Put an item into the queue.
        
        If maxsize is set and the queue is full, this method will block
        until space becomes available.
        
        Args:
            item: The item to add to the queue (will be serialized before storage)
        """
        if self.maxsize is not None:
            while await self.qsize() >= self.maxsize:
                await asyncio.sleep(self.sleep)
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def put_nowait(self, item):
        """
        Put an item into the queue without blocking.
        
        If maxsize is set and the queue is full, this method will raise
        QueueFull instead of blocking.
        
        Args:
            item: The item to add to the queue (will be serialized before storage)
            
        Raises:
            asyncio.QueueFull: If the queue is full and maxsize is set
        """
        if self.maxsize is not None and await self.qsize() >= self.maxsize:
            raise asyncio.QueueFull("RedisQueue is full")
        await self.redis.rpush(self.name, self.serializer.serialize(item))

    async def get(self):
        """
        Get an item from the queue, blocking until one is available.
        
        This method will block indefinitely until an item becomes available
        in the queue.
        
        Returns:
            The next item from the queue, or None if the queue is empty
        """
        result = await self.redis.blpop(self.name, timeout=0)
        return self.serializer.deserialize(result[1]) if result else None

    async def get_nowait(self):
        """
        Get an item from the queue without blocking.
        
        This method returns immediately with the next item if available,
        or None if the queue is empty.
        
        Returns:
            The next item from the queue, or None if the queue is empty
        """
        val = await self.redis.lpop(self.name)
        return self.serializer.deserialize(val) if val else None

    async def peek(self):
        """
        Peek at the first item in the queue without removing it.
        
        This method returns the first item in the queue without removing
        it from the queue.
        
        Returns:
            The first item in the queue, or None if the queue is empty
        """
        items = await self.redis.lrange(self.name, 0, 0)
        return self.serializer.deserialize(items[0]) if items else None

    async def qsize(self) -> int:
        """
        Get the current number of items in the queue.
        
        Returns:
            The number of items currently in the queue
        """
        return await self.redis.llen(self.name)

    async def empty(self) -> bool:
        """
        Check if the queue is empty.
        
        Returns:
            True if the queue is empty, False otherwise
        """
        return await self.qsize() == 0

    async def clear(self):
        """
        Remove all items from the queue.
        
        This method deletes the entire queue from Redis.
        """
        await self.redis.delete(self.name)

    def __aiter__(self):
        """
        Return an async iterator for the queue.
        
        Returns:
            Self instance configured for async iteration
        """
        self._iter_index = 0
        return self

    async def __anext__(self):
        """
        Get the next item during async iteration.
        
        Returns:
            The next item in the queue
            
        Raises:
            StopAsyncIteration: When iteration is complete
        """
        item = await self.redis.lindex(self.name, self._iter_index)
        if item is None:
            raise StopAsyncIteration
        self._iter_index += 1
        return self.serializer.deserialize(item)
