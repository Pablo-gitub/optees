from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.entities.knapsack.fractional_item import FractionalKnapsackItem
from optees.domain.models.knapsack.fractional_knapsack_model import (
    FractionalKnapsackModel,
)
from optees.utility.knapsack_json_io import (
    DOMAIN_FRACTIONAL,
    VARIANT_FRACTIONAL,
    KnapsackJsonProblem,
    knapsack_problem_from_dict,
)


def knapsack_fractional_model_from_dict(
    payload: dict[str, JsonValue],
) -> FractionalKnapsackModel:
    required = ("version", "problem_type", "variant", "capacity", "items")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "knapsack.fractional is missing required fields: " + ", ".join(missing)
        )
    variant = str(payload["variant"]).strip().lower().replace("-", "_")
    if variant != VARIANT_FRACTIONAL:
        raise ValueError(
            "knapsack.fractional requires variant 'fractional' and the "
            "fractional domain"
        )
    problem = knapsack_problem_from_dict(payload)
    return knapsack_fractional_model_from_problem(problem)


def knapsack_fractional_model_from_problem(
    problem: KnapsackJsonProblem,
) -> FractionalKnapsackModel:
    if problem.variant != VARIANT_FRACTIONAL or problem.domain != DOMAIN_FRACTIONAL:
        raise ValueError(
            "knapsack.fractional requires variant 'fractional' and the "
            "fractional domain"
        )
    if problem.capacity is None:
        raise ValueError("capacity is required for knapsack.fractional")

    items = []
    for index, item in enumerate(problem.items):
        if item.weight is None:
            raise ValueError(f"items[{index}].weight is required")
        items.append(
            FractionalKnapsackItem(
                name=item.name,
                value=item.value,
                weight=item.weight,
            )
        )
    return FractionalKnapsackModel.from_parts(items, capacity=problem.capacity)
