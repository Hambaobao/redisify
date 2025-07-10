import dill
import base64
from typing import Any


class Serializer:
    """Simple and universal serializer using dill for all Python objects"""

    def __init__(self):
        """Initialize the serializer (no parameters needed with dill)"""
        pass

    def serialize(self, obj: Any) -> str:
        """
        Serialize any Python object to a string using dill
        
        Args:
            obj: Any Python object to serialize
            
        Returns:
            Base64 encoded string representation of the object
            
        Raises:
            TypeError: If serialization fails
        """
        try:
            pickled = dill.dumps(obj)
            return base64.b64encode(pickled).decode('utf-8')
        except Exception as e:
            raise TypeError(f"Serialization failed: {e}")

    def deserialize(self, s: str) -> Any:
        """
        Deserialize a string back to the original Python object using dill
        
        Args:
            s: Base64 encoded string from serialize()
            
        Returns:
            The original Python object with all its type information preserved
            
        Raises:
            ValueError: If deserialization fails
        """
        try:
            pickled = base64.b64decode(s.encode('utf-8'))
            return dill.loads(pickled)
        except Exception as e:
            raise ValueError(f"Deserialization failed: {e}")
