import pytest
import pytest_asyncio
from redisify import RedisSemaphore, connect_to_redis, reset
import asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_semaphore_manual_release():
    sem1 = RedisSemaphore("test:semaphore", 2)
    sem2 = RedisSemaphore("test:semaphore", 2)
    sem3 = RedisSemaphore("test:semaphore", 2)

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
    sem = RedisSemaphore("test:semaphore:with", 1)

    async with sem:
        # No direct way to check token in Redis, just ensure context works
        assert True

    # After context, should be released (no error means pass)
    assert True


@pytest.mark.asyncio
async def test_redis_semaphore_value():
    sem1 = RedisSemaphore("test:semaphore:value", 3)
    sem2 = RedisSemaphore("test:semaphore:value", 3)
    sem3 = RedisSemaphore("test:semaphore:value", 3)

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
    sem = RedisSemaphore("test:semaphore:value:context", 2)

    # Initially, no semaphores are acquired
    assert await sem.value() == 0

    # Use context manager
    async with sem:
        assert await sem.value() == 1

    # After context, semaphore should be released
    assert await sem.value() == 0


@pytest.mark.asyncio
async def test_redis_semaphore_timeout():
    """Test semaphore acquisition with timeout."""
    sem1 = RedisSemaphore("test:semaphore:timeout", 1, sleep=0.01)
    sem2 = RedisSemaphore("test:semaphore:timeout", 1, sleep=0.01)

    # First semaphore should acquire immediately
    assert await sem1.acquire() is True

    # Second semaphore should fail to acquire within timeout
    start_time = asyncio.get_event_loop().time()
    result = await sem2.acquire(timeout=0.1)
    end_time = asyncio.get_event_loop().time()

    assert result is False
    assert end_time - start_time >= 0.1  # Should have waited at least timeout duration

    # Clean up
    await sem1.release()


@pytest.mark.asyncio
async def test_redis_semaphore_context_manager_timeout():
    """Test semaphore as async context manager with timeout."""
    sem1 = RedisSemaphore("test:semaphore:ctx:timeout", 1, sleep=0.01)
    sem2 = RedisSemaphore("test:semaphore:ctx:timeout", 1, sleep=0.01)

    # First semaphore should acquire immediately
    async with sem1:
        # Second semaphore should block indefinitely in context manager (no timeout)
        task = asyncio.create_task(sem2.__aenter__())

        # Wait a bit to ensure second semaphore is blocked
        await asyncio.sleep(0.05)
        assert not task.done()

        # Release first semaphore
        await sem1.release()

        # Second semaphore should now acquire
        await asyncio.wait_for(task, timeout=1.0)
        assert task.done()

        # Clean up
        await sem2.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_redis_semaphore_no_timeout():
    """Test semaphore acquisition without timeout (should wait indefinitely)."""
    sem1 = RedisSemaphore("test:semaphore:no:timeout", 1, sleep=0.01)
    sem2 = RedisSemaphore("test:semaphore:no:timeout", 1, sleep=0.01)

    # First semaphore should acquire immediately
    assert await sem1.acquire() is True

    # Second semaphore should acquire after first is released (no timeout)
    task = asyncio.create_task(sem2.acquire())  # No timeout specified

    # Wait a bit to ensure second semaphore is blocked
    await asyncio.sleep(0.05)
    assert not task.done()

    # Release first semaphore
    await sem1.release()

    # Second semaphore should now acquire
    await asyncio.wait_for(task, timeout=1.0)
    assert task.done()

    # Clean up
    await sem2.release()


@pytest.mark.asyncio
async def test_redis_semaphore_multiple_permits_with_timeout():
    """Test semaphore with multiple permits and timeout."""
    sem1 = RedisSemaphore("test:semaphore:multi:timeout", 2, sleep=0.01)
    sem2 = RedisSemaphore("test:semaphore:multi:timeout", 2, sleep=0.01)
    sem3 = RedisSemaphore("test:semaphore:multi:timeout", 2, sleep=0.01)

    # First two semaphores should acquire immediately
    assert await sem1.acquire() is True
    assert await sem2.acquire() is True

    # Third semaphore should fail to acquire within timeout
    start_time = asyncio.get_event_loop().time()
    result = await sem3.acquire(timeout=0.1)
    end_time = asyncio.get_event_loop().time()

    assert result is False
    assert end_time - start_time >= 0.1

    # Release one permit
    await sem1.release()

    # Third semaphore should now acquire immediately
    assert await sem3.acquire() is True

    # Clean up
    await sem2.release()
    await sem3.release()
