from __future__ import annotations

from typing import Protocol

from optees.application.contracts.report_composition import ResolvedReportArtifact
from optees.application.contracts.report_conversion import ConvertedReportArtifact


class ReportAssetConverterPort(Protocol):
    """Convert only validated stored artifacts into bounded report material."""

    def convert(
        self,
        artifact: ResolvedReportArtifact,
        *,
        views: tuple[str, ...],
        locale: str,
    ) -> ConvertedReportArtifact:
        ...
