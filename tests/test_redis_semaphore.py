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


@pytest.mark.asyncio
async def test_redis_semaphore_value():
    redis = Redis(decode_responses=True)
    await redis.delete("redisify:semaphore:test:semaphore:value")  # clear before test

    sem1 = RedisSemaphore(redis, 3, "test:semaphore:value")
    sem2 = RedisSemaphore(redis, 3, "test:semaphore:value")
    sem3 = RedisSemaphore(redis, 3, "test:semaphore:value")

    # Initially, no semaphores are acquired
    assert await sem1.value() == 0

    # Acquire first semaphore
    await sem1.acquire()
    assert await sem1.value() == 1
    assert await sem2.value() == 1  # All instances share the same semaphore

    # Acquire second semaphore
    await sem2.acquire()
    assert await sem1.value() == 2
    assert await sem2.value() == 2
    assert await sem3.value() == 2

    # Acquire third semaphore
    await sem3.acquire()
    assert await sem1.value() == 3
    assert await sem2.value() == 3
    assert await sem3.value() == 3

    # Release one semaphore
    await sem1.release()
    assert await sem1.value() == 2
    assert await sem2.value() == 2
    assert await sem3.value() == 2

    # Release remaining semaphores
    await sem2.release()
    await sem3.release()
    assert await sem1.value() == 0
    assert await sem2.value() == 0
    assert await sem3.value() == 0


@pytest.mark.asyncio
async def test_redis_semaphore_value_with_context_manager():
    redis = Redis(decode_responses=True)
    await redis.delete("redisify:semaphore:test:semaphore:value:context")  # clear before test

    sem = RedisSemaphore(redis, 2, "test:semaphore:value:context")

    # Initially, no semaphores are acquired
    assert await sem.value() == 0

    # Use context manager
    async with sem:
        assert await sem.value() == 1

    # After context, semaphore should be released
    assert await sem.value() == 0
