from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.entities.knapsack.item import KnapsackItem
from optees.domain.models.knapsack.knapsack01_model import Knapsack01Model
from optees.utility.knapsack_json_io import (
    DOMAIN_ZERO_ONE,
    VARIANT_ZERO_ONE,
    KnapsackJsonProblem,
    knapsack_problem_from_dict,
)


def knapsack_zero_one_model_from_dict(
    payload: dict[str, JsonValue],
) -> Knapsack01Model:
    """Parse the shared schema and enforce the 0/1 capability boundary."""

    required = ("version", "problem_type", "variant", "capacity", "items")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "knapsack.zero_one is missing required fields: " + ", ".join(missing)
        )
    problem = knapsack_problem_from_dict(payload)
    return knapsack_zero_one_model_from_problem(problem)


def knapsack_zero_one_model_from_problem(
    problem: KnapsackJsonProblem,
) -> Knapsack01Model:
    if problem.variant != VARIANT_ZERO_ONE or problem.domain != DOMAIN_ZERO_ONE:
        raise ValueError(
            "knapsack.zero_one requires variant 'zero_one' and the 0/1 domain"
        )
    if problem.capacity is None:
        raise ValueError("capacity is required for knapsack.zero_one")

    items = []
    for index, item in enumerate(problem.items):
        if item.weight is None:
            raise ValueError(f"items[{index}].weight is required")
        items.append(
            KnapsackItem(
                name=item.name,
                value=item.value,
                weight=item.weight,
            )
        )
    return Knapsack01Model.from_parts(items, capacity=int(problem.capacity))
