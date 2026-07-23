from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.artifact import ArtifactManifestEntry
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.contracts.report import ReportRequest


@dataclass(frozen=True)
class ResolvedReportArtifact:
    artifact_id: str
    manifest: ArtifactManifestEntry | None = None
    content: bytes | None = None
    unavailable_reason: str | None = None


@dataclass(frozen=True)
class ReportCompositionContext:
    request: ReportRequest
    jobs: dict[str, ExecutionEnvelope]
    unavailable_jobs: dict[str, str]
    artifacts: dict[str, ResolvedReportArtifact]
    optees_version: str


@dataclass(frozen=True)
class ComposedReport:
    content: bytes
    media_type: str
    source_job_ids: tuple[str, ...]
    source_artifact_ids: tuple[str, ...]
    unsupported_block_count: int
