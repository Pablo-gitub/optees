from __future__ import annotations

from threading import Event
from time import monotonic, sleep

from optees.application.codecs.report_request_codec import report_request_from_dict
from optees.application.contracts.artifact import (
    ArtifactBatchRequest,
    ArtifactFormat,
    ArtifactRequest,
    ArtifactStatus,
)
from optees.application.contracts.errors import StructuredError
from optees.application.contracts.report import ReportStatus
from optees.application.contracts.report_backend import (
    RenderedReport,
    ReportBackendCancelledError,
    ReportBackendDiagnostic,
)
from optees.application.services.report_composition_service import (
    ReportCompositionService,
)
from optees.composition.local_agent import (
    create_local_artifact_service,
    create_local_job_service,
)
from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore


class _FakePdfBackend:
    backend_id = "fake.pdf.v1"

    def diagnostic(self):
        return ReportBackendDiagnostic(self.backend_id, True, "fake")

    def render(self, request, *, cancellation, progress):
        assert b"Optees" in request.markdown
        assert not cancellation.is_set()
        progress(75, "rendering_pdf")
        return RenderedReport(
            "application/pdf",
            b"%PDF-1.7\n% deterministic test\n",
            self.backend_id,
        )


class _BlockingPdfBackend(_FakePdfBackend):
    def __init__(self) -> None:
        self.started = Event()

    def render(self, request, *, cancellation, progress):
        del request
        progress(75, "rendering_pdf")
        self.started.set()
        assert cancellation.wait(timeout=2)
        raise ReportBackendCancelledError("cancelled")


def _lp_payload() -> dict:
    return {
        "version": "1",
        "variables": [{"name": "x", "label": "Product", "lb": 0, "ub": 1}],
        "objective": {"sense": "max", "coefficients": [1], "offset": 0},
        "constraints": [],
    }


def _forecast_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "univariate_forecasting",
        "target_name": "daily_orders",
        "frequency": "daily",
        "horizon": 2,
        "method": "naive",
        "missing_period_policy": "reject",
        "observations": [
            {"timestamp": "2026-01-01T00:00:00", "value": 10.0},
            {"timestamp": "2026-01-02T00:00:00", "value": 12.0},
            {"timestamp": "2026-01-03T00:00:00", "value": 14.0},
            {"timestamp": "2026-01-04T00:00:00", "value": 16.0},
        ],
        "evaluation": {"strategy": "holdout", "holdout_size": 1},
    }


def _wait_for_job(jobs, job_id: str) -> None:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        outcome = jobs.get(job_id)
        assert not isinstance(outcome, StructuredError)
        if outcome.job_status.value == "completed":
            return
        sleep(0.01)
    raise AssertionError("job did not complete")


def _wait_for_artifact(artifacts, job_id: str):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        batches = artifacts.list_for_job(job_id)
        assert not isinstance(batches, StructuredError)
        if batches:
            entry = batches[-1].artifacts[0]
            if entry.status is ArtifactStatus.AVAILABLE:
                return entry
        sleep(0.01)
    raise AssertionError("artifact did not become available")


def _wait_for_report(reports, report_id: str):
    deadline = monotonic() + 5
    while monotonic() < deadline:
        outcome = reports.get(report_id)
        assert not isinstance(outcome, StructuredError)
        if outcome.status is ReportStatus.AVAILABLE:
            return outcome
        if outcome.status is ReportStatus.FAILED:
            raise AssertionError(str(outcome.to_dict()))
        sleep(0.01)
    raise AssertionError("report did not become available")


def test_report_service_composes_jobs_tables_provenance_and_footer(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
    )
    try:
        job = jobs.submit("lp.continuous", _lp_payload())
        assert not isinstance(job, StructuredError)
        _wait_for_job(jobs, job.job_id)
        artifacts.submit(
            job.job_id,
            ArtifactBatchRequest(
                (
                    ArtifactRequest(
                        "solution_table",
                        (ArtifactFormat.MARKDOWN,),
                    ),
                )
            ),
        )
        artifact = _wait_for_artifact(artifacts, job.job_id)
        request = report_request_from_dict(
            {
                "contract_version": "1",
                "format": "markdown",
                "locale": "it",
                "title": "Piano di produzione",
                "sections": [
                    {
                        "section_id": "results",
                        "heading": "Risultati",
                        "blocks": [
                            {"type": "job_status", "job_id": job.job_id},
                            {
                                "type": "artifact",
                                "artifact_id": artifact.artifact_id,
                                "caption": "Soluzione",
                            },
                        ],
                    }
                ],
                "metadata": {"author": "Optees test"},
            }
        )

        submitted = reports.submit(request)
        assert not isinstance(submitted, StructuredError)
        available = _wait_for_report(reports, submitted.report_id)
        downloaded = reports.download(submitted.report_id)
        assert not isinstance(downloaded, StructuredError)
        markdown = downloaded.content.decode("utf-8")

        assert available.sha256 == downloaded.artifact.sha256
        assert available.source_job_ids == (job.job_id,)
        assert available.source_artifact_ids == (artifact.artifact_id,)
        assert "Stato del solver" in markdown
        assert "Soluzione" in markdown
        assert artifact.sha256 in markdown
        assert "[Optees · optees.it](https://optees.it)" in markdown
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()


def test_forecast_table_flows_into_markdown_report_without_refitting(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
    )
    try:
        job = jobs.submit("ml.forecasting.univariate", _forecast_payload())
        assert not isinstance(job, StructuredError)
        _wait_for_job(jobs, job.job_id)
        artifacts.submit(
            job.job_id,
            ArtifactBatchRequest(
                (
                    ArtifactRequest(
                        "forecast_table",
                        (ArtifactFormat.MARKDOWN,),
                    ),
                )
            ),
        )
        artifact = _wait_for_artifact(artifacts, job.job_id)
        request = report_request_from_dict(
            {
                "contract_version": "1",
                "format": "markdown",
                "locale": "en",
                "title": "Demand forecast",
                "sections": [
                    {
                        "section_id": "forecast",
                        "heading": "Forecast result",
                        "blocks": [
                            {"type": "job_status", "job_id": job.job_id},
                            {
                                "type": "artifact",
                                "artifact_id": artifact.artifact_id,
                                "caption": "Forecast timeline",
                            },
                        ],
                    }
                ],
            }
        )

        submitted = reports.submit(request)
        assert not isinstance(submitted, StructuredError)
        available = _wait_for_report(reports, submitted.report_id)
        downloaded = reports.download(submitted.report_id)
        assert not isinstance(downloaded, StructuredError)
        markdown = downloaded.content.decode("utf-8")

        assert available.source_job_ids == (job.job_id,)
        assert available.source_artifact_ids == (artifact.artifact_id,)
        assert "Forecast result" in markdown
        assert "Forecast timeline" in markdown
        assert "Timestamp" in markdown
        assert "future" in markdown
        assert "[Optees · optees.it](https://optees.it)" in markdown
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()


def test_missing_sources_are_visible_unsupported_blocks_not_silent_failures(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
    )
    try:
        request = report_request_from_dict(
            {
                "title": "Incomplete report",
                "sections": [
                    {
                        "section_id": "missing",
                        "heading": "Missing references",
                        "blocks": [
                            {"type": "job_status", "job_id": "job-missing"},
                            {
                                "type": "artifact",
                                "artifact_id": "artifact-missing",
                            },
                        ],
                    }
                ],
            }
        )
        submitted = reports.submit(request)
        assert not isinstance(submitted, StructuredError)
        available = _wait_for_report(reports, submitted.report_id)
        downloaded = reports.download(submitted.report_id)
        assert not isinstance(downloaded, StructuredError)

        assert available.unsupported_block_count == 2
        assert downloaded.content.decode("utf-8").count(
            "unsupported_artifact"
        ) == 2
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()


def test_pdf_report_uses_explicit_backend_and_publishes_progress(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
        backend=_FakePdfBackend(),
    )
    try:
        request = report_request_from_dict(
            {
                "format": "pdf",
                "title": "PDF report",
                "sections": [
                    {
                        "section_id": "summary",
                        "heading": "Summary",
                        "blocks": [
                            {"type": "markdown", "content": "Validated result."}
                        ],
                    }
                ],
            }
        )
        submitted = reports.submit(request)
        assert not isinstance(submitted, StructuredError)
        available = _wait_for_report(reports, submitted.report_id)
        downloaded = reports.download(submitted.report_id)
        assert not isinstance(downloaded, StructuredError)

        assert available.media_type == "application/pdf"
        assert available.backend_id == "fake.pdf.v1"
        assert available.progress_percent == 100
        assert available.progress_stage == "complete"
        assert downloaded.content.startswith(b"%PDF-")
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()


def test_pdf_report_fails_before_queue_when_backend_is_unavailable(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
    )
    try:
        request = report_request_from_dict(
            {
                "format": "pdf",
                "title": "Unavailable PDF",
                "sections": [
                    {
                        "section_id": "summary",
                        "heading": "Summary",
                        "blocks": [{"type": "markdown", "content": "Content."}],
                    }
                ],
            }
        )
        outcome = reports.submit(request)

        assert isinstance(outcome, StructuredError)
        assert outcome.code.value == "report_backend_unavailable"
        assert outcome.context["backend"]["available"] is False
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()


def test_composing_pdf_report_can_be_cancelled(tmp_path):
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    backend = _BlockingPdfBackend()
    reports = ReportCompositionService(
        jobs,
        artifacts,
        LocalArtifactStore(parent_directory=tmp_path),
        backend=backend,
    )
    try:
        request = report_request_from_dict(
            {
                "format": "pdf",
                "title": "Cancelled PDF",
                "sections": [
                    {
                        "section_id": "summary",
                        "heading": "Summary",
                        "blocks": [{"type": "markdown", "content": "Content."}],
                    }
                ],
            }
        )
        submitted = reports.submit(request)
        assert not isinstance(submitted, StructuredError)
        assert backend.started.wait(timeout=2)

        cancelled = reports.cancel(submitted.report_id)

        assert not isinstance(cancelled, StructuredError)
        assert cancelled.status is ReportStatus.CANCELLED
        assert cancelled.progress_stage == "cancelled"
        sleep(0.05)
        final = reports.get(submitted.report_id)
        assert not isinstance(final, StructuredError)
        assert final.status is ReportStatus.CANCELLED
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown()
