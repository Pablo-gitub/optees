from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)


class PackingComplexityLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass(frozen=True)
class PackingComplexityEstimate:
    """Structural size of the exact pairwise-disjunctive MILP.

    For n physical units the formulation creates n(n-1)/2 item pairs and six
    separation binaries per pair. This quadratic term is a more honest warning
    signal than a machine-independent runtime prediction.
    """

    unit_count: int
    orientation_binary_count: int
    pair_count: int
    separation_binary_count: int
    approximate_variable_count: int
    approximate_constraint_count: int
    level: PackingComplexityLevel


def estimate_packing_complexity(
    model: SingleContainerPackingModel,
) -> PackingComplexityEstimate:
    units = model.unit_count()
    orientations = sum(
        item.quantity * len(item.orientations()) for item in model.items
    )
    pairs = units * (units - 1) // 2
    separation = 6 * pairs
    approximate_variables = 4 * units + orientations + separation
    per_unit_constraints = 5 if model.selection_policy.value == "all_required" else 4
    approximate_constraints = (
        per_unit_constraints * units
        + 19 * pairs
        + len(model.container.capacities)
    )

    if units >= 25 or separation >= 1800 or orientations >= 120:
        level = PackingComplexityLevel.HIGH
    elif units >= 15 or separation >= 630 or orientations >= 70:
        level = PackingComplexityLevel.MODERATE
    else:
        level = PackingComplexityLevel.LOW

    return PackingComplexityEstimate(
        unit_count=units,
        orientation_binary_count=orientations,
        pair_count=pairs,
        separation_binary_count=separation,
        approximate_variable_count=approximate_variables,
        approximate_constraint_count=approximate_constraints,
        level=level,
    )
