import pytest
from redis.asyncio import Redis
from redisify import RedisLock


@pytest.mark.asyncio
async def test_redis_lock_acquire_and_release():
    redis = Redis(decode_responses=True)
    lock = RedisLock(redis, "test:lock")

    # lock should be acquirable
    acquired = await lock.acquire()
    assert acquired

    # trying to acquire it again should block, so we skip this test
    await lock.release()

    # now it should be acquirable again
    acquired2 = await lock.acquire()
    assert acquired2
    await lock.release()


@pytest.mark.asyncio
async def test_redis_lock_async_with():
    redis = Redis(decode_responses=True)
    lock = RedisLock(redis, "test:lock:with")

    async with lock:
        val = await redis.get(lock.name)
        assert val is not None  # lock exists in Redis

    # After context, lock should be released
    val = await redis.get(lock.name)
    assert val is None
