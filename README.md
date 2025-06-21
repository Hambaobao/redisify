# Redisify

**Redisify** is a lightweight Python library that provides Redis-backed data structures such as `RedisDict`, `RedisList`, and `RedisQueue`. It is designed for distributed systems where persistent, shared, and async-compatible data structures are needed.

## Features

- 📦 **RedisDict**: A dictionary-like interface backed by Redis hash.
- 📋 **RedisList**: A list-like structure supporting indexing, insertion, and iteration.
- 🔁 **RedisQueue**: A simple FIFO queue with blocking and async operations.
- 🔐 (Coming soon) RedisLock, RedisSemaphore for concurrency control.

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

## Usage Example

```python
from redis.asyncio import Redis
from redisify import RedisDict, RedisList, RedisQueue

redis = Redis()

# Dict example
rdict = RedisDict(redis, "example:dict")
await rdict.__setitem__("key", "value")
print(await rdict["key"])  # Output: value

# List example
rlist = RedisList(redis, "example:list")
await rlist.append("item")
print(await rlist[0])  # Output: item

# Queue example
rqueue = RedisQueue(redis, "example:queue")
await rqueue.put("task1")
print(await rqueue.get())  # Output: task1
```

## Requirements

- Python 3.10+
- Redis server (local or remote)
- redis Python client (redis-py)

## Testing

Make sure you have Redis running (locally or via Docker), then:

```bash
pytest -v tests
```

## License

This project is licensed under the MIT License.
