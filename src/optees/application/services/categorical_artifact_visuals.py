from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
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
    "knapsack.zero_one",
    "knapsack.bounded",
    "knapsack.unbounded",
    "knapsack.fractional",
)

_DEFINITIONS = (
    CategoricalVisualDefinition(
        "milp.linear",
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
        "knapsack.multi_dimensional",
        "item_chart",
        "Knapsack item values",
        "items",
        True,
    ),
    CategoricalVisualDefinition(
        "knapsack.multi_dimensional",
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
