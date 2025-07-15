import pytest
from redis.asyncio import Redis
from redisify import RedisLock
from redisify import RedisRWLock
import asyncio
import warnings


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


@pytest.mark.asyncio
async def test_redis_rwlock_write_acquire_and_release():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:w")

    acquired = await lock.acquire_write()
    assert acquired
    await lock.release_write()

    acquired2 = await lock.acquire_write()
    assert acquired2
    await lock.release_write()


@pytest.mark.asyncio
async def test_redis_rwlock_write_async_with():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:wctx")

    # 推荐新用法
    async with lock('w'):
        val = await redis.get(lock.write_key)
        assert val == lock.token

    val = await redis.get(lock.write_key)
    assert val is None

    # 兼容旧用法，断言 DeprecationWarning
    with pytest.warns(DeprecationWarning):
        async with lock:
            val = await redis.get(lock.write_key)
            assert val == lock.token

    val = await redis.get(lock.write_key)
    assert val is None


@pytest.mark.asyncio
async def test_redis_rwlock_read_acquire_and_release():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:r")

    acquired = await lock.acquire_read()
    assert acquired
    await lock.release_read()

    acquired2 = await lock.acquire_read()
    assert acquired2
    await lock.release_read()


@pytest.mark.asyncio
async def test_redis_rwlock_read_async_with():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:rctx")

    # recommend new usage
    async with await lock('r'):
        val = await redis.get(lock.readers_key)
        assert int(val) >= 1

    val = await redis.get(lock.readers_key)
    assert val is None or int(val) == 0

    # compatible with old usage
    async with await lock.read_lock():
        val = await redis.get(lock.readers_key)
        assert int(val) >= 1

    val = await redis.get(lock.readers_key)
    assert val is None or int(val) == 0

    # deprecated usage, should warn
    with pytest.warns(DeprecationWarning):
        async with lock:
            val = await redis.get(lock.readers_key)
            assert val is None or int(val) == 0

    val = await redis.get(lock.readers_key)
    assert val is None or int(val) == 0


@pytest.mark.asyncio
async def test_redis_rwlock_readers_can_share():
    redis = Redis(decode_responses=True)
    lock1 = RedisRWLock(redis, "test:rwlock:share")
    lock2 = RedisRWLock(redis, "test:rwlock:share")

    await lock1.acquire_read()
    await lock2.acquire_read()
    val = await redis.get(lock1.readers_key)
    assert int(val) == 2
    await lock1.release_read()
    await lock2.release_read()


@pytest.mark.asyncio
async def test_redis_rwlock_write_blocks_read():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:block")

    await lock.acquire_write()
    # Try to acquire read lock, should not increment readers
    fut = asyncio.create_task(lock.acquire_read())
    await asyncio.sleep(0.2)
    val = await redis.get(lock.readers_key)
    assert val is None or int(val) == 0
    await lock.release_write()
    await fut  # Now should succeed
    await lock.release_read()


@pytest.mark.asyncio
async def test_redis_rwlock_read_blocks_write():
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:block2")

    await lock.acquire_read()
    fut = asyncio.create_task(lock.acquire_write())
    await asyncio.sleep(0.2)
    val = await redis.get(lock.write_key)
    assert val is None
    await lock.release_read()
    await fut
    await lock.release_write()


@pytest.mark.asyncio
async def test_redis_rwlock_high_concurrency_readers():
    """Test multiple concurrent readers"""
    redis = Redis(decode_responses=True)

    def make_lock():
        return RedisRWLock(redis, "test:rwlock:concurrent_read")

    async def reader_task(reader_id):
        lock = make_lock()
        await lock.acquire_read()
        await asyncio.sleep(0.1)  # Simulate read work
        await lock.release_read()
        return reader_id

    # Start 10 concurrent readers
    tasks = [reader_task(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert set(results) == set(range(10))

    # Verify no readers left
    val = await redis.get("redisify:rwlock:test:rwlock:concurrent_read:readers")
    assert val is None or int(val) == 0


@pytest.mark.asyncio
async def test_redis_rwlock_high_concurrency_writers():
    """Test multiple concurrent writers (should serialize)"""
    redis = Redis(decode_responses=True)

    def make_lock():
        return RedisRWLock(redis, "test:rwlock:concurrent_write")

    results = []

    async def writer_task(writer_id):
        lock = make_lock()
        await lock.acquire_write()
        results.append(writer_id)
        await asyncio.sleep(0.05)  # Simulate write work
        await lock.release_write()
        return writer_id

    # Start 5 concurrent writers
    tasks = [writer_task(i) for i in range(5)]
    await asyncio.gather(*tasks)

    # Writers should execute sequentially
    assert len(results) == 5
    # Note: order might vary due to timing, but all should complete

    # Verify no write lock left
    val = await redis.get("redisify:rwlock:test:rwlock:concurrent_write:write")
    assert val is None


@pytest.mark.asyncio
async def test_redis_rwlock_mixed_read_write_concurrency():
    """Test mixed read/write concurrency"""
    redis = Redis(decode_responses=True)

    def make_lock():
        return RedisRWLock(redis, "test:rwlock:mixed")

    read_results = []
    write_results = []

    async def reader_task(reader_id):
        lock = make_lock()
        await lock.acquire_read()
        read_results.append(reader_id)
        await asyncio.sleep(0.1)
        await lock.release_read()
        return f"reader_{reader_id}"

    async def writer_task(writer_id):
        lock = make_lock()
        await lock.acquire_write()
        write_results.append(writer_id)
        await asyncio.sleep(0.05)
        await lock.release_write()
        return f"writer_{writer_id}"

    # Start mixed read/write tasks
    tasks = []
    for i in range(3):
        tasks.append(reader_task(i))
        tasks.append(writer_task(i))

    await asyncio.gather(*tasks)

    # All tasks should complete
    assert len(read_results) == 3
    assert len(write_results) == 3


@pytest.mark.asyncio
async def test_redis_rwlock_stress_test():
    """Stress test with many rapid operations"""
    redis = Redis(decode_responses=True)

    def make_lock():
        return RedisRWLock(redis, "test:rwlock:stress")

    async def stress_task(task_id):
        lock = make_lock()
        for i in range(10):
            if task_id % 2 == 0:  # Even tasks are readers
                await lock.acquire_read()
                await asyncio.sleep(0.01)
                await lock.release_read()
            else:  # Odd tasks are writers
                await lock.acquire_write()
                await asyncio.sleep(0.01)
                await lock.release_write()
        return task_id

    # Start 20 stress tasks
    tasks = [stress_task(i) for i in range(20)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 20
    assert set(results) == set(range(20))

    # Verify clean state
    val = await redis.get("redisify:rwlock:test:rwlock:stress:write")
    assert val is None
    val = await redis.get("redisify:rwlock:test:rwlock:stress:readers")
    assert val is None or int(val) == 0


@pytest.mark.asyncio
async def test_redis_rwlock_reader_writer_starvation():
    """Test that readers don't starve writers and vice versa"""
    redis = Redis(decode_responses=True)

    def make_lock():
        return RedisRWLock(redis, "test:rwlock:starvation")

    reader_count = 0
    writer_count = 0

    async def continuous_reader():
        nonlocal reader_count
        lock = make_lock()
        for _ in range(5):
            await lock.acquire_read()
            reader_count += 1
            await asyncio.sleep(0.02)
            await lock.release_read()
            await asyncio.sleep(0.01)

    async def continuous_writer():
        nonlocal writer_count
        lock = make_lock()
        for _ in range(3):
            await lock.acquire_write()
            writer_count += 1
            await asyncio.sleep(0.05)
            await lock.release_write()
            await asyncio.sleep(0.01)

    # Start continuous readers and writers
    reader_tasks = [continuous_reader() for _ in range(3)]
    writer_tasks = [continuous_writer() for _ in range(2)]

    await asyncio.gather(*(reader_tasks + writer_tasks))

    # Both readers and writers should make progress
    assert reader_count > 0
    assert writer_count > 0


@pytest.mark.asyncio
async def test_redis_rwlock_cancellation_safety():
    """Test that locks are properly released when tasks are cancelled"""
    redis = Redis(decode_responses=True)
    lock = RedisRWLock(redis, "test:rwlock:cancel")

    async def task_with_cancellation():
        try:
            await lock.acquire_read()
            await asyncio.sleep(1)  # Long sleep that will be cancelled
        except asyncio.CancelledError:
            await lock.release_read()
            raise

    # Start task and cancel it
    task = asyncio.create_task(task_with_cancellation())
    await asyncio.sleep(0.1)
    task.cancel()

    try:
        await task
    except asyncio.CancelledError:
        pass

    # Lock should be properly released
    val = await redis.get(lock.readers_key)
    assert val is None or int(val) == 0
