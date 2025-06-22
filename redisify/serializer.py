import json
import pickle
import base64
import importlib
from datetime import datetime
from uuid import UUID
from typing import Any


class Serializer:

    def __init__(self, use_pickle_fallback: bool = True):
        self.use_pickle_fallback = use_pickle_fallback

    def serialize(self, obj: Any) -> str:
        try:
            # Detect Pydantic v2 or v1
            if hasattr(obj, "model_dump"):
                return json.dumps({
                    "__pydantic_model__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                    "data": obj.model_dump(),
                })
            elif hasattr(obj, "dict"):
                return json.dumps({
                    "__pydantic_model__": f"{obj.__class__.__module__}.{obj.__class__.__name__}",
                    "data": obj.dict(),
                })

            return json.dumps(obj, default=self._default_json_encoder)
        except (TypeError, ValueError):
            if self.use_pickle_fallback:
                try:
                    pickled = pickle.dumps(obj)
                    b64 = base64.b64encode(pickled).decode("utf-8")
                    return json.dumps({"__format__": "pickle", "data": b64})
                except Exception as e:
                    raise TypeError(f"Pickle fallback failed: {e}")
            raise

    def deserialize(self, s: str) -> Any:
        try:
            obj = json.loads(s)

            if isinstance(obj, dict):
                # Pydantic model auto-import
                if "__pydantic_model__" in obj and "data" in obj:
                    module_path, class_name = obj["__pydantic_model__"].rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    cls = getattr(module, class_name)
                    return cls(**obj["data"])

                # Pickle fallback
                if obj.get("__format__") == "pickle":
                    return pickle.loads(base64.b64decode(obj["data"]))

            return obj
        except Exception as e:
            raise ValueError(f"Failed to deserialize: {e}")

    def _default_json_encoder(self, obj):
        if isinstance(obj, (datetime, UUID)):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
