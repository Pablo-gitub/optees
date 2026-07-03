from __future__ import annotations

import json
from dataclasses import dataclass
from math import isfinite, isinf
from pathlib import Path
from typing import Iterable, Optional, Tuple


KNAPSACK_JSON_VERSION = "1"

VARIANT_ZERO_ONE = "zero_one"
VARIANT_BOUNDED = "bounded"
VARIANT_UNBOUNDED = "unbounded"
VARIANT_FRACTIONAL = "fractional"
VARIANT_MULTI_DIMENSIONAL = "multi_dimensional"

DOMAIN_ZERO_ONE = "zero_one"
DOMAIN_BOUNDED = "bounded"
DOMAIN_UNBOUNDED = "unbounded"
DOMAIN_FRACTIONAL = "fractional"


@dataclass(frozen=True)
class KnapsackJsonResource:
    name: str
    capacity: float


@dataclass(frozen=True)
class KnapsackJsonItem:
    name: str
    value: float
    weight: Optional[float] = None
    max_quantity: Optional[float] = None
    usage: Tuple[float, ...] = ()


@dataclass(frozen=True)
class KnapsackJsonProblem:
    version: str
    variant: str
    domain: str
    capacity: Optional[float]
    items: Tuple[KnapsackJsonItem, ...]
    resources: Tuple[KnapsackJsonResource, ...] = ()

    def is_multi_dimensional(self) -> bool:
        return self.variant == VARIANT_MULTI_DIMENSIONAL


def knapsack_problem_from_file(path: str | Path) -> KnapsackJsonProblem:
    return knapsack_problem_from_dict(
        json.loads(Path(path).read_text(encoding="utf-8"))
    )


def knapsack_problem_to_file(problem: KnapsackJsonProblem, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(knapsack_problem_to_dict(problem), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def knapsack_problem_from_dict(data: dict) -> KnapsackJsonProblem:
    if not isinstance(data, dict):
        raise ValueError("knapsack JSON root must be an object")

    version = str(data.get("version", KNAPSACK_JSON_VERSION))
    if version != KNAPSACK_JSON_VERSION:
        raise ValueError(f"unsupported knapsack JSON version: {version!r}")

    problem_type = str(data.get("problem_type", "knapsack")).strip().lower()
    if problem_type not in {"knapsack", "zaino"}:
        raise ValueError("problem_type must be 'knapsack'")

    variant = _normalize_variant(data.get("variant", VARIANT_ZERO_ONE))
    domain = _normalize_domain(data.get("domain"), variant)

    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("items must be a non-empty array")

    if variant == VARIANT_MULTI_DIMENSIONAL:
        resources = _parse_resources(data.get("resources"))
        items = _parse_multi_items(raw_items, len(resources), domain)
        return KnapsackJsonProblem(
            version=version,
            variant=variant,
            domain=domain,
            capacity=None,
            items=items,
            resources=resources,
        )

    capacity = _normalize_number(data.get("capacity"), "capacity")
    if domain in (DOMAIN_ZERO_ONE, DOMAIN_BOUNDED, DOMAIN_UNBOUNDED):
        capacity = float(_normalize_non_negative_int(capacity, "capacity"))
    items = _parse_single_resource_items(raw_items, domain)
    return KnapsackJsonProblem(
        version=version,
        variant=variant,
        domain=domain,
        capacity=capacity,
        items=items,
    )


def knapsack_problem_to_dict(problem: KnapsackJsonProblem) -> dict:
    data: dict = {
        "version": problem.version,
        "problem_type": "knapsack",
        "variant": problem.variant,
        "items": [],
    }
    if problem.is_multi_dimensional():
        data["domain"] = problem.domain
        data["resources"] = [
            {"name": resource.name, "capacity": resource.capacity}
            for resource in problem.resources
        ]
        data["items"] = [
            _drop_none(
                {
                    "name": item.name,
                    "value": item.value,
                    "usage": list(item.usage),
                    "max_quantity": _serialize_optional_number(item.max_quantity),
                }
            )
            for item in problem.items
        ]
    else:
        data["capacity"] = problem.capacity
        data["items"] = [
            _drop_none(
                {
                    "name": item.name,
                    "value": item.value,
                    "weight": item.weight,
                    "max_quantity": _serialize_optional_number(item.max_quantity),
                }
            )
            for item in problem.items
        ]
    return data


def _parse_resources(value: object) -> Tuple[KnapsackJsonResource, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("resources must be a non-empty array")
    resources = []
    used_names = set()
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"resources[{index}] must be an object")
        name = _normalize_name(raw.get("name"), f"Resource {index + 1}")
        key = name.casefold()
        if key in used_names:
            raise ValueError("resource names must be unique")
        used_names.add(key)
        resources.append(
            KnapsackJsonResource(
                name=name,
                capacity=_normalize_number(raw.get("capacity"), f"resources[{index}].capacity"),
            )
        )
    return tuple(resources)


def _parse_single_resource_items(
    raw_items: list,
    domain: str,
) -> Tuple[KnapsackJsonItem, ...]:
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        weight = _normalize_number(raw.get("weight"), f"items[{index}].weight")
        if domain in (DOMAIN_ZERO_ONE, DOMAIN_BOUNDED, DOMAIN_UNBOUNDED):
            weight = float(_normalize_non_negative_int(weight, f"items[{index}].weight"))
        elif weight <= 0:
            raise ValueError(f"items[{index}].weight must be positive")
        items.append(
            KnapsackJsonItem(
                name=_normalize_name(raw.get("name"), f"Item {index + 1}"),
                value=_normalize_number(raw.get("value"), f"items[{index}].value"),
                weight=weight,
                max_quantity=_parse_max_quantity(raw.get("max_quantity"), domain),
            )
        )
    return tuple(items)


def _parse_multi_items(
    raw_items: list,
    resource_count: int,
    domain: str,
) -> Tuple[KnapsackJsonItem, ...]:
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        usage = raw.get("usage")
        if not isinstance(usage, list) or len(usage) != resource_count:
            raise ValueError(
                f"items[{index}].usage must contain {resource_count} values"
            )
        items.append(
            KnapsackJsonItem(
                name=_normalize_name(raw.get("name"), f"Item {index + 1}"),
                value=_normalize_number(raw.get("value"), f"items[{index}].value"),
                max_quantity=_parse_max_quantity(raw.get("max_quantity"), domain),
                usage=tuple(
                    _normalize_number(amount, f"items[{index}].usage[{j}]")
                    for j, amount in enumerate(usage)
                ),
            )
        )
    return tuple(items)


def _normalize_variant(value: object) -> str:
    token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "0/1": VARIANT_ZERO_ONE,
        "01": VARIANT_ZERO_ONE,
        "zero_one": VARIANT_ZERO_ONE,
        "binary": VARIANT_ZERO_ONE,
        "bounded": VARIANT_BOUNDED,
        "unbounded": VARIANT_UNBOUNDED,
        "fractional": VARIANT_FRACTIONAL,
        "multi": VARIANT_MULTI_DIMENSIONAL,
        "multi_dimensional": VARIANT_MULTI_DIMENSIONAL,
        "multidimensional": VARIANT_MULTI_DIMENSIONAL,
    }
    try:
        return aliases[token]
    except KeyError as exc:
        raise ValueError(f"unsupported knapsack variant: {value!r}") from exc


def _normalize_domain(value: object, variant: str) -> str:
    if variant != VARIANT_MULTI_DIMENSIONAL:
        return {
            VARIANT_ZERO_ONE: DOMAIN_ZERO_ONE,
            VARIANT_BOUNDED: DOMAIN_BOUNDED,
            VARIANT_UNBOUNDED: DOMAIN_UNBOUNDED,
            VARIANT_FRACTIONAL: DOMAIN_FRACTIONAL,
        }[variant]

    token = str(value or DOMAIN_ZERO_ONE).strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "0/1": DOMAIN_ZERO_ONE,
        "01": DOMAIN_ZERO_ONE,
        "zero_one": DOMAIN_ZERO_ONE,
        "binary": DOMAIN_ZERO_ONE,
        "bounded": DOMAIN_BOUNDED,
        "bounded_integer": DOMAIN_BOUNDED,
        "unbounded": DOMAIN_UNBOUNDED,
        "unbounded_integer": DOMAIN_UNBOUNDED,
        "fractional": DOMAIN_FRACTIONAL,
        "continuous": DOMAIN_FRACTIONAL,
    }
    try:
        return aliases[token]
    except KeyError as exc:
        raise ValueError(f"unsupported multi-dimensional domain: {value!r}") from exc


def _normalize_name(value: object, default: str) -> str:
    text = str(value or "").strip()
    return text or default


def _normalize_number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite non-negative number")
    try:
        normalized = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite non-negative number") from exc
    if not isfinite(normalized) or normalized < 0:
        raise ValueError(f"{label} must be a finite non-negative number")
    return normalized


def _normalize_non_negative_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a non-negative integer")
    parsed = float(value)  # type: ignore[arg-type]
    if not parsed.is_integer() or parsed < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return int(parsed)


def _parse_max_quantity(value: object, domain: str) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, str) and value.strip().lower() in {
        "inf",
        "+inf",
        "infinity",
        "+infinity",
    }:
        if domain == DOMAIN_BOUNDED:
            raise ValueError("max_quantity must be finite for bounded knapsack")
        return float("inf")
    parsed = _normalize_number(value, "max_quantity")
    if domain in (DOMAIN_BOUNDED, DOMAIN_UNBOUNDED):
        return float(_normalize_non_negative_int(parsed, "max_quantity"))
    return parsed


def _serialize_optional_number(value: Optional[float]) -> Optional[float | str]:
    if value is None:
        return None
    if isinf(value):
        return "inf"
    return value


def _drop_none(data: dict) -> dict:
    return {key: value for key, value in data.items() if value is not None}
