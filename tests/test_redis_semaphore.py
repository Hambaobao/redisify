import pytest
from redis.asyncio import Redis
from redisify import RedisSemaphore


@pytest.mark.asyncio
async def test_redis_semaphore_manual_release():
    redis = Redis(decode_responses=True)
    await redis.delete("test:semaphore")  # clear before test

    sem1 = RedisSemaphore(redis, "test:semaphore", limit=2)
    sem2 = RedisSemaphore(redis, "test:semaphore", limit=2)
    sem3 = RedisSemaphore(redis, "test:semaphore", limit=2)

    assert await sem1.acquire()
    assert await sem2.acquire()
    assert not await sem3.acquire()  # limit reached

    await sem1.release()
    assert await sem3.acquire()  # now possible
    await sem2.release()
    await sem3.release()


@pytest.mark.asyncio
async def test_redis_semaphore_async_with():
    redis = Redis(decode_responses=True)
    await redis.delete("test:semaphore:with")

    sem = RedisSemaphore(redis, "test:semaphore:with", limit=1)

    async with sem:
        rank = await redis.zrank("test:semaphore:with", sem.token)
        assert rank == 0  # we're inside the semaphore

    # should be removed after release
    rank_after = await redis.zrank("test:semaphore:with", sem.token)
    assert rank_after is None
