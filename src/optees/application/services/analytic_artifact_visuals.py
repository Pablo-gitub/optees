from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
from optees.application.contracts.execution import MathematicalStatus


@dataclass(frozen=True)
class AnalyticVisualDefinition:
    capability_id: str
    artifact_type: str
    title: str
    chart_kind: str
    statuses: tuple[MathematicalStatus, ...]
    supports_max_points: bool = False
    supports_view: bool = False

    def descriptor(self) -> AvailableArtifact:
        properties: dict[str, object] = {
            "locale": {"enum": ["en", "it"]},
            "theme": {"enum": ["light", "dark"]},
            "width": {"type": "integer", "minimum": 320, "maximum": 4096},
            "height": {"type": "integer", "minimum": 240, "maximum": 4096},
        }
        if self.supports_max_points:
            properties["max_points"] = {
                "type": "integer",
                "minimum": 10,
                "maximum": 2000,
            }
        if self.supports_view:
            properties["view"] = {"enum": ["contour", "surface"]}
            properties["resolution"] = {
                "type": "integer",
                "minimum": 20,
                "maximum": 200,
            }
        return AvailableArtifact(
            artifact_type=self.artifact_type,
            title=self.title,
            formats=(ArtifactFormat.SVG, ArtifactFormat.PNG),
            required_mathematical_statuses=self.statuses,
            options_schema={
                "type": "object",
                "properties": properties,
                "additionalProperties": False,
            },
        )


_OPTIMAL = (MathematicalStatus.OPTIMAL,)
_FEASIBLE = (MathematicalStatus.FEASIBLE,)

_DEFINITIONS = (
    AnalyticVisualDefinition(
        "graph.shortest_path.dijkstra",
        "highlighted_graph",
        "Shortest path graph",
        "dijkstra_graph",
        _OPTIMAL,
    ),
    AnalyticVisualDefinition(
        "nlp.continuous_local",
        "convergence_chart",
        "NLP convergence history",
        "nlp_convergence",
        _FEASIBLE,
        supports_max_points=True,
    ),
    AnalyticVisualDefinition(
        "nlp.continuous_local",
        "objective_landscape",
        "NLP objective landscape",
        "nlp_landscape",
        _FEASIBLE,
        supports_view=True,
    ),
    AnalyticVisualDefinition(
        "ml.regression.linear",
        "fit_chart",
        "Regression fit",
        "regression_fit",
        _FEASIBLE,
        supports_max_points=True,
    ),
    AnalyticVisualDefinition(
        "ml.classification.binary_logistic",
        "confusion_matrix",
        "Classification confusion matrix",
        "classification_confusion",
        _FEASIBLE,
    ),
    AnalyticVisualDefinition(
        "ml.classification.binary_logistic",
        "decision_boundary",
        "Classification decision boundary",
        "classification_boundary",
        _FEASIBLE,
        supports_max_points=True,
    ),
)


def analytic_visual_definitions() -> tuple[AnalyticVisualDefinition, ...]:
    return _DEFINITIONS


def analytic_visual_descriptors(
    capability_id: str,
) -> tuple[AvailableArtifact, ...]:
    return tuple(
        definition.descriptor()
        for definition in _DEFINITIONS
        if definition.capability_id == capability_id
    )
