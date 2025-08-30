"""
Redisify - Redis-backed data structures and distributed synchronization primitives.

A lightweight Python library that provides Redis-backed data structures like dicts, 
queues, locks, and semaphores, designed for distributed systems.
"""

__version__ = "0.2.0"

from redisify.structures.set import RedisSet
from redisify.structures.list import RedisList
from redisify.structures.dict import RedisDict
from redisify.structures.queue import RedisQueue
from redisify.distributed.lock import RedisLock
from redisify.distributed.semaphore import RedisSemaphore
from redisify.distributed.limiter import RedisLimiter

from redisify.config import connect_to_redis, reset

__all__ = [
    "RedisList",
    "RedisDict",
    "RedisQueue",
    "RedisLock",
    "RedisSemaphore",
    "RedisLimiter",
    "RedisSet",
    "connect_to_redis",
    "reset",
    "__version__",
]
