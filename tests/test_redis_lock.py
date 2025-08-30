import pytest
import pytest_asyncio
import asyncio

from redisify import RedisLock, connect_to_redis, reset


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_lock_basic():
    """Test basic lock acquisition and release."""
    lock = RedisLock("test:lock:basic")

    # Acquire lock
    assert await lock.acquire() is True

    # Release lock
    await lock.release()


@pytest.mark.asyncio
async def test_redis_lock_context_manager():
    """Test lock as async context manager."""
    async with RedisLock("test:lock:ctx") as lock:
        assert lock.id == "redisify:lock:test:lock:ctx"
        # Lock should be automatically released when exiting context


@pytest.mark.asyncio
async def test_redis_lock_unique_tokens():
    """Test that each lock instance has unique tokens."""
    lock1 = RedisLock("test:lock:token1")
    lock2 = RedisLock("test:lock:token2")

    assert lock1.token != lock2.token
    assert lock1.id != lock2.id


@pytest.mark.asyncio
async def test_redis_lock_blocking():
    """Test that lock blocks until acquired."""
    lock1 = RedisLock("test:lock:block", sleep=0.01)
    lock2 = RedisLock("test:lock:block", sleep=0.01)

    # First lock should acquire immediately
    assert await lock1.acquire() is True

    # Second lock should block until first is released
    task = asyncio.create_task(lock2.acquire())

    # Wait a bit to ensure second lock is blocked
    await asyncio.sleep(0.05)
    assert not task.done()

    # Release first lock
    await lock1.release()

    # Second lock should now acquire
    await asyncio.wait_for(task, timeout=1.0)
    assert task.done()

    # Clean up
    await lock2.release()


@pytest.mark.asyncio
async def test_redis_lock_release_own_lock():
    """Test that only the lock owner can release the lock."""
    lock1 = RedisLock("test:lock:owner")
    lock2 = RedisLock("test:lock:owner")

    # First lock acquires
    await lock1.acquire()

    # Second lock tries to release (should not work)
    await lock2.release()

    # First lock should still be held
    # Try to acquire with a third lock to verify
    lock3 = RedisLock("test:lock:owner")
    task = asyncio.create_task(lock3.acquire())

    # Wait a bit to ensure it's still blocked
    await asyncio.sleep(0.05)
    assert not task.done()

    # Clean up
    await lock1.release()
    await asyncio.wait_for(task, timeout=1.0)
    await lock3.release()


@pytest.mark.asyncio
async def test_redis_lock_concurrent_access():
    """Test concurrent access to different locks."""
    locks = [RedisLock(f"test:lock:concurrent:{i}") for i in range(5)]

    # All locks should be able to acquire simultaneously
    acquired = await asyncio.gather(*[lock.acquire() for lock in locks])
    assert all(acquired)

    # Release all locks
    await asyncio.gather(*[lock.release() for lock in locks])


@pytest.mark.asyncio
async def test_redis_lock_custom_sleep():
    """Test lock with custom sleep duration."""
    lock = RedisLock("test:lock:sleep", sleep=0.5)
    assert lock.sleep == 0.5


@pytest.mark.asyncio
async def test_redis_lock_uuid_generation():
    """Test that lock generates UUID if no id provided."""
    lock1 = RedisLock()
    lock2 = RedisLock()

    # Both should have different IDs and tokens
    assert lock1.id != lock2.id
    assert lock1.token != lock2.token
    assert lock1.id.startswith("redisify:lock:")
    assert lock2.id.startswith("redisify:lock:")


@pytest.mark.asyncio
async def test_redis_lock_timeout():
    """Test lock acquisition with timeout."""
    lock1 = RedisLock("test:lock:timeout", sleep=0.01)
    lock2 = RedisLock("test:lock:timeout", sleep=0.01)

    # First lock should acquire immediately
    assert await lock1.acquire() is True

    # Second lock should fail to acquire within timeout
    start_time = asyncio.get_event_loop().time()
    result = await lock2.acquire(timeout=0.1)
    end_time = asyncio.get_event_loop().time()

    assert result is False
    assert end_time - start_time >= 0.1  # Should have waited at least timeout duration

    # Clean up
    await lock1.release()


@pytest.mark.asyncio
async def test_redis_lock_context_manager_timeout():
    """Test lock as async context manager with timeout."""
    lock1 = RedisLock("test:lock:ctx:timeout", sleep=0.01)
    lock2 = RedisLock("test:lock:ctx:timeout", sleep=0.01)

    # First lock should acquire immediately
    async with lock1:
        assert lock1.id == "redisify:lock:test:lock:ctx:timeout"

        # Second lock should block indefinitely in context manager (no timeout)
        task = asyncio.create_task(lock2.__aenter__())

        # Wait a bit to ensure second lock is blocked
        await asyncio.sleep(0.05)
        assert not task.done()

        # Release first lock
        await lock1.release()

        # Second lock should now acquire
        await asyncio.wait_for(task, timeout=1.0)
        assert task.done()

        # Clean up
        await lock2.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_redis_lock_no_timeout():
    """Test lock acquisition without timeout (should wait indefinitely)."""
    lock1 = RedisLock("test:lock:no:timeout", sleep=0.01)
    lock2 = RedisLock("test:lock:no:timeout", sleep=0.01)

    # First lock should acquire immediately
    assert await lock1.acquire() is True

    # Second lock should acquire after first is released (no timeout)
    task = asyncio.create_task(lock2.acquire())  # No timeout specified

    # Wait a bit to ensure second lock is blocked
    await asyncio.sleep(0.05)
    assert not task.done()

    # Release first lock
    await lock1.release()

    # Second lock should now acquire
    await asyncio.wait_for(task, timeout=1.0)
    assert task.done()

    # Clean up
    await lock2.release()
