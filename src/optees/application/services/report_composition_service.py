from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, replace
from threading import RLock
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
    ReportManifest,
    ReportRequest,
    ReportStatus,
)
from optees.application.contracts.report_composition import (
    ReportCompositionContext,
    ResolvedReportArtifact,
)
from optees.application.ports.artifact_storage_port import ArtifactStoragePort
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


class ReportCompositionService:
    """Asynchronous Markdown composition over verified local jobs and artifacts."""

    def __init__(
        self,
        jobs: LocalJobService,
        artifacts: ArtifactGenerationService,
        storage: ArtifactStoragePort,
        *,
        composer: MarkdownReportComposer | None = None,
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
                    media_type="text/markdown; charset=utf-8",
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
        self._executor.shutdown(wait=wait, cancel_futures=True)
        self._storage.close()

    def _compose(self, report_id: str) -> None:
        with self._lock:
            record = self._records.get(report_id)
            if record is None:
                return
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.COMPOSING,
            )
        jobs: dict[str, ExecutionEnvelope] = {}
        unavailable_jobs: dict[str, str] = {}
        resolved_artifacts: dict[str, ResolvedReportArtifact] = {}
        pinned: list[str] = []
        try:
            for section in record.request.sections:
                for block in section.blocks:
                    if isinstance(block, JobStatusReportBlock):
                        if block.job_id in jobs or block.job_id in unavailable_jobs:
                            continue
                        outcome = self._jobs.result(block.job_id)
                        if isinstance(outcome, StructuredError):
                            unavailable_jobs[block.job_id] = outcome.message
                        else:
                            jobs[block.job_id] = outcome
                    elif isinstance(block, ArtifactReportBlock):
                        if block.artifact_id in resolved_artifacts:
                            continue
                        resolved = self._resolve_artifact(block.artifact_id, pinned)
                        resolved_artifacts[block.artifact_id] = resolved

            composed = self._composer.compose(
                ReportCompositionContext(
                    request=record.request,
                    jobs=jobs,
                    unavailable_jobs=unavailable_jobs,
                    artifacts=resolved_artifacts,
                    optees_version=get_app_version(),
                )
            )
            stored = self._storage.store(
                composed.content,
                media_type=composed.media_type,
                ttl_seconds=self._ttl_seconds,
            )
            with self._lock:
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
                "The Markdown report could not be composed.",
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
            record.manifest = replace(
                record.manifest,
                status=ReportStatus.FAILED,
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
