from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactFormat, AvailableArtifact
from optees.application.contracts.capability_ids import PACKING_CAPABILITY_ID
from optees.application.contracts.execution import MathematicalStatus


@dataclass(frozen=True)
class PackingSceneDefinition:
    capability_id: str
    artifact_type: str
    title: str
    formats: tuple[ArtifactFormat, ...]
    supports_view: bool = False

    def descriptor(self) -> AvailableArtifact:
        properties: dict[str, object] = {
            "locale": {"enum": ["en", "it"]},
        }
        if self.supports_view:
            properties.update(
                {
                    "theme": {"enum": ["light", "dark"]},
                    "width": {
                        "type": "integer",
                        "minimum": 640,
                        "maximum": 4096,
                    },
                    "height": {
                        "type": "integer",
                        "minimum": 480,
                        "maximum": 4096,
                    },
                    "view": {"enum": ["isometric", "front", "side", "top", "all"]},
                    "labels": {"enum": ["none", "items"]},
                    "max_labels": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                    },
                }
            )
        return AvailableArtifact(
            artifact_type=self.artifact_type,
            title=self.title,
            formats=self.formats,
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


_DEFINITIONS = (
    PackingSceneDefinition(
        PACKING_CAPABILITY_ID,
        "scene_views",
        "Packing scene camera views",
        (ArtifactFormat.PNG,),
        supports_view=True,
    ),
    PackingSceneDefinition(
        PACKING_CAPABILITY_ID,
        "scene_model",
        "Packing scene OBJ + MTL model",
        (ArtifactFormat.OBJ_MTL_ZIP,),
    ),
)


def packing_scene_definitions() -> tuple[PackingSceneDefinition, ...]:
    return _DEFINITIONS


def packing_scene_descriptors(
    capability_id: str,
) -> tuple[AvailableArtifact, ...]:
    return tuple(
        definition.descriptor()
        for definition in _DEFINITIONS
        if definition.capability_id == capability_id
    )
