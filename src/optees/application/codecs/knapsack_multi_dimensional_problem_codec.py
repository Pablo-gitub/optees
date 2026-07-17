from __future__ import annotations

from math import isinf

from optees.application.contracts.json_value import JsonValue
from optees.application.dtos.multi_dimensional_knapsack_dtos import (
    MultiDimensionalKnapsackRequest,
)
from optees.domain.entities.knapsack.multi_dimensional_item import (
    MultiDimensionalKnapsackItem,
)
from optees.domain.entities.knapsack.multi_dimensional_resource import (
    MultiDimensionalKnapsackResource,
)
from optees.domain.models.knapsack.multi_dimensional_knapsack_model import (
    MultiDimensionalKnapsackModel,
)
from optees.utility.knapsack_json_io import (
    DOMAIN_BOUNDED,
    DOMAIN_FRACTIONAL,
    DOMAIN_UNBOUNDED,
    DOMAIN_ZERO_ONE,
    VARIANT_MULTI_DIMENSIONAL,
    KnapsackJsonProblem,
    knapsack_problem_from_dict,
)


def knapsack_multi_dimensional_request_from_dict(
    payload: dict[str, JsonValue],
) -> MultiDimensionalKnapsackRequest:
    required = ("version", "problem_type", "variant", "domain", "resources", "items")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "knapsack.multi_dimensional is missing required fields: "
            + ", ".join(missing)
        )
    variant = str(payload["variant"]).strip().lower().replace("-", "_")
    if variant not in {"multi", "multidimensional", VARIANT_MULTI_DIMENSIONAL}:
        raise ValueError(
            "knapsack.multi_dimensional requires variant 'multi_dimensional'"
        )
    problem = knapsack_problem_from_dict(payload)
    return knapsack_multi_dimensional_request_from_problem(problem)


def knapsack_multi_dimensional_request_from_problem(
    problem: KnapsackJsonProblem,
) -> MultiDimensionalKnapsackRequest:
    if problem.variant != VARIANT_MULTI_DIMENSIONAL:
        raise ValueError(
            "knapsack.multi_dimensional requires variant 'multi_dimensional'"
        )

    resources = tuple(
        MultiDimensionalKnapsackResource(resource.name, resource.capacity)
        for resource in problem.resources
    )
    items = tuple(
        MultiDimensionalKnapsackItem(item.name, item.value, item.usage)
        for item in problem.items
    )
    model = MultiDimensionalKnapsackModel.from_parts(resources, items)
    upper_bounds = tuple(
        _upper_bound(problem.domain, item.max_quantity, index)
        for index, item in enumerate(problem.items)
    )
    return MultiDimensionalKnapsackRequest(model, problem.domain, upper_bounds)


def _upper_bound(domain: str, value: float | None, index: int) -> float | None:
    if domain == DOMAIN_ZERO_ONE:
        return 1.0
    if domain == DOMAIN_UNBOUNDED:
        return None
    if domain == DOMAIN_BOUNDED:
        if value is None or isinf(value):
            raise ValueError(
                f"items[{index}].max_quantity is required for bounded domain"
            )
        return value
    if domain == DOMAIN_FRACTIONAL:
        if value is not None and isinf(value):
            return None
        return 1.0 if value is None else value
    raise ValueError(f"unsupported multi-dimensional domain: {domain!r}")
