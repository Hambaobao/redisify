"""
Redisify - Redis-backed distributed data structures and synchronization primitives.

Redisify is a lightweight Python library that provides Redis-backed data structures
and distributed synchronization primitives. It is designed for distributed systems
where persistent, shared, and async-compatible data structures are needed.

This package provides the following main components:

Data Structures:
    - RedisDict: A dictionary-like interface backed by Redis hash
    - RedisList: A list-like structure supporting indexing and iteration
    - RedisQueue: A FIFO queue with blocking and async operations
    - RedisSet: A set-like structure with union, intersection, difference operations

Distributed Synchronization:
    - RedisLock: Distributed locking mechanism with automatic cleanup
    - RedisSemaphore: Semaphore for controlling concurrent access
    - RedisLimiter: Rate limiting with token bucket algorithm

All classes support async/await operations and can be used as context managers
with `async with` statements. Complex Python objects are automatically serialized
using the built-in serializer.

Example:
    >>> import asyncio
    >>> from redis.asyncio import Redis
    >>> from redisify import RedisDict, RedisLock
    >>>
    >>> async def example():
    ...     redis = Redis()
    ...     rdict = RedisDict(redis, "example")
    ...     await rdict["key"] = "value"
    ...     value = await rdict["key"]
    ...     print(value)  # 'value'
    ...
    ...     async with RedisLock(redis, "lock"):
    ...         print("Critical section")
    ...
    >>> asyncio.run(example())
"""

from redisify.structures.set import RedisSet
from redisify.structures.list import RedisList
from redisify.structures.dict import RedisDict
from redisify.structures.queue import RedisQueue
from redisify.distributed.lock import RedisLock
from redisify.distributed.semaphore import RedisSemaphore
from redisify.distributed.limiter import RedisLimiter

__all__ = [
    "RedisList",
    "RedisDict",
    "RedisQueue",
    "RedisLock",
    "RedisSemaphore",
    "RedisLimiter",
    "RedisSet",
]

__version__ = "0.1.3"
__author__ = "Lei Zhang"
__email__ = "jameszhang2880@gmail.com"
