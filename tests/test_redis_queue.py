from redis.asyncio import Redis
from redisify import RedisQueue
import pytest


@pytest.mark.asyncio
async def test_redis_queue():
    redis = Redis(decode_responses=True)
    queue = RedisQueue(redis, "test:queue")
    await queue.clear()

    await queue.put("job1")
    await queue.put("job2")

    assert await queue.peek() == "job1"
    assert await queue.size() == 2
    assert not await queue.is_empty()

    job = await queue.get()
    assert job == "job1"

    job2 = await queue.get_block(timeout=1)
    assert job2 == "job2"

    assert await queue.get() is None  # empty
    await queue.clear()
    assert await queue.is_empty()
