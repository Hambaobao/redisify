from redis.asyncio import Redis
from redisify import RedisDict
import pytest


@pytest.mark.asyncio
async def test_redis_dict():
    redis = Redis(decode_responses=True)
    rdict = RedisDict(redis, "test:dict")
    await rdict.clear()

    await rdict.__setitem__("a", "1")
    assert await rdict.__getitem__("a") == "1"

    await rdict.__setitem__("b", "2")
    assert sorted(await rdict.keys()) == ["a", "b"]
    assert await rdict.get("c", "default") == "default"

    await rdict.__delitem__("a")
    assert await rdict.get("a") is None

    await rdict.update({"x": "100", "y": "200"})
    items = {}
    keys = await rdict.keys()
    for k in keys:
        items[k] = await rdict.get(k)
    assert items["x"] == "100"
    assert "y" in items

    await rdict.clear()
    assert await rdict.__len__() == 0
