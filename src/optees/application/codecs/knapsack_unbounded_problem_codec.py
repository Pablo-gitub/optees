from __future__ import annotations

from optees.application.contracts.json_value import JsonValue
from optees.domain.entities.knapsack.unbounded_item import UnboundedKnapsackItem
from optees.domain.models.knapsack.unbounded_knapsack_model import (
    UnboundedKnapsackModel,
)
from optees.utility.knapsack_json_io import (
    DOMAIN_UNBOUNDED,
    VARIANT_UNBOUNDED,
    KnapsackJsonProblem,
    knapsack_problem_from_dict,
)


def knapsack_unbounded_model_from_dict(
    payload: dict[str, JsonValue],
) -> UnboundedKnapsackModel:
    required = ("version", "problem_type", "variant", "capacity", "items")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(
            "knapsack.unbounded is missing required fields: " + ", ".join(missing)
        )
    problem = knapsack_problem_from_dict(payload)
    return knapsack_unbounded_model_from_problem(problem)


def knapsack_unbounded_model_from_problem(
    problem: KnapsackJsonProblem,
) -> UnboundedKnapsackModel:
    if problem.variant != VARIANT_UNBOUNDED or problem.domain != DOMAIN_UNBOUNDED:
        raise ValueError(
            "knapsack.unbounded requires variant 'unbounded' and the unbounded domain"
        )
    if problem.capacity is None:
        raise ValueError("capacity is required for knapsack.unbounded")

    items = []
    for index, item in enumerate(problem.items):
        if item.weight is None:
            raise ValueError(f"items[{index}].weight is required")
        items.append(
            UnboundedKnapsackItem(
                name=item.name,
                value=item.value,
                weight=item.weight,
            )
        )
    return UnboundedKnapsackModel.from_parts(items, capacity=int(problem.capacity))
