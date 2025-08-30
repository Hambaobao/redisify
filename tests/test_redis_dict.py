from redisify import RedisDict, connect_to_redis, reset
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_dict():
    rdict = RedisDict("test:dict")
    await rdict.clear()

    await rdict.set("a", "1")
    assert await rdict.get("a") == "1"

    await rdict.set("b", "2")
    assert sorted(await rdict.keys()) == ["a", "b"]
    assert await rdict.get("c", "default") == "default"

    await rdict.delete("a")
    assert await rdict.get("a") is None

    await rdict.update({"x": "100", "y": "200"})
    items = {}
    keys = await rdict.keys()
    for k in keys:
        items[k] = await rdict.get(k)
    assert items["x"] == "100"
    assert "y" in items

    await rdict.clear()
    assert await rdict.size() == 0
