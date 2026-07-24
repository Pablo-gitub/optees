from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
from optees.application.contracts.capability_ids import LP_CAPABILITY_ID
from optees.application.contracts.execution import MathematicalStatus


@dataclass(frozen=True)
class LPVisualDefinition:
    capability_id: str
    artifact_type: str
    title: str

    def descriptor(self) -> AvailableArtifact:
        return AvailableArtifact(
            artifact_type=self.artifact_type,
            title=self.title,
            formats=(ArtifactFormat.SVG, ArtifactFormat.PNG),
            required_mathematical_statuses=(MathematicalStatus.OPTIMAL,),
            options_schema={
                "type": "object",
                "properties": {
                    "locale": {"enum": ["en", "it"]},
                    "theme": {"enum": ["light", "dark"]},
                    "width": {
                        "type": "integer",
                        "minimum": 320,
                        "maximum": 4096,
                    },
                    "height": {
                        "type": "integer",
                        "minimum": 240,
                        "maximum": 4096,
                    },
                },
                "additionalProperties": False,
            },
        )


LP_FEASIBLE_REGION = LPVisualDefinition(
    capability_id=LP_CAPABILITY_ID,
    artifact_type="feasible_region",
    title="LP feasible region (2D/3D)",
)


def lp_visual_definitions() -> tuple[LPVisualDefinition, ...]:
    return (LP_FEASIBLE_REGION,)


def lp_visual_descriptors(
    capability_id: str,
) -> tuple[AvailableArtifact, ...]:
    return tuple(
        definition.descriptor()
        for definition in lp_visual_definitions()
        if definition.capability_id == capability_id
    )
