from __future__ import annotations

from typing import Protocol

from optees.application.contracts.artifact_rendering import ArtifactSource
from optees.application.contracts.errors import StructuredError


class ArtifactSourcePort(Protocol):
    """Read-only boundary exposing completed job inputs and results."""

    def artifact_source(self, job_id: str) -> ArtifactSource | StructuredError:
        ...
