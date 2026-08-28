"""Deeply immutable mapping helpers for domain results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FrozenDict(dict):
    """A dict-compatible snapshot that rejects in-place mutation."""

    def _immutable(self, *args: object, **kwargs: object) -> None:
        raise TypeError("frozen mapping cannot be mutated")

    __setitem__ = _immutable
    __delitem__ = _immutable
    clear = _immutable
    pop = _immutable
    popitem = _immutable
    setdefault = _immutable
    update = _immutable
    __ior__ = _immutable


def freeze_mapping(value: Mapping[str, Any]) -> FrozenDict:
    def freeze(item: Any) -> Any:
        if isinstance(item, Mapping):
            return FrozenDict({str(key): freeze(child) for key, child in item.items()})
        if isinstance(item, (list, tuple)):
            return tuple(freeze(child) for child in item)
        return item

    return freeze(value)
