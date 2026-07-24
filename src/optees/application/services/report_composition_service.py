from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from threading import Event, RLock
from time import time
from typing import TypeAlias
from uuid import uuid4

from optees.application.contracts.artifact import ArtifactManifestEntry
from optees.application.contracts.artifact_storage import (
    DEFAULT_ARTIFACT_TTL_SECONDS,
    ArtifactCapacityError,
    ArtifactExpiredError,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactStorageClosedError,
    StoredArtifactPayload,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.contracts.report import (
    ArtifactReportBlock,
    JobStatusReportBlock,
    ReportFormat,
    ReportManifest,
    ReportRequest,
    ReportStatus,
)
from optees.application.contracts.report_backend import (
    ReportBackendCancelledError,
    ReportBackendDiagnostic,
    ReportBackendRequest,
    ReportBackendUnavailableError,
)
from optees.application.contracts.report_composition import (
    ReportCompositionContext,
    ResolvedReportArtifact,
)
from optees.application.ports.artifact_storage_port import ArtifactStoragePort
from optees.application.ports.report_asset_converter_port import (
    ReportAssetConverterPort,
)
from optees.application.ports.report_backend_port import ReportBackendPort
from optees.application.services.artifact_generation_service import (
    ArtifactGenerationService,
)
from optees.application.services.local_job_service import LocalJobService
from optees.application.services.markdown_report_composer import (
    MarkdownReportComposer,
)
from optees.core.version import get_app_version


ReportOperationOutcome: TypeAlias = ReportManifest | StructuredError
ReportDownloadOutcome: TypeAlias = StoredArtifactPayload | StructuredError


@dataclass
class _ReportRecord:
    request: ReportRequest
    manifest: ReportManifest
    storage_id: str | None = None
    cancellation: Event = field(default_factory=Event)


class ReportCompositionService:
    """Asynchronous Markdown composition over verified local jobs and artifacts."""

    def __init__(
        self,
        jobs: LocalJobService,
        artifacts: ArtifactGenerationService,
        storage: ArtifactStoragePort,
        *,
        composer: MarkdownReportComposer | None = None,
        backend: ReportBackendPort | None = None,
        asset_converter: ReportAssetConverterPort | None = None,
        ttl_seconds: int = DEFAULT_ARTIFACT_TTL_SECONDS,
        clock: Callable[[], float] = time,
        report_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or ttl_seconds < 1
        ):
            raise ValueError("ttl_seconds must be a positive integer")
        self._jobs = jobs
        self._artifacts = artifacts
        self._storage = storage
        self._composer = composer or MarkdownReportComposer()
        self._backend = backend
        self._asset_converter = asset_converter
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._report_id_factory = report_id_factory or (
            lambda: f"report-{uuid4().hex}"
        )
        self._records: dict[str, _ReportRecord] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="optees-report-composer",
        )
        self._futures: set[Future[None]] = set()
        self._accepting = True
        self._lock = RLock()

    def submit(
        self,
        request: ReportRequest,
        *,
        request_id: str | None = None,
    ) -> ReportOperationOutcome:
        if request.format is ReportFormat.PDF:
            diagnostic = self._backend_diagnostic()
            if not diagnostic.available:
                return StructuredError(
                    code=ErrorCode.REPORT_BACKEND_UNAVAILABLE,
                    message=diagnostic.reason or "The PDF backend is unavailable.",
                    context={"backend": diagnostic.to_dict()},
                    request_id=request_id,
                )
        with self._lock:
            if not self._accepting:
                return StructuredError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="The report service is shutting down.",
                    request_id=request_id,
                )
            report_id = self._report_id_factory()
            now = self._clock()
            record = _ReportRecord(
                request=request,
                manifest=ReportManifest(
                    report_id=report_id,
                    title=request.title,
                    locale=request.locale,
                    format=request.format,
                    media_type=(
                        "application/pdf"
                        if request.format is ReportFormat.PDF
                        else "text/markdown; charset=utf-8"
                    ),
                    status=ReportStatus.QUEUED,
                    created_at=_iso_timestamp(now),
                    expires_at=_iso_timestamp(now + self._ttl_seconds),
                ),
            )
            self._records[report_id] = record
            future = self._executor.submit(self._compose, report_id)
            self._futures.add(future)
            future.add_done_callback(self._forget_future)
            return record.manifest

    def backend_diagnostics(self) -> tuple[ReportBackendDiagnostic, ...]:
        return (self._backend_diagnostic(),)

    def cancel(self, report_id: str) -> ReportOperationOutcome:
        with self._lock:
            record = self._records.get(report_id)
            if record is None:
                return _report_error(
                    ErrorCode.REPORT_NOT_FOUND,
                    "The report was not found.",
                    report_id,
                )
            if record.manifest.status in {
                ReportStatus.AVAILABLE,
                ReportStatus.FAILED,
                ReportStatus.CANCELLED,
                ReportStatus.EXPIRED,
            }:
                return record.manifest
            record.cancellation.set()
            self._mark_cancelled(record)
            return record.manifest

    def get(self, report_id: str) -> ReportOperationOutcome:
        with self._lock:
            record = self._records.get(report_id)
            if record is None:
                return _report_error(
                    ErrorCode.REPORT_NOT_FOUND,
                    "The report was not found.",
                    report_id,
                )
            self._refresh(record)
            if record.manifest.status is ReportStatus.EXPIRED:
                return _report_error(
                    ErrorCode.REPORT_EXPIRED,
                    "The report has expired.",
                    report_id,
                )
            return record.manifest

    def download(self, report_id: str) -> ReportDownloadOutcome:
        with self._lock:
            record = self._records.get(report_id)
            if record is None:
                return _report_error(
                    ErrorCode.REPORT_NOT_FOUND,
                    "The report was not found.",
                    report_id,
                )
            self._refresh(record)
            if record.manifest.status is ReportStatus.EXPIRED:
                return _report_error(
                    ErrorCode.REPORT_EXPIRED,
                    "The report has expired.",
                    report_id,
                )
            if (
                record.manifest.status is not ReportStatus.AVAILABLE
                or record.storage_id is None
            ):
                return _report_error(
                    ErrorCode.REPORT_ARTIFACT_NOT_AVAILABLE,
                    "The report is not available for download.",
                    report_id,
                )
            storage_id = record.storage_id
        try:
            return self._storage.get(storage_id)
        except ArtifactExpiredError:
            self._mark_expired(record)
            return _report_error(
                ErrorCode.REPORT_EXPIRED,
                "The report has expired.",
                report_id,
            )
        except ArtifactNotFoundError:
            return _report_error(
                ErrorCode.REPORT_NOT_FOUND,
                "The report content was not found.",
                report_id,
            )
        except (ArtifactIntegrityError, ArtifactStorageClosedError):
            return _report_error(
                ErrorCode.REPORT_BACKEND_UNAVAILABLE,
                "The report storage could not return verified content.",
                report_id,
            )

    def close(self, *, wait: bool = True) -> None:
        with self._lock:
            if not self._accepting:
                return
            self._accepting = False
            for record in self._records.values():
                record.cancellation.set()
        self._executor.shutdown(wait=wait, cancel_futures=True)
        self._storage.close()

    def _compose(self, report_id: str) -> None:
        with self._lock:
            record = self._records.get(report_id)
            if record is None:
                return
            if record.cancellation.is_set():
                self._mark_cancelled(record)
                return
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.COMPOSING,
                progress_percent=10,
                progress_stage="resolving_sources",
            )
        jobs: dict[str, ExecutionEnvelope] = {}
        unavailable_jobs: dict[str, str] = {}
        resolved_artifacts: dict[str, ResolvedReportArtifact] = {}
        artifact_views: dict[str, tuple[str, ...]] = {}
        pinned: list[str] = []
        try:
            for section in record.request.sections:
                for block in section.blocks:
                    if record.cancellation.is_set():
                        self._mark_cancelled(record)
                        return
                    if isinstance(block, JobStatusReportBlock):
                        if block.job_id in jobs or block.job_id in unavailable_jobs:
                            continue
                        outcome = self._jobs.result(block.job_id)
                        if isinstance(outcome, StructuredError):
                            unavailable_jobs[block.job_id] = outcome.message
                        else:
                            jobs[block.job_id] = outcome
                    elif isinstance(block, ArtifactReportBlock):
                        previous = artifact_views.get(block.artifact_id, ())
                        artifact_views[block.artifact_id] = tuple(
                            dict.fromkeys((*previous, *block.views))
                        )
                        if block.artifact_id in resolved_artifacts:
                            continue
                        resolved = self._resolve_artifact(block.artifact_id, pinned)
                        resolved_artifacts[block.artifact_id] = resolved

            if self._asset_converter is not None:
                for artifact_id, resolved in tuple(resolved_artifacts.items()):
                    manifest = resolved.manifest
                    if (
                        manifest is not None
                        and resolved.content is not None
                        and (
                            manifest.format.value == "xlsx"
                            or (
                                manifest.format.value == "obj_mtl_zip"
                                and record.request.format is ReportFormat.PDF
                            )
                        )
                    ):
                        conversion = self._asset_converter.convert(
                            resolved,
                            views=artifact_views.get(artifact_id, ()),
                            locale=record.request.locale,
                        )
                        resolved_artifacts[artifact_id] = replace(
                            resolved,
                            conversion=conversion,
                        )
            if record.cancellation.is_set():
                self._mark_cancelled(record)
                return
            self._update_progress(record, 40, "composing_markdown")
            composed = self._composer.compose(
                ReportCompositionContext(
                    request=record.request,
                    jobs=jobs,
                    unavailable_jobs=unavailable_jobs,
                    artifacts=resolved_artifacts,
                    optees_version=get_app_version(),
                )
            )
            content = composed.content
            media_type = composed.media_type
            backend_id = "optees.markdown.v1"
            if record.request.format is ReportFormat.PDF:
                backend = self._backend
                if backend is None:
                    raise ReportBackendUnavailableError(
                        "The PDF backend is not configured."
                    )
                rendered = backend.render(
                    ReportBackendRequest(
                        markdown=composed.content,
                        title=record.request.title,
                        locale=record.request.locale,
                        assets=composed.assets,
                    ),
                    cancellation=record.cancellation,
                    progress=lambda percent, stage: self._update_progress(
                        record,
                        percent,
                        stage,
                    ),
                )
                content = rendered.content
                media_type = rendered.media_type
                backend_id = rendered.backend_id
            if record.cancellation.is_set():
                self._mark_cancelled(record)
                return
            self._update_progress(record, 95, "storing_report")
            stored = self._storage.store(
                content,
                media_type=media_type,
                ttl_seconds=self._ttl_seconds,
            )
            with self._lock:
                if record.cancellation.is_set():
                    self._mark_cancelled(record)
                    return
                record.storage_id = stored.artifact_id
                record.manifest = replace(
                    record.manifest,
                    status=ReportStatus.AVAILABLE,
                    media_type=stored.media_type,
                    created_at=stored.created_at,
                    expires_at=stored.expires_at,
                    source_job_ids=composed.source_job_ids,
                    source_artifact_ids=composed.source_artifact_ids,
                    size_bytes=stored.size_bytes,
                    sha256=stored.sha256,
                    unsupported_block_count=composed.unsupported_block_count,
                    progress_percent=100,
                    progress_stage="complete",
                    backend_id=backend_id,
                )
        except ReportBackendCancelledError:
            self._mark_cancelled(record)
        except ReportBackendUnavailableError as error:
            self._fail(
                record,
                ErrorCode.REPORT_BACKEND_UNAVAILABLE,
                str(error),
            )
        except ArtifactCapacityError:
            self._fail(
                record,
                ErrorCode.REPORT_CAPACITY_EXCEEDED,
                "Report storage capacity was exceeded.",
            )
        except (ArtifactStorageClosedError, ArtifactIntegrityError):
            self._fail(
                record,
                ErrorCode.REPORT_BACKEND_UNAVAILABLE,
                "Report storage is unavailable.",
            )
        except Exception:
            self._fail(
                record,
                ErrorCode.REPORT_COMPOSITION_FAILED,
                "The report could not be composed.",
            )
        finally:
            for artifact_id in pinned:
                self._artifacts.unpin(artifact_id)

    def _resolve_artifact(
        self,
        artifact_id: str,
        pinned: list[str],
    ) -> ResolvedReportArtifact:
        manifest = self._artifacts.manifest_entry(artifact_id)
        if isinstance(manifest, StructuredError):
            return ResolvedReportArtifact(
                artifact_id,
                unavailable_reason=manifest.message,
            )
        assert isinstance(manifest, ArtifactManifestEntry)
        pin_error = self._artifacts.pin(artifact_id)
        if pin_error is not None:
            return ResolvedReportArtifact(
                artifact_id,
                manifest=manifest,
                unavailable_reason=pin_error.message,
            )
        pinned.append(artifact_id)
        payload = self._artifacts.download(artifact_id)
        if isinstance(payload, StructuredError):
            return ResolvedReportArtifact(
                artifact_id,
                manifest=manifest,
                unavailable_reason=payload.message,
            )
        return ResolvedReportArtifact(
            artifact_id,
            manifest=manifest,
            content=payload.content,
        )

    def _refresh(self, record: _ReportRecord) -> None:
        if (
            record.manifest.status is not ReportStatus.AVAILABLE
            or record.storage_id is None
        ):
            return
        try:
            self._storage.describe(record.storage_id)
        except (ArtifactExpiredError, ArtifactNotFoundError):
            self._mark_expired(record)

    def _backend_diagnostic(self) -> ReportBackendDiagnostic:
        if self._backend is None:
            return ReportBackendDiagnostic(
                backend_id="pandoc.typst.v1",
                available=False,
                engine="typst",
                reason="The optional Pandoc+Typst PDF backend is not configured.",
            )
        return self._backend.diagnostic()

    def _update_progress(
        self,
        record: _ReportRecord,
        percent: int,
        stage: str,
    ) -> None:
        with self._lock:
            if record.manifest.status in {
                ReportStatus.CANCELLED,
                ReportStatus.FAILED,
                ReportStatus.EXPIRED,
                ReportStatus.AVAILABLE,
            }:
                return
            record.manifest = replace(
                record.manifest,
                progress_percent=max(record.manifest.progress_percent, percent),
                progress_stage=stage,
            )

    def _mark_cancelled(self, record: _ReportRecord) -> None:
        with self._lock:
            if record.manifest.status in {
                ReportStatus.AVAILABLE,
                ReportStatus.FAILED,
                ReportStatus.EXPIRED,
            }:
                return
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.CANCELLED,
                progress_stage="cancelled",
            )

    def _forget_future(self, future: Future[None]) -> None:
        with self._lock:
            self._futures.discard(future)

    def _mark_expired(self, record: _ReportRecord) -> None:
        with self._lock:
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.EXPIRED,
                size_bytes=None,
                sha256=None,
            )

    def _fail(
        self,
        record: _ReportRecord,
        code: ErrorCode,
        message: str,
    ) -> None:
        with self._lock:
            if record.manifest.status is ReportStatus.CANCELLED:
                return
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.FAILED,
                progress_stage="failed",
                error=StructuredError(code=code, message=message),
            )


def _report_error(
    code: ErrorCode,
    message: str,
    report_id: str,
) -> StructuredError:
    return StructuredError(
        code=code,
        message=message,
        context={"report_id": report_id},
    )


def _iso_timestamp(epoch_seconds: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(epoch_seconds, timezone.utc).isoformat()
