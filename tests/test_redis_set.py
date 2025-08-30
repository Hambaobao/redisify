from redisify import RedisSet, connect_to_redis, reset
import pytest
import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_redis_set_basic():
    rset = RedisSet("test:set")
    await rset.clear()

    await rset.add("a")
    await rset.add("b")
    await rset.add("c")
    assert await rset.size() == 3
    assert await rset.contains("a")
    assert not await rset.contains("x")

    s = await rset.to_set()
    assert s == {"a", "b", "c"}

    await rset.remove("b")
    assert await rset.to_set() == {"a", "c"}

    await rset.discard("x")  # should not raise
    await rset.discard("a")
    assert await rset.to_set() == {"c"}

    popped = await rset.pop()
    assert popped == "c"
    assert await rset.size() == 0

    await rset.clear()
    assert await rset.size() == 0


@pytest.mark.asyncio
async def test_redis_set_update_and_setops():
    s1 = RedisSet("test:set1")
    s2 = RedisSet("test:set2")
    await s1.clear()
    await s2.clear()
    await s1.update([1, 2, 3])
    await s2.update([3, 4, 5])

    assert await s1.to_set() == {1, 2, 3}
    assert await s2.to_set() == {3, 4, 5}

    diff = await s1.difference(s2)
    assert diff == {1, 2}
    union = await s1.union(s2)
    assert union == {1, 2, 3, 4, 5}
    inter = await s1.intersection(s2)
    assert inter == {3}

    assert await s1.issubset([1, 2, 3, 4])
    assert await s1.issuperset([1, 2])
    assert await s1.isdisjoint([4, 5, 6])


@pytest.mark.asyncio
async def test_redis_set_async_iter():
    rset = RedisSet("test:set:iter")
    await rset.clear()
    await rset.update(["x", "y", "z"])
    items = set()
    async for item in rset:
        items.add(item)
    assert items == {"x", "y", "z"}
    await rset.clear()
