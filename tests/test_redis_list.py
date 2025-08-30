from redisify import RedisList, connect_to_redis, reset
import pytest


@pytest.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_list():
    rlist = RedisList("test:list")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.insert(1, "x")  # a, x, b

    assert await rlist.__getitem__(0) == "a"
    assert await rlist.__getitem__(1) == "x"
    assert await rlist.__getitem__(2) == "b"

    await rlist.__setitem__(2, "z")
    assert await rlist.__getitem__(2) == "z"

    values = await rlist.range(0, -1)
    assert values == ["a", "x", "z"]

    async for item in rlist:
        assert item in values

    await rlist.clear()
    assert await rlist.__len__() == 0
