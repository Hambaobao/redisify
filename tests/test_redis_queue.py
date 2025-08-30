from redisify import RedisQueue, connect_to_redis, reset
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_queue():
    queue = RedisQueue("test:queue")
    await queue.clear()

    await queue.put("job1")
    await queue.put("job2")

    assert await queue.peek() == "job1"
    assert await queue.qsize() == 2
    assert not await queue.empty()

    job = await queue.get()
    assert job == "job1"

    job2 = await queue.get()
    assert job2 == "job2"

    assert await queue.get_nowait() is None  # empty
    await queue.clear()
    assert await queue.empty()
