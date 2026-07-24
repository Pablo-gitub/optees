from __future__ import annotations

from typing import Protocol

from optees.application.contracts.report_backend import (
    RenderedReport,
    ReportBackendDiagnostic,
    ReportBackendRequest,
    ReportCancellation,
    ReportProgressCallback,
)


class ReportBackendPort(Protocol):
    """Optional local document backend hidden behind the report contract."""

    def diagnostic(self) -> ReportBackendDiagnostic:
        """Describe runtime availability without executing untrusted input."""
        ...

    def render(
        self,
        request: ReportBackendRequest,
        *,
        cancellation: ReportCancellation,
        progress: ReportProgressCallback,
    ) -> RenderedReport:
        """Render one bounded PDF using fixed backend configuration."""
        ...
