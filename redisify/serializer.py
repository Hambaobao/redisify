import json
import pickle
import base64
from datetime import datetime
from uuid import UUID
from typing import Any


class Serializer:

    def __init__(self, use_pickle_fallback: bool = True):
        self.use_pickle_fallback = use_pickle_fallback

    def serialize(self, obj: Any) -> str:
        try:
            return json.dumps(obj, default=self._default_json_encoder)
        except (TypeError, ValueError):
            if self.use_pickle_fallback:
                pickled = pickle.dumps(obj)
                b64 = base64.b64encode(pickled).decode("utf-8")
                return json.dumps({"__format__": "pickle", "data": b64})
            raise

    def deserialize(self, s: str) -> Any:
        try:
            obj = json.loads(s)
            if isinstance(obj, dict) and obj.get("__format__") == "pickle":
                b64 = obj["data"]
                return pickle.loads(base64.b64decode(b64))
            return obj
        except Exception as e:
            raise ValueError(f"Failed to deserialize: {e}")

    def _default_json_encoder(self, obj):
        if isinstance(obj, (datetime, UUID)):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if hasattr(obj, "model_dump"):  # Pydantic v2
            return obj.model_dump()
        if hasattr(obj, "dict"):  # Pydantic v1 fallback
            return obj.dict()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
