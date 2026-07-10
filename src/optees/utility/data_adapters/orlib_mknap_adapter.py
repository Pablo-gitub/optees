"""Reader for OR-Library ``mknap`` multi-dimensional knapsack instances.

The OR-Library ``mknap`` files store several 0/1 multi-dimensional knapsack
instances.  Each instance provides the known optimum, item profits, one
resource-usage vector per constraint, and the corresponding capacities.

The reader intentionally returns a plain canonical dictionary.  This keeps the
external file format at the infrastructure boundary and lets callers construct
the domain model appropriate to their use case.
"""

from __future__ import annotations

from math import isfinite
from pathlib import Path
from typing import Any


__all__ = ["load_orlib_mknap"]


_SOURCE_URL = "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html"


def load_orlib_mknap(path: str | Path, instance_index: int) -> dict[str, Any]:
    """Load one 1-based instance from an OR-Library ``mknap`` file.

    The format is token based, so line wrapping is irrelevant:

    ``number_of_instances`` followed by, for every instance,
    ``n m known_optimum``, ``n`` profits, ``m * n`` resource consumptions,
    and ``m`` capacities.

    Resource consumptions in the source are constraint-major.  Optees uses an
    item-major matrix, therefore ``usage_matrix[item][resource]`` is returned.
    """
    index = _require_positive_int(instance_index, "instance_index")
    tokens = _numeric_tokens(path)
    cursor = 0

    instance_count, cursor = _read_int(tokens, cursor, "instance count")
    if index > instance_count:
        raise ValueError(
            f"instance_index {index} is outside the file range 1..{instance_count}"
        )

    selected: dict[str, Any] | None = None
    for current_index in range(1, instance_count + 1):
        item_count, cursor = _read_int(tokens, cursor, "item count")
        resource_count, cursor = _read_int(tokens, cursor, "resource count")
        optimum, cursor = _read_float(tokens, cursor, "known optimum")
        if item_count < 0 or resource_count <= 0:
            raise ValueError("OR-Library mknap dimensions must be non-negative")

        values, cursor = _read_float_vector(tokens, cursor, item_count, "profits")
        resource_major: list[list[float]] = []
        for resource_index in range(resource_count):
            usage, cursor = _read_float_vector(
                tokens,
                cursor,
                item_count,
                f"resource {resource_index + 1} usage",
            )
            resource_major.append(usage)
        capacities, cursor = _read_float_vector(
            tokens,
            cursor,
            resource_count,
            "capacities",
        )

        if current_index == index:
            selected = {
                "values": values,
                "usage_matrix": [
                    [resource_major[resource][item] for resource in range(resource_count)]
                    for item in range(item_count)
                ],
                "capacities": capacities,
                "known_optimum": optimum,
                "metadata": {
                    "source": "OR-Library",
                    "dataset": Path(path).stem,
                    "instance_index": current_index,
                    "source_url": _SOURCE_URL,
                    "item_count": item_count,
                    "resource_count": resource_count,
                },
            }

    if cursor != len(tokens):
        raise ValueError("unexpected trailing data in OR-Library mknap file")
    if selected is None:
        raise ValueError(f"instance_index {index} was not found")
    return selected


def _numeric_tokens(path: str | Path) -> list[str]:
    try:
        content = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"cannot read OR-Library mknap file: {path}") from exc

    tokens = content.split()
    if not tokens:
        raise ValueError("OR-Library mknap file is empty")
    return tokens


def _read_int(tokens: list[str], cursor: int, label: str) -> tuple[int, int]:
    value, next_cursor = _read_float(tokens, cursor, label)
    if not value.is_integer():
        raise ValueError(f"{label} must be an integer")
    return int(value), next_cursor


def _read_float(tokens: list[str], cursor: int, label: str) -> tuple[float, int]:
    if cursor >= len(tokens):
        raise ValueError(f"missing {label} in OR-Library mknap file")
    try:
        value = float(tokens[cursor])
    except ValueError as exc:
        raise ValueError(f"invalid {label} in OR-Library mknap file") from exc
    if not isfinite(value):
        raise ValueError(f"invalid {label} in OR-Library mknap file")
    return value, cursor + 1


def _read_float_vector(
    tokens: list[str],
    cursor: int,
    length: int,
    label: str,
) -> tuple[list[float], int]:
    values: list[float] = []
    for _ in range(length):
        value, cursor = _read_float(tokens, cursor, label)
        values.append(value)
    return values, cursor


def _require_positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value
