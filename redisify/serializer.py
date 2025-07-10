import dill
import base64
from typing import Any


class Serializer:
    """
    A universal Python object serializer using dill and base64 encoding.
    
    This class provides a simple and powerful serialization mechanism that can
    handle any Python object, including complex data structures, custom classes,
    functions, and even lambda expressions. The serializer uses dill for Python
    object serialization and base64 encoding for string representation.
    
    The serializer is designed to work seamlessly with Redis storage, providing
    a reliable way to store and retrieve complex Python objects in a distributed
    environment.
    
    Features:
        - Serializes any Python object including custom classes and functions
        - Uses base64 encoding for safe string storage in Redis
        - Preserves all type information and object relationships
        - Handles complex nested data structures
        - Thread-safe and process-safe serialization
    
    Attributes:
        None - This is a stateless serializer class
    """

    def __init__(self):
        """
        Initialize the serializer.
        
        This constructor creates a new serializer instance. No parameters
        are required as the serializer uses dill which handles all Python
        objects automatically.
        
        Note:
            The serializer is stateless and can be safely shared across
            multiple threads or processes.
        """
        pass

    def serialize(self, obj: Any) -> str:
        """
        Serialize any Python object to a base64-encoded string.
        
        This method takes any Python object and converts it to a string
        representation suitable for storage in Redis or other string-based
        storage systems. The serialization process uses dill to preserve
        all object information including type, relationships, and custom
        attributes.
        
        The resulting string is base64-encoded to ensure safe storage
        and transmission without encoding issues.
        
        Args:
            obj: Any Python object to serialize. This can include:
                - Basic types (int, float, str, bool, None)
                - Complex types (list, dict, tuple, set)
                - Custom classes and objects
                - Functions and lambda expressions
                - Nested data structures
                - Objects with circular references (handled by dill)
            
        Returns:
            A base64-encoded string representation of the object that can
            be safely stored in Redis or transmitted over the network.
            
        Raises:
            TypeError: If the object cannot be serialized by dill, typically
                due to C extensions, file handles, or other non-serializable
                objects.
                
        Example:
            >>> serializer = Serializer()
            >>> data = {"name": "Alice", "age": 30, "hobbies": ["reading", "swimming"]}
            >>> serialized = serializer.serialize(data)
            >>> print(type(serialized))  # <class 'str'>
        """
        try:
            pickled = dill.dumps(obj)
            return base64.b64encode(pickled).decode('utf-8')
        except Exception as e:
            raise TypeError(f"Serialization failed: {e}")

    def deserialize(self, s: str) -> Any:
        """
        Deserialize a base64-encoded string back to the original Python object.
        
        This method reverses the serialization process, converting a string
        representation back to the original Python object with all its
        properties, type information, and relationships intact.
        
        The deserialization process handles the base64 decoding and dill
        unpickling to restore the original object exactly as it was serialized.
        
        Args:
            s: A base64-encoded string that was previously created by the
                serialize() method. The string should contain a valid
                serialized Python object.
            
        Returns:
            The original Python object with all its properties, type information,
            and relationships preserved exactly as they were before serialization.
            
        Raises:
            ValueError: If the string cannot be deserialized, typically due to:
                - Invalid base64 encoding
                - Corrupted serialized data
                - Incompatible dill version
                - Malformed or incomplete serialized data
                
        Example:
            >>> serializer = Serializer()
            >>> original_data = {"name": "Alice", "age": 30}
            >>> serialized = serializer.serialize(original_data)
            >>> deserialized = serializer.deserialize(serialized)
            >>> print(deserialized == original_data)  # True
            >>> print(type(deserialized))  # <class 'dict'>
        """
        try:
            pickled = base64.b64decode(s.encode('utf-8'))
            return dill.loads(pickled)
        except Exception as e:
            raise ValueError(f"Deserialization failed: {e}")
