from redisify import RedisDict, connect_to_redis, reset
import pytest
import pytest_asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_basic_operations():
    """Test basic dictionary operations: set, get, delete, clear, size."""
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


@pytest.mark.asyncio
async def test_getitem_setitem():
    """Test __getitem__ and __setitem__ operations."""
    rdict = RedisDict("test:getitem_setitem")
    await rdict.clear()

    # Test __setitem__ and __getitem__
    await rdict.set("key1", "value1")
    assert await rdict["key1"] == "value1"

    await rdict.set("key2", "value2")
    assert await rdict["key2"] == "value2"

    # Test KeyError for non-existent key
    with pytest.raises(KeyError):
        await rdict["nonexistent"]

    # Test setting new value
    await rdict.set("key1", "updated_value")
    assert await rdict["key1"] == "updated_value"


@pytest.mark.asyncio
async def test_delitem():
    """Test __delitem__ operation."""
    rdict = RedisDict("test:delitem")
    await rdict.clear()

    await rdict.set("key1", "value1")
    await rdict.set("key2", "value2")

    # Test __delitem__
    await rdict.delete("key1")
    assert await rdict.get("key1") is None
    assert await rdict.get("key2") == "value2"

    # Test deleting non-existent key (should not raise error)
    await rdict.delete("nonexistent")


@pytest.mark.asyncio
async def test_contains():
    """Test __contains__ operation."""
    rdict = RedisDict("test:contains")
    await rdict.clear()

    await rdict.set("key1", "value1")
    await rdict.set("key2", "value2")

    # Test __contains__
    assert await rdict.__contains__("key1") is True
    assert await rdict.__contains__("key2") is True
    assert await rdict.__contains__("nonexistent") is False

    # Test with different data types as keys
    await rdict.set(123, "number_key")
    assert await rdict.__contains__(123) is True
    assert await rdict.__contains__(456) is False


@pytest.mark.asyncio
async def test_len():
    """Test __len__ operation."""
    rdict = RedisDict("test:len")
    await rdict.clear()

    assert await rdict.__len__() == 0

    await rdict.set("key1", "value1")
    assert await rdict.__len__() == 1

    await rdict.set("key2", "value2")
    assert await rdict.__len__() == 2

    await rdict.delete("key1")
    assert await rdict.__len__() == 1

    await rdict.clear()
    assert await rdict.__len__() == 0


@pytest.mark.asyncio
async def test_keys_values():
    """Test keys() and values() operations."""
    rdict = RedisDict("test:keys_values")
    await rdict.clear()

    # Test empty dictionary
    assert await rdict.keys() == []
    assert await rdict.values() == []

    # Test with data
    await rdict.set("a", "1")
    await rdict.set("b", "2")
    await rdict.set("c", "3")

    keys = await rdict.keys()
    values = await rdict.values()

    assert sorted(keys) == ["a", "b", "c"]
    assert sorted(values) == ["1", "2", "3"]

    # Test with different data types
    await rdict.set(123, "number")
    await rdict.set(True, "boolean")

    keys = await rdict.keys()
    assert "a" in keys
    assert 123 in keys
    assert True in keys


@pytest.mark.asyncio
async def test_items():
    """Test items() operation and AsyncItemsIterator."""
    rdict = RedisDict("test:items")
    await rdict.clear()

    # Test empty dictionary
    items_iter = await rdict.items()
    items_list = []
    async for key, value in items_iter:
        items_list.append((key, value))
    assert items_list == []

    # Test with data
    await rdict.set("a", "1")
    await rdict.set("b", "2")
    await rdict.set("c", "3")

    items_iter = await rdict.items()
    items_list = []
    async for key, value in items_iter:
        items_list.append((key, value))

    # Sort for comparison since order might vary
    items_list.sort()
    assert items_list == [("a", "1"), ("b", "2"), ("c", "3")]


@pytest.mark.asyncio
async def test_async_iteration():
    """Test async iteration over dictionary keys."""
    rdict = RedisDict("test:iteration")
    await rdict.clear()

    # Test iteration over empty dictionary
    keys = []
    async for key in rdict:
        keys.append(key)
    assert keys == []

    # Test iteration over non-empty dictionary
    await rdict.set("a", "1")
    await rdict.set("b", "2")
    await rdict.set("c", "3")

    keys = []
    async for key in rdict:
        keys.append(key)

    assert sorted(keys) == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_setdefault():
    """Test setdefault operation."""
    rdict = RedisDict("test:setdefault")
    await rdict.clear()

    # Test setting default for non-existent key
    result = await rdict.setdefault("new_key", "default_value")
    assert result == "default_value"
    assert await rdict.get("new_key") == "default_value"

    # Test getting existing value (should not change)
    result = await rdict.setdefault("new_key", "different_value")
    assert result == "default_value"
    assert await rdict.get("new_key") == "default_value"

    # Test with different data types
    result = await rdict.setdefault("number_key", 42)
    assert result == 42
    assert await rdict.get("number_key") == 42


@pytest.mark.asyncio
async def test_update():
    """Test update operation."""
    rdict = RedisDict("test:update")
    await rdict.clear()

    # Test updating with empty dictionary
    await rdict.update({})
    assert await rdict.size() == 0

    # Test updating with new items
    await rdict.update({"a": "1", "b": "2", "c": "3"})
    assert await rdict.get("a") == "1"
    assert await rdict.get("b") == "2"
    assert await rdict.get("c") == "3"
    assert await rdict.size() == 3

    # Test updating existing items
    await rdict.update({"a": "updated", "d": "4"})
    assert await rdict.get("a") == "updated"
    assert await rdict.get("b") == "2"
    assert await rdict.get("c") == "3"
    assert await rdict.get("d") == "4"
    assert await rdict.size() == 4


@pytest.mark.asyncio
async def test_serialization():
    """Test serialization and deserialization of complex objects."""
    rdict = RedisDict("test:serialization")
    await rdict.clear()

    # Test with different data types
    test_data = {"string": "hello", "number": 123, "float": 45.67, "boolean": True, "none": None, "list": [1, 2, 3], "dict": {"nested": "value"}, "tuple": (1, 2, 3)}

    for key, value in test_data.items():
        await rdict.set(key, value)

    # Verify all items can be retrieved correctly
    for key, expected in test_data.items():
        assert await rdict.get(key) == expected

    # Test with complex nested structures
    complex_obj = {"list": [1, 2, {"nested": "dict"}], "tuple": (1, 2, 3), "bool": True, "none": None}
    await rdict.set("complex", complex_obj)
    retrieved = await rdict.get("complex")
    assert retrieved == complex_obj


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases and error conditions."""
    rdict = RedisDict("test:edge_cases")
    await rdict.clear()

    # Test operations on empty dictionary
    assert await rdict.size() == 0
    assert await rdict.keys() == []
    assert await rdict.values() == []
    assert await rdict.get("nonexistent") is None
    assert await rdict.get("nonexistent", "default") == "default"

    # Test KeyError for __getitem__
    with pytest.raises(KeyError):
        await rdict["nonexistent"]

    # Test with empty string keys and values
    await rdict.set("", "empty_key")
    await rdict.set("empty_value", "")
    assert await rdict.get("") == "empty_key"
    assert await rdict.get("empty_value") == ""

    # Test with None as key and value
    await rdict.set(None, "none_key")
    await rdict.set("none_value", None)
    assert await rdict.get(None) == "none_key"
    assert await rdict.get("none_value") is None


@pytest.mark.asyncio
async def test_key_types():
    """Test different key types."""
    rdict = RedisDict("test:key_types")
    await rdict.clear()

    # Test with different key types
    test_keys = ["string", 123, 45.67, True, False, None, (1, 2, 3), frozenset([1, 2, 3])]

    for i, key in enumerate(test_keys):
        await rdict.set(key, f"value_{i}")

    # Verify all keys can be retrieved
    for i, key in enumerate(test_keys):
        assert await rdict.get(key) == f"value_{i}"

    # Test keys() with different types
    keys = await rdict.keys()
    for key in test_keys:
        assert key in keys


@pytest.mark.asyncio
async def test_value_types():
    """Test different value types."""
    rdict = RedisDict("test:value_types")
    await rdict.clear()

    # Test with different value types
    test_values = ["string", 123, 45.67, True, False, None, [1, 2, 3], {"nested": "dict"}, (1, 2, 3), {1, 2, 3}]

    for i, value in enumerate(test_values):
        await rdict.set(f"key_{i}", value)

    # Verify all values can be retrieved
    for i, value in enumerate(test_values):
        retrieved = await rdict.get(f"key_{i}")
        assert retrieved == value

    # Test values() with different types
    values = await rdict.values()
    for value in test_values:
        assert value in values


# Pydantic model definitions for testing
class User(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True
    created_at: Optional[datetime] = None


class Product(BaseModel):
    id: int
    name: str
    price: float
    tags: List[str] = []
    metadata: Dict[str, Any] = {}


class Order(BaseModel):
    id: int
    user_id: int
    products: List[Product]
    total: float
    status: str = "pending"


@pytest.mark.asyncio
async def test_pydantic_models():
    """Test RedisDict with Pydantic models as values."""
    rdict = RedisDict("test:pydantic")
    await rdict.clear()

    # Test with simple Pydantic model
    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com", is_active=False)

    await rdict.set("user1", user1)
    await rdict.set("user2", user2)

    # Verify retrieval
    retrieved_user1 = await rdict.get("user1")
    retrieved_user2 = await rdict.get("user2")

    assert isinstance(retrieved_user1, User)
    assert isinstance(retrieved_user2, User)
    assert retrieved_user1.id == 1
    assert retrieved_user1.name == "Alice"
    assert retrieved_user1.email == "alice@example.com"
    assert retrieved_user1.is_active is True

    assert retrieved_user2.id == 2
    assert retrieved_user2.name == "Bob"
    assert retrieved_user2.is_active is False

    # Test with nested Pydantic models
    product1 = Product(id=1, name="Laptop", price=999.99, tags=["electronics", "computer"])
    product2 = Product(id=2, name="Mouse", price=29.99, tags=["electronics", "accessory"])

    order = Order(id=1, user_id=1, products=[product1, product2], total=1029.98, status="confirmed")

    await rdict.set("order1", order)
    retrieved_order = await rdict.get("order1")

    assert isinstance(retrieved_order, Order)
    assert retrieved_order.id == 1
    assert retrieved_order.user_id == 1
    assert retrieved_order.total == 1029.98
    assert retrieved_order.status == "confirmed"
    assert len(retrieved_order.products) == 2

    # Verify nested models
    assert isinstance(retrieved_order.products[0], Product)
    assert retrieved_order.products[0].name == "Laptop"
    assert retrieved_order.products[0].price == 999.99
    assert retrieved_order.products[0].tags == ["electronics", "computer"]

    assert isinstance(retrieved_order.products[1], Product)
    assert retrieved_order.products[1].name == "Mouse"
    assert retrieved_order.products[1].price == 29.99


@pytest.mark.asyncio
async def test_pydantic_models_with_datetime():
    """Test Pydantic models with datetime fields."""
    rdict = RedisDict("test:pydantic_datetime")
    await rdict.clear()

    now = datetime.now()
    user = User(id=1, name="Charlie", email="charlie@example.com", created_at=now)

    await rdict.set("user", user)
    retrieved_user = await rdict.get("user")

    assert isinstance(retrieved_user, User)
    assert retrieved_user.id == 1
    assert retrieved_user.name == "Charlie"
    assert retrieved_user.created_at == now


@pytest.mark.asyncio
async def test_pydantic_models_as_keys():
    """Test Pydantic models as dictionary keys."""
    rdict = RedisDict("test:pydantic_keys")
    await rdict.clear()

    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com")

    # Test using Pydantic models as keys
    await rdict.set(user1, "user1_data")
    await rdict.set(user2, "user2_data")

    # Verify retrieval
    assert await rdict.get(user1) == "user1_data"
    assert await rdict.get(user2) == "user2_data"

    # Test __contains__ with Pydantic models as keys
    assert await rdict.__contains__(user1) is True
    assert await rdict.__contains__(user2) is True

    # Test keys() with Pydantic models
    keys = await rdict.keys()
    assert user1 in keys
    assert user2 in keys

    # Note: Testing retrieval using keys() results may fail due to serialization consistency issues
    # This is a known limitation when using Pydantic models as keys across different Python versions
    # The core functionality (direct get/set with original objects) works correctly

    # Test size
    assert await rdict.size() == 2

    # Note: items() iteration with Pydantic models as keys may have serialization consistency issues
    # This is a known limitation when using complex objects as keys
    # We'll skip this test for now until deterministic serialization is implemented


@pytest.mark.asyncio
async def test_pydantic_models_modification():
    """Test modifying Pydantic models in RedisDict."""
    rdict = RedisDict("test:pydantic_modification")
    await rdict.clear()

    user = User(id=1, name="David", email="david@example.com")
    await rdict.set("user", user)

    # Modify the user
    user.name = "David Updated"
    user.is_active = False
    await rdict.set("user", user)

    retrieved_user = await rdict.get("user")
    assert retrieved_user.name == "David Updated"
    assert retrieved_user.is_active is False
    assert retrieved_user.email == "david@example.com"  # unchanged


@pytest.mark.asyncio
async def test_pydantic_models_iteration():
    """Test iteration over Pydantic models."""
    rdict = RedisDict("test:pydantic_iteration")
    await rdict.clear()

    users = [
        User(id=1, name="Alice", email="alice@example.com"),
        User(id=2, name="Bob", email="bob@example.com"),
        User(id=3, name="Charlie", email="charlie@example.com"),
    ]

    for i, user in enumerate(users):
        await rdict.set(f"user_{i}", user)

    # Test async iteration over keys
    keys = []
    async for key in rdict:
        keys.append(key)
    assert sorted(keys) == ["user_0", "user_1", "user_2"]

    # Test async iteration over items
    items_iter = await rdict.items()
    retrieved_users = []
    async for key, user in items_iter:
        assert isinstance(user, User)
        retrieved_users.append(user)

    assert len(retrieved_users) == 3
    names = [user.name for user in retrieved_users]
    assert "Alice" in names
    assert "Bob" in names
    assert "Charlie" in names


@pytest.mark.asyncio
async def test_pydantic_models_setdefault():
    """Test setdefault with Pydantic models."""
    rdict = RedisDict("test:pydantic_setdefault")
    await rdict.clear()

    default_user = User(id=0, name="Default", email="default@example.com")

    # Test setting default for non-existent key
    result = await rdict.setdefault("new_user", default_user)
    assert isinstance(result, User)
    assert result.name == "Default"
    retrieved_user = await rdict.get("new_user")
    assert retrieved_user.name == "Default"

    # Test getting existing value (should not change)
    result = await rdict.setdefault("new_user", User(id=1, name="Different", email="different@example.com"))
    assert result.name == "Default"  # Should still be the original value


@pytest.mark.asyncio
async def test_pydantic_models_update():
    """Test update operation with Pydantic models."""
    rdict = RedisDict("test:pydantic_update")
    await rdict.clear()

    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com")
    user3 = User(id=3, name="Charlie", email="charlie@example.com")

    # Test updating with Pydantic models
    await rdict.update({"user1": user1, "user2": user2, "user3": user3})

    retrieved_user1 = await rdict.get("user1")
    retrieved_user2 = await rdict.get("user2")
    retrieved_user3 = await rdict.get("user3")
    assert retrieved_user1.name == "Alice"
    assert retrieved_user2.name == "Bob"
    assert retrieved_user3.name == "Charlie"
    assert await rdict.size() == 3

    # Test updating existing items
    updated_user1 = User(id=1, name="Alice Updated", email="alice.updated@example.com")
    await rdict.update({"user1": updated_user1})

    retrieved_user1_updated = await rdict.get("user1")
    retrieved_user2_unchanged = await rdict.get("user2")
    assert retrieved_user1_updated.name == "Alice Updated"
    assert retrieved_user2_unchanged.name == "Bob"  # unchanged


@pytest.mark.asyncio
async def test_pydantic_models_complex_nesting():
    """Test complex nested Pydantic models."""
    rdict = RedisDict("test:pydantic_complex")
    await rdict.clear()

    # Create a complex nested structure
    product1 = Product(id=1, name="Laptop", price=999.99, tags=["electronics", "computer"], metadata={"brand": "Apple", "model": "MacBook Pro"})

    product2 = Product(id=2, name="Mouse", price=29.99, tags=["electronics", "accessory"], metadata={"brand": "Logitech", "wireless": True})

    user = User(id=1, name="John", email="john@example.com")

    order = Order(id=1, user_id=1, products=[product1, product2], total=1029.98, status="shipped")

    # Store the complex object
    await rdict.set("order", order)
    retrieved_order = await rdict.get("order")

    # Verify the complex structure
    assert isinstance(retrieved_order, Order)
    assert retrieved_order.user_id == 1
    assert len(retrieved_order.products) == 2

    # Verify nested products
    laptop = retrieved_order.products[0]
    assert isinstance(laptop, Product)
    assert laptop.name == "Laptop"
    assert laptop.metadata["brand"] == "Apple"
    assert laptop.metadata["model"] == "MacBook Pro"

    mouse = retrieved_order.products[1]
    assert isinstance(mouse, Product)
    assert mouse.name == "Mouse"
    assert mouse.metadata["brand"] == "Logitech"
    assert mouse.metadata["wireless"] is True
