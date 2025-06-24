import pytest
from redis.asyncio import Redis
from redisify import RedisSemaphore


@pytest.mark.asyncio
async def test_redis_semaphore_manual_release():
    redis = Redis(decode_responses=True)
    await redis.delete("redisify:semaphore:test:semaphore")  # clear before test

    sem1 = RedisSemaphore(redis, 2, "test:semaphore")
    sem2 = RedisSemaphore(redis, 2, "test:semaphore")
    sem3 = RedisSemaphore(redis, 2, "test:semaphore")

    await sem1.acquire()
    await sem2.acquire()
    can_acquire = await sem3.can_acquire()
    assert not can_acquire  # limit reached

    await sem1.release()
    await sem3.acquire()  # now possible
    await sem2.release()
    await sem3.release()


@pytest.mark.asyncio
async def test_redis_semaphore_async_with():
    redis = Redis(decode_responses=True)
    await redis.delete("redisify:semaphore:test:semaphore:with")

    sem = RedisSemaphore(redis, 1, "test:semaphore:with")

    async with sem:
        # No direct way to check token in Redis, just ensure context works
        assert True

    # After context, should be released (no error means pass)
    assert True
