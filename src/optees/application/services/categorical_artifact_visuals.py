from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
from optees.application.contracts.capability_ids import (
    KNAPSACK_BOUNDED_CAPABILITY_ID,
    KNAPSACK_FRACTIONAL_CAPABILITY_ID,
    KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
    KNAPSACK_UNBOUNDED_CAPABILITY_ID,
    KNAPSACK_ZERO_ONE_CAPABILITY_ID,
    MILP_CAPABILITY_ID,
)
from optees.application.contracts.execution import MathematicalStatus


@dataclass(frozen=True)
class CategoricalVisualDefinition:
    capability_id: str
    artifact_type: str
    title: str
    chart_kind: str
    bounded_categories: bool = False

    def descriptor(self) -> AvailableArtifact:
        properties: dict[str, object] = {
            "locale": {"enum": ["en", "it"]},
            "theme": {"enum": ["light", "dark"]},
            "width": {"type": "integer", "minimum": 320, "maximum": 4096},
            "height": {"type": "integer", "minimum": 240, "maximum": 4096},
        }
        if self.bounded_categories:
            properties["max_items"] = {
                "type": "integer",
                "minimum": 1,
                "maximum": 200,
            }
        return AvailableArtifact(
            artifact_type=self.artifact_type,
            title=self.title,
            formats=(ArtifactFormat.SVG, ArtifactFormat.PNG),
            required_mathematical_statuses=(
                MathematicalStatus.OPTIMAL,
                MathematicalStatus.FEASIBLE,
            ),
            options_schema={
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            },
        )


_KNAPSACK_IDS = (
    KNAPSACK_ZERO_ONE_CAPABILITY_ID,
    KNAPSACK_BOUNDED_CAPABILITY_ID,
    KNAPSACK_UNBOUNDED_CAPABILITY_ID,
    KNAPSACK_FRACTIONAL_CAPABILITY_ID,
)

_DEFINITIONS = (
    CategoricalVisualDefinition(
        MILP_CAPABILITY_ID,
        "variable_chart",
        "MILP variable values",
        "variables",
        True,
    ),
    *tuple(
        CategoricalVisualDefinition(
            capability_id,
            "item_chart",
            "Knapsack item values",
            "items",
            True,
        )
        for capability_id in _KNAPSACK_IDS
    ),
    *tuple(
        CategoricalVisualDefinition(
            capability_id,
            "capacity_chart",
            "Knapsack capacity utilization",
            "capacity",
        )
        for capability_id in _KNAPSACK_IDS
    ),
    CategoricalVisualDefinition(
        KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        "item_chart",
        "Knapsack item values",
        "items",
        True,
    ),
    CategoricalVisualDefinition(
        KNAPSACK_MULTI_DIMENSIONAL_CAPABILITY_ID,
        "resource_chart",
        "Knapsack resource utilization",
        "resources",
        True,
    ),
)


def categorical_visual_definitions() -> tuple[CategoricalVisualDefinition, ...]:
    return _DEFINITIONS


def categorical_visual_descriptors(
    capability_id: str,
) -> tuple[AvailableArtifact, ...]:
    return tuple(
        definition.descriptor()
        for definition in _DEFINITIONS
        if definition.capability_id == capability_id
    )
