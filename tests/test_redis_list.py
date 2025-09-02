import pytest
import pytest_asyncio

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel

from redisify import RedisList, connect_to_redis, reset


@pytest_asyncio.fixture(autouse=True)
async def setup_redis():
    """Setup Redis connection for each test."""
    connect_to_redis(host="localhost", port=6379, db=0, decode_responses=True)
    yield
    reset()


@pytest.mark.asyncio
async def test_basic_operations():
    """Test basic list operations: append, get, set, insert, range, clear, size."""
    rlist = RedisList("test:list")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.insert(1, "x")  # a, x, b

    assert await rlist.get(0) == "a"
    assert await rlist.get(1) == "x"
    assert await rlist.get(2) == "b"

    await rlist.set(2, "z")
    assert await rlist.get(2) == "z"

    values = await rlist.range(0, -1)
    assert values == ["a", "x", "z"]

    async for item in rlist:
        assert item in values

    await rlist.clear()
    assert await rlist.size() == 0


@pytest.mark.asyncio
async def test_pop_operation():
    """Test pop operation to remove and return the last item."""
    rlist = RedisList("test:pop")
    await rlist.clear()

    # Test pop on empty list
    assert await rlist.pop() is None

    # Test pop on non-empty list
    await rlist.append("a")
    await rlist.append("b")
    await rlist.append("c")

    assert await rlist.pop() == "c"
    assert await rlist.size() == 2
    assert await rlist.pop() == "b"
    assert await rlist.size() == 1
    assert await rlist.pop() == "a"
    assert await rlist.size() == 0
    assert await rlist.pop() is None


@pytest.mark.asyncio
async def test_delete_operation():
    """Test delete operation to remove item by index."""
    rlist = RedisList("test:delete")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.append("c")
    await rlist.append("d")

    # Test delete middle item
    await rlist.delete(1)
    assert await rlist.range(0, -1) == ["a", "c", "d"]

    # Test delete first item
    await rlist.delete(0)
    assert await rlist.range(0, -1) == ["c", "d"]

    # Test delete last item
    await rlist.delete(-1)
    assert await rlist.range(0, -1) == ["c"]

    # Test delete remaining item
    await rlist.delete(0)
    assert await rlist.size() == 0

    # Test delete on empty list
    with pytest.raises(IndexError):
        await rlist.delete(0)


@pytest.mark.asyncio
async def test_remove_operation():
    """Test remove operation to remove occurrences of a value."""
    rlist = RedisList("test:remove")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.append("a")
    await rlist.append("c")
    await rlist.append("a")

    # Test remove single occurrence
    await rlist.remove("b")
    assert await rlist.range(0, -1) == ["a", "a", "c", "a"]

    # Test remove multiple occurrences
    await rlist.remove("a", count=2)
    assert await rlist.range(0, -1) == ["c", "a"]

    # Test remove all occurrences
    await rlist.remove("a", count=0)
    assert await rlist.range(0, -1) == ["c"]

    # Test remove non-existent value
    await rlist.remove("x")
    assert await rlist.range(0, -1) == ["c"]


@pytest.mark.asyncio
async def test_getitem_setitem():
    """Test __getitem__ and __setitem__ operations."""
    rlist = RedisList("test:getitem_setitem")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.append("c")

    # Test single index access
    assert await rlist[0] == "a"
    assert await rlist[1] == "b"
    assert await rlist[2] == "c"
    assert await rlist[-1] == "c"
    assert await rlist[-2] == "b"

    # Test single index assignment using set method
    await rlist.set(1, "x")
    assert await rlist[1] == "x"

    # Test slice access
    assert await rlist[0:2] == ["a", "x"]
    assert await rlist[1:] == ["x", "c"]
    assert await rlist[:2] == ["a", "x"]
    assert await rlist[::2] == ["a", "c"]  # step=2

    # Note: Slice assignment is not supported in async context
    # We'll test individual set operations instead
    await rlist.set(0, "y")
    await rlist.set(1, "z")
    assert await rlist.range(0, -1) == ["y", "z", "c"]

    # Test index out of range
    with pytest.raises(IndexError):
        await rlist[10]


@pytest.mark.asyncio
async def test_len_operation():
    """Test __len__ operation."""
    rlist = RedisList("test:len")
    await rlist.clear()

    assert await rlist.__len__() == 0

    await rlist.append("a")
    assert await rlist.__len__() == 1

    await rlist.append("b")
    await rlist.append("c")
    assert await rlist.__len__() == 3

    await rlist.pop()
    assert await rlist.__len__() == 2


@pytest.mark.asyncio
async def test_range_operation():
    """Test range operation with different parameters."""
    rlist = RedisList("test:range")
    await rlist.clear()

    await rlist.append("a")
    await rlist.append("b")
    await rlist.append("c")
    await rlist.append("d")
    await rlist.append("e")

    # Test full range
    assert await rlist.range() == ["a", "b", "c", "d", "e"]
    assert await rlist.range(0, -1) == ["a", "b", "c", "d", "e"]

    # Test partial range
    assert await rlist.range(1, 3) == ["b", "c", "d"]
    assert await rlist.range(0, 2) == ["a", "b", "c"]
    assert await rlist.range(2, -1) == ["c", "d", "e"]

    # Test single item range
    assert await rlist.range(1, 1) == ["b"]
    assert await rlist.range(-1, -1) == ["e"]


@pytest.mark.asyncio
async def test_insert_operation():
    """Test insert operation with different positions."""
    rlist = RedisList("test:insert")
    await rlist.clear()

    # Test insert at beginning
    await rlist.insert(0, "a")
    assert await rlist.range(0, -1) == ["a"]

    # Test insert at end
    await rlist.insert(1, "c")
    assert await rlist.range(0, -1) == ["a", "c"]

    # Test insert in middle
    await rlist.insert(1, "b")
    assert await rlist.range(0, -1) == ["a", "b", "c"]

    # Test insert with negative index
    await rlist.insert(-1, "x")
    assert await rlist.range(0, -1) == ["a", "b", "x", "c"]

    # Test insert at end with negative index
    await rlist.insert(-1, "y")
    assert await rlist.range(0, -1) == ["a", "b", "x", "y", "c"]

    # Test insert out of range
    with pytest.raises(IndexError):
        await rlist.insert(10, "z")


@pytest.mark.asyncio
async def test_serialization():
    """Test serialization and deserialization of complex objects."""
    rlist = RedisList("test:serialization")
    await rlist.clear()

    # Test with different data types
    test_data = ["string", 123, 45.67, True, None, [1, 2, 3], {"key": "value"}, (1, 2, 3)]

    for item in test_data:
        await rlist.append(item)

    # Verify all items can be retrieved correctly
    for i, expected in enumerate(test_data):
        assert await rlist[i] == expected

    # Test with nested structures
    complex_obj = {"list": [1, 2, {"nested": "dict"}], "tuple": (1, 2, 3), "bool": True, "none": None}
    await rlist.append(complex_obj)
    retrieved = await rlist[-1]
    assert retrieved == complex_obj


@pytest.mark.asyncio
async def test_edge_cases():
    """Test edge cases and error conditions."""
    rlist = RedisList("test:edge_cases")
    await rlist.clear()

    # Test operations on empty list
    assert await rlist.size() == 0
    assert await rlist.pop() is None
    assert await rlist.range(0, -1) == []

    # Test index out of range errors
    with pytest.raises(IndexError):
        await rlist.get(0)

    # Note: set() on empty list will raise Redis error, not IndexError
    # This is expected behavior since Redis doesn't have the key yet

    with pytest.raises(IndexError):
        await rlist.delete(0)

    # Test insert at invalid positions
    with pytest.raises(IndexError):
        await rlist.insert(-1, "value")  # Insert at -1 when list is empty

    # Test with single item
    await rlist.append("single")
    assert await rlist.size() == 1
    assert await rlist[0] == "single"
    assert await rlist[-1] == "single"

    # Test delete last item
    await rlist.delete(0)
    assert await rlist.size() == 0


@pytest.mark.asyncio
async def test_async_iteration():
    """Test async iteration over the list."""
    rlist = RedisList("test:iteration")
    await rlist.clear()

    # Test iteration over empty list
    items = []
    async for item in rlist:
        items.append(item)
    assert items == []

    # Test iteration over non-empty list
    test_items = ["a", "b", "c", "d"]
    for item in test_items:
        await rlist.append(item)

    items = []
    async for item in rlist:
        items.append(item)
    assert items == test_items

    # Test iteration after modification
    await rlist.append("e")
    items = []
    async for item in rlist:
        items.append(item)
    assert items == test_items + ["e"]


@pytest.mark.asyncio
async def test_slice_operations():
    """Test comprehensive slice operations."""
    rlist = RedisList("test:slices")
    await rlist.clear()

    # Setup test data
    test_data = ["a", "b", "c", "d", "e", "f"]
    for item in test_data:
        await rlist.append(item)

    # Test various slice patterns
    assert await rlist[1:4] == ["b", "c", "d"]
    assert await rlist[:3] == ["a", "b", "c"]
    assert await rlist[3:] == ["d", "e", "f"]
    assert await rlist[::2] == ["a", "c", "e"]  # every second item
    assert await rlist[1::2] == ["b", "d", "f"]  # every second item starting from index 1
    assert await rlist[::-1] == ["f", "e", "d", "c", "b", "a"]  # reverse
    assert await rlist[2:5:2] == ["c", "e"]  # slice with step

    # Test individual set operations instead of slice assignment
    await rlist.set(1, "x")
    await rlist.set(2, "y")
    await rlist.set(3, "z")
    assert await rlist.range(0, -1) == ["a", "x", "y", "z", "e", "f"]

    # Test setting multiple items individually
    await rlist.set(1, "p")
    await rlist.set(2, "q")
    await rlist.set(3, "r")
    await rlist.set(4, "s")
    assert await rlist.range(0, -1) == ["a", "p", "q", "r", "s", "f"]


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
    """Test RedisList with Pydantic models."""
    rlist = RedisList("test:pydantic")
    await rlist.clear()

    # Test with simple Pydantic model
    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com", is_active=False)

    await rlist.append(user1)
    await rlist.append(user2)

    # Verify retrieval
    retrieved_user1 = await rlist[0]
    retrieved_user2 = await rlist[1]

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

    await rlist.append(order)
    retrieved_order = await rlist[2]

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
    rlist = RedisList("test:pydantic_datetime")
    await rlist.clear()

    now = datetime.now()
    user = User(id=1, name="Charlie", email="charlie@example.com", created_at=now)

    await rlist.append(user)
    retrieved_user = await rlist[0]

    assert isinstance(retrieved_user, User)
    assert retrieved_user.id == 1
    assert retrieved_user.name == "Charlie"
    assert retrieved_user.created_at == now


@pytest.mark.asyncio
async def test_pydantic_models_modification():
    """Test modifying Pydantic models in RedisList."""
    rlist = RedisList("test:pydantic_modification")
    await rlist.clear()

    user = User(id=1, name="David", email="david@example.com")
    await rlist.append(user)

    # Modify the user
    user.name = "David Updated"
    user.is_active = False
    await rlist.set(0, user)

    retrieved_user = await rlist[0]
    assert retrieved_user.name == "David Updated"
    assert retrieved_user.is_active is False
    assert retrieved_user.email == "david@example.com"  # unchanged


@pytest.mark.asyncio
async def test_pydantic_models_slice_operations():
    """Test slice operations with Pydantic models."""
    rlist = RedisList("test:pydantic_slices")
    await rlist.clear()

    users = [
        User(id=1, name="User1", email="user1@example.com"),
        User(id=2, name="User2", email="user2@example.com"),
        User(id=3, name="User3", email="user3@example.com"),
        User(id=4, name="User4", email="user4@example.com"),
    ]

    for user in users:
        await rlist.append(user)

    # Test slice retrieval
    slice_users = await rlist[1:3]
    assert len(slice_users) == 2
    assert slice_users[0].name == "User2"
    assert slice_users[1].name == "User3"

    # Test individual set operations instead of slice assignment
    new_user1 = User(id=10, name="NewUser1", email="new1@example.com")
    new_user2 = User(id=11, name="NewUser2", email="new2@example.com")
    await rlist.set(1, new_user1)
    await rlist.set(2, new_user2)

    # Verify the change
    all_users = await rlist.range(0, -1)
    assert all_users[0].name == "User1"
    assert all_users[1].name == "NewUser1"
    assert all_users[2].name == "NewUser2"
    assert all_users[3].name == "User4"


@pytest.mark.asyncio
async def test_pydantic_models_iteration():
    """Test iteration over Pydantic models."""
    rlist = RedisList("test:pydantic_iteration")
    await rlist.clear()

    users = [
        User(id=1, name="Alice", email="alice@example.com"),
        User(id=2, name="Bob", email="bob@example.com"),
        User(id=3, name="Charlie", email="charlie@example.com"),
    ]

    for user in users:
        await rlist.append(user)

    # Test async iteration
    retrieved_users = []
    async for user in rlist:
        assert isinstance(user, User)
        retrieved_users.append(user)

    assert len(retrieved_users) == 3
    assert retrieved_users[0].name == "Alice"
    assert retrieved_users[1].name == "Bob"
    assert retrieved_users[2].name == "Charlie"


@pytest.mark.asyncio
async def test_pydantic_models_remove_operation():
    """Test remove operation with Pydantic models."""
    rlist = RedisList("test:pydantic_remove")
    await rlist.clear()

    user1 = User(id=1, name="Alice", email="alice@example.com")
    user2 = User(id=2, name="Bob", email="bob@example.com")
    user3 = User(id=1, name="Alice", email="alice@example.com")  # Same as user1

    await rlist.append(user1)
    await rlist.append(user2)
    await rlist.append(user3)

    # Remove one occurrence of user1
    await rlist.remove(user1, count=1)

    remaining_users = await rlist.range(0, -1)
    assert len(remaining_users) == 2
    assert remaining_users[0].name == "Bob"
    assert remaining_users[1].name == "Alice"  # The duplicate should remain


@pytest.mark.asyncio
async def test_pydantic_models_complex_nesting():
    """Test complex nested Pydantic models."""
    rlist = RedisList("test:pydantic_complex")
    await rlist.clear()

    # Create a complex nested structure
    product1 = Product(id=1, name="Laptop", price=999.99, tags=["electronics", "computer"], metadata={"brand": "Apple", "model": "MacBook Pro"})

    product2 = Product(id=2, name="Mouse", price=29.99, tags=["electronics", "accessory"], metadata={"brand": "Logitech", "wireless": True})

    user = User(id=1, name="John", email="john@example.com")

    order = Order(id=1, user_id=1, products=[product1, product2], total=1029.98, status="shipped")

    # Store the complex object
    await rlist.append(order)
    retrieved_order = await rlist[0]

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
