from typing import Dict, List, Tuple, Any
from redis.asyncio import Redis
import uuid

from redisify.serializer import Serializer


class RedisDict:
    """
    A distributed dictionary implementation using Redis.
    
    This class provides a Redis-backed dictionary that can be used across multiple
    processes or servers. The dictionary supports all standard dict operations
    including get, set, delete, iteration, and membership testing.
    
    All keys and values are automatically serialized and deserialized using the
    provided serializer, allowing storage of complex Python objects as both keys
    and values.
    
    Attributes:
        redis: The Redis client instance
        name: The Redis key name for this dictionary
        serializer: Serializer instance for object serialization
    """

    def __init__(self, redis: Redis, name: str = None, serializer: Serializer = None):
        """
        Initialize a Redis-based distributed dictionary.
        
        Args:
            redis: Redis client instance
            name: Unique name for this dictionary (auto-generated if None)
            serializer: Serializer instance for object serialization
        """
        self.redis = redis
        _name = name or str(uuid.uuid4())
        self.name = f"redisify:dict:{_name}"
        self.serializer = serializer or Serializer()

    async def __getitem__(self, key):
        """
        Get a value from the dictionary by key.
        
        Args:
            key: The key to look up (will be serialized for comparison)
            
        Returns:
            The value associated with the key
            
        Raises:
            KeyError: If the key is not found
        """
        key_s = self.serializer.serialize(key)
        val = await self.redis.hget(self.name, key_s)
        if val is None:
            raise KeyError(key)
        return self.serializer.deserialize(val)

    async def __setitem__(self, key, value):
        """
        Set a key-value pair in the dictionary.
        
        Args:
            key: The key to set (will be serialized before storage)
            value: The value to associate with the key (will be serialized before storage)
        """
        key_s = self.serializer.serialize(key)
        val_s = self.serializer.serialize(value)
        await self.redis.hset(self.name, key_s, val_s)

    async def __delitem__(self, key):
        """
        Delete a key-value pair from the dictionary.
        
        Args:
            key: The key to delete (will be serialized for comparison)
        """
        key_s = self.serializer.serialize(key)
        await self.redis.hdel(self.name, key_s)

    async def keys(self):
        """
        Get all keys in the dictionary.
        
        Returns:
            List of all keys in the dictionary
        """
        keys_raw = await self.redis.hkeys(self.name)
        return [self.serializer.deserialize(k) for k in keys_raw]

    async def values(self):
        """
        Get all values in the dictionary.
        
        Returns:
            List of all values in the dictionary
        """
        vals_raw = await self.redis.hvals(self.name)
        return [self.serializer.deserialize(v) for v in vals_raw]

    async def items(self):
        """
        Get an async iterator for all key-value pairs.
        
        Returns:
            AsyncItemsIterator instance for iterating over key-value pairs
        """
        return _AsyncItemsIterator(self)

    def __aiter__(self):
        """
        Return an async iterator for the dictionary keys.
        
        Returns:
            Self instance configured for async iteration over keys
        """
        self._iter_keys = None
        self._iter_index = 0
        return self

    async def __anext__(self):
        """
        Get the next key during async iteration.
        
        Returns:
            The next key in the dictionary
            
        Raises:
            StopAsyncIteration: When iteration is complete
        """
        if self._iter_keys is None:
            self._iter_keys = await self.keys()
        if self._iter_index >= len(self._iter_keys):
            raise StopAsyncIteration
        key = self._iter_keys[self._iter_index]
        self._iter_index += 1
        return key

    async def __contains__(self, key) -> bool:
        """
        Check if a key exists in the dictionary.
        
        Args:
            key: The key to check (will be serialized for comparison)
            
        Returns:
            True if the key exists, False otherwise
        """
        key_s = self.serializer.serialize(key)
        return await self.redis.hexists(self.name, key_s)

    async def __len__(self) -> int:
        """
        Get the number of key-value pairs in the dictionary.
        
        Returns:
            The number of items in the dictionary
        """
        return await self.redis.hlen(self.name)

    async def set(self, key, value):
        """
        Set a key-value pair in the dictionary.
        
        This is an alias for __setitem__ for explicit method calls.
        
        Args:
            key: The key to set (will be serialized before storage)
            value: The value to associate with the key (will be serialized before storage)
        """
        key_s = self.serializer.serialize(key)
        val_s = self.serializer.serialize(value)
        await self.redis.hset(self.name, key_s, val_s)

    async def get(self, key, default=None):
        """
        Get a value from the dictionary by key, returning a default if not found.
        
        Args:
            key: The key to look up (will be serialized for comparison)
            default: Value to return if the key is not found
            
        Returns:
            The value associated with the key, or the default value if not found
        """
        key_s = self.serializer.serialize(key)
        val = await self.redis.hget(self.name, key_s)
        return self.serializer.deserialize(val) if val is not None else default

    async def delete(self, key):
        """
        Delete a single key-value pair by key.
        
        Args:
            key: The key to delete (will be serialized for comparison)
        """
        key_s = self.serializer.serialize(key)
        await self.redis.hdel(self.name, key_s)

    async def setdefault(self, key, default):
        """
        Get a value from the dictionary, setting it to default if not present.
        
        If the key exists, return its value. If the key doesn't exist,
        set it to the default value and return the default.
        
        Args:
            key: The key to look up or set (will be serialized before storage)
            default: Default value to set if the key doesn't exist
            
        Returns:
            The value associated with the key, or the default value if it was set
        """
        key_s = self.serializer.serialize(key)
        exists = await self.redis.hexists(self.name, key_s)
        if not exists:
            val_s = self.serializer.serialize(default)
            await self.redis.hset(self.name, key_s, val_s)
            return default
        val = await self.redis.hget(self.name, key_s)
        return self.serializer.deserialize(val)

    async def clear(self):
        """
        Remove all key-value pairs from the dictionary.
        
        This method deletes the entire dictionary from Redis.
        """
        await self.redis.delete(self.name)

    async def update(self, mapping: dict):
        """
        Update the dictionary with key-value pairs from another mapping.
        
        Args:
            mapping: Dictionary containing key-value pairs to add or update
        """
        pipe = self.redis.pipeline()
        for k, v in mapping.items():
            pipe.hset(self.name, self.serializer.serialize(k), self.serializer.serialize(v))
        await pipe.execute()


class _AsyncItemsIterator:
    """
    Async iterator for key-value pairs in a RedisDict.
    
    This class provides an async iterator that yields (key, value) tuples
    for all items in the dictionary.
    
    Attributes:
        redis_dict: The RedisDict instance to iterate over
        _keys: Cached list of keys for iteration
        _index: Current iteration index
    """

    def __init__(self, redis_dict: RedisDict):
        """
        Initialize the async items iterator.
        
        Args:
            redis_dict: The RedisDict instance to iterate over
        """
        self.redis_dict = redis_dict
        self._keys = None
        self._index = 0

    def __aiter__(self):
        """
        Return self as an async iterator.
        
        Returns:
            Self instance for async iteration
        """
        return self

    async def __anext__(self):
        """
        Get the next key-value pair during async iteration.
        
        Returns:
            Tuple of (key, value) for the next item
            
        Raises:
            StopAsyncIteration: When iteration is complete
        """
        if self._keys is None:
            self._keys = await self.redis_dict.keys()
        if self._index >= len(self._keys):
            raise StopAsyncIteration
        key = self._keys[self._index]
        self._index += 1
        val = await self.redis_dict.get(key)
        return key, val

    async def to_dict(self) -> Dict:
        """
        Convert the iterator to a regular Python dictionary.
        
        This method iterates through all key-value pairs and builds
        a standard Python dictionary.
        
        Returns:
            Dictionary containing all key-value pairs
        """
        d = {}
        async for k, v in self:
            d[k] = v
        return d

    def __repr__(self):
        """
        String representation of the iterator.
        
        Returns:
            String describing the iterator
        """
        return f"<AsyncItemsIterator over {self.redis_dict.name}>"
