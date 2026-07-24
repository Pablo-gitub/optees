from __future__ import annotations

from dataclasses import dataclass

from optees.application.contracts.report_backend import ReportBackendAsset


@dataclass(frozen=True)
class ConvertedReportArtifact:
    """Validated report representation derived from one stored artifact."""

    markdown: str | None = None
    assets: tuple[ReportBackendAsset, ...] = ()
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.markdown is None and not self.assets and self.unavailable_reason is None:
            raise ValueError("a report conversion must contain output or a reason")
