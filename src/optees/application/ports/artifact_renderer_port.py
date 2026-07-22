from __future__ import annotations

from typing import Protocol

from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)


class ArtifactRendererPort(Protocol):
    """Headless boundary for one capability artifact renderer."""

    renderer_version: str

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        """Render deterministic bytes without importing presentation widgets."""
        ...
