# Redisify

**Redisify** is a lightweight Python library that provides Redis-backed data structures and distributed synchronization primitives. It is designed for distributed systems where persistent, shared, and async-compatible data structures are needed.

## Features

### Data Structures
- 📦 **RedisDict**: A dictionary-like interface backed by Redis hash with full CRUD operations
- 📋 **RedisList**: A list-like structure supporting indexing, insertion, deletion, and iteration
- 🔄 **RedisQueue**: A FIFO queue with blocking and async operations
- 🎯 **RedisSet**: A set-like structure with union, intersection, difference operations

### Distributed Synchronization
- 🔐 **RedisLock**: Distributed locking mechanism with automatic cleanup
- 🚦 **RedisSemaphore**: Semaphore for controlling concurrent access
- ⏱️ **RedisLimiter**: Rate limiting with token bucket algorithm

### Advanced Features
- 🔄 **Async/Await Support**: All operations are async-compatible
- 📦 **Smart Serialization**: Automatic serialization of complex objects including Pydantic models
- 🎯 **Context Manager Support**: Use with `async with` statements
- 🧪 **Comprehensive Testing**: Full test coverage for all components

## Installation

```bash
pip install redisify
```

Or for development and testing:

```bash
git clone https://github.com/Hambaobao/redisify.git
cd redisify
pip install -e .[test]
```

## Quick Start

```python
import asyncio
from redis.asyncio import Redis
from redisify import RedisDict, RedisList, RedisQueue, RedisSet, RedisLock, RedisSemaphore, RedisLimiter

async def main():
    redis = Redis()
    
    # Dictionary operations
    rdict = RedisDict(redis, "example:dict")
    await rdict["user:1"] = {"name": "Alice", "age": 30}
    user = await rdict["user:1"]
    print(user)  # {'name': 'Alice', 'age': 30}
    
    # List operations
    rlist = RedisList(redis, "example:list")
    await rlist.append("item1")
    await rlist.append("item2")
    first_item = await rlist[0]
    print(first_item)  # item1
    
    # Queue operations
    rqueue = RedisQueue(redis, "example:queue")
    await rqueue.put("task1")
    await rqueue.put("task2")
    task = await rqueue.get()
    print(task)  # task1
    
    # Set operations
    rset = RedisSet(redis, "example:set")
    await rset.add("item1")
    await rset.add("item2")
    items = await rset.to_set()
    print(items)  # {'item1', 'item2'}

asyncio.run(main())
```

## Detailed Usage

### RedisDict

```python
from redisify import RedisDict

rdict = RedisDict(redis, "users")

# Basic operations
await rdict["user1"] = {"name": "Alice", "age": 30}
await rdict["user2"] = {"name": "Bob", "age": 25}

# Get values
user1 = await rdict["user1"]
print(user1)  # {'name': 'Alice', 'age': 30}

# Check existence
if "user1" in rdict:
    print("User exists")

# Delete items
del await rdict["user2"]

# Iterate over items
async for key, value in rdict.items():
    print(f"{key}: {value}")
```

### RedisList

```python
from redisify import RedisList

rlist = RedisList(redis, "tasks")

# Add items
await rlist.append("task1")
await rlist.append("task2")
await rlist.insert(0, "priority_task")

# Access by index
first_task = await rlist[0]
print(first_task)  # priority_task

# Get length
length = await len(rlist)
print(length)  # 3

# Iterate
async for item in rlist:
    print(item)
```

### RedisQueue

```python
from redisify import RedisQueue

rqueue = RedisQueue(redis, "job_queue")

# Producer
await rqueue.put("job1")
await rqueue.put("job2")

# Consumer
job = await rqueue.get()  # Blocks until item available
print(job)  # job1

# Non-blocking get
try:
    job = await rqueue.get_nowait()
except QueueEmpty:
    print("Queue is empty")
```

### RedisSet

```python
from redisify import RedisSet

set1 = RedisSet(redis, "set1")
set2 = RedisSet(redis, "set2")

# Add items
await set1.add("item1")
await set1.add("item2")
await set2.add("item2")
await set2.add("item3")

# Set operations
union = await set1.union(set2)
intersection = await set1.intersection(set2)
difference = await set1.difference(set2)

print(union)  # {'item1', 'item2', 'item3'}
print(intersection)  # {'item2'}
print(difference)  # {'item1'}
```

### RedisLock

```python
from redisify import RedisLock

lock = RedisLock(redis, "resource_lock")

# Manual lock/unlock
await lock.acquire()
try:
    # Critical section
    print("Resource locked")
finally:
    await lock.release()

# Context manager (recommended)
async with RedisLock(redis, "resource_lock"):
    print("Resource locked automatically")
    # Lock is automatically released
```

### RedisSemaphore

```python
from redisify import RedisSemaphore

# Limit to 3 concurrent operations
semaphore = RedisSemaphore(redis, limit=3, name="api_limit")

async def api_call():
    async with semaphore:
        print("API call executing")
        await asyncio.sleep(1)

# Run multiple concurrent calls
tasks = [api_call() for _ in range(10)]
await asyncio.gather(*tasks)

# Check current semaphore value
current_value = await semaphore.value()
print(f"Currently {current_value} semaphores are acquired")
```

### RedisLimiter

```python
from redisify import RedisLimiter

# Rate limit: 10 requests per minute
limiter = RedisLimiter(redis, "api_rate", rate_limit=10, time_period=60)

async def make_request():
    if await limiter.acquire():
        print("Request allowed")
        # Make API call
    else:
        print("Rate limit exceeded")

# Context manager with automatic retry
async with RedisLimiter(redis, "api_rate", rate_limit=10, time_period=60):
    print("Request allowed")
    # Make API call
```

## Serialization

Redisify includes a smart serializer that handles complex objects:

```python
from pydantic import BaseModel
from redisify import RedisDict

class User(BaseModel):
    name: str
    age: int

user = User(name="Alice", age=30)
rdict = RedisDict(redis, "users")

# Pydantic models are automatically serialized
await rdict["user1"] = user

# And automatically deserialized
retrieved_user = await rdict["user1"]
print(type(retrieved_user))  # <class '__main__.User'>
print(retrieved_user.name)  # Alice
```

## Requirements

- Python 3.10+
- Redis server (local or remote)
- redis Python client (redis-py)

## Testing

Make sure you have Redis running (locally or via Docker), then:

```bash
# Run all tests
pytest -v tests

# Run with coverage
pytest --cov=redisify tests

# Run specific test file
pytest tests/test_redis_dict.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Changelog

### v0.1.0
- Initial release with RedisDict, RedisList, RedisQueue
- Added RedisSet with full set operations
- Implemented RedisLock for distributed locking
- Added RedisSemaphore for concurrency control
- Introduced RedisLimiter with token bucket algorithm
- Smart serialization supporting Pydantic models
- Comprehensive async/await support
- Full test coverage
