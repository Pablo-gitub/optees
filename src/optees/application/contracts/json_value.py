from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import TypeAlias


JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


def require_json_value(value: object, *, path: str = "$") -> JsonValue:
    """Validate a public payload without silently coercing unsupported values."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number.")
        return value
    if isinstance(value, list):
        return [
            require_json_value(item, path=f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string object key.")
            result[key] = require_json_value(item, path=f"{path}.{key}")
        return result
    raise ValueError(f"{path} contains unsupported type {type(value).__name__}.")


def dumps_json(value: object, *, indent: int | None = None) -> str:
    normalized = require_json_value(value)
    return json.dumps(
        normalized,
        allow_nan=False,
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )
