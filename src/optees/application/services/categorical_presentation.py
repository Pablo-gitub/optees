from __future__ import annotations

from dataclasses import dataclass
from typing import TypeVar


T = TypeVar("T")

DEFAULT_CATEGORY_WINDOW = 40
MAX_CATEGORY_WINDOW = 200


@dataclass(frozen=True)
class CategoryWindow:
    total: int
    displayed: int

    @property
    def truncated(self) -> bool:
        return self.displayed < self.total


def bounded_categories(
    values: list[T],
    *,
    limit: int = DEFAULT_CATEGORY_WINDOW,
) -> tuple[list[T], CategoryWindow]:
    """Return the deterministic leading window used by desktop and artifacts."""

    if isinstance(limit, bool) or not isinstance(limit, int):
        raise ValueError("category limit must be an integer")
    if limit < 1 or limit > MAX_CATEGORY_WINDOW:
        raise ValueError(
            f"category limit must be between 1 and {MAX_CATEGORY_WINDOW}"
        )
    displayed = min(len(values), limit)
    return values[:displayed], CategoryWindow(len(values), displayed)
