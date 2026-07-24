from __future__ import annotations

import json
from copy import deepcopy
from collections.abc import Callable, Mapping
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from threading import Event, RLock
from time import time
from typing import TypeAlias
from uuid import uuid4

from optees.application.contracts.artifact import (
    ArtifactBatchManifest,
    ArtifactBatchRequest,
    ArtifactFormat,
    ArtifactManifestEntry,
    ArtifactProvenance,
    ArtifactRequest,
    ArtifactStatus,
    AvailableArtifact,
)
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    ArtifactRenderOptions,
    ArtifactSource,
)
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
from optees.application.ports.artifact_renderer_port import ArtifactRendererPort
from optees.application.ports.artifact_source_port import ArtifactSourcePort
from optees.application.ports.artifact_storage_port import ArtifactStoragePort


ArtifactBatchOutcome: TypeAlias = ArtifactBatchManifest | StructuredError
ArtifactDownloadOutcome: TypeAlias = StoredArtifactPayload | StructuredError

_STANDARD_OPTION_KEYS = {
    "locale",
    "theme",
    "width",
    "height",
    "font_family",
}


@dataclass(frozen=True)
class ArtifactRendererRegistration:
    capability_id: str
    descriptor: AvailableArtifact
    renderer: ArtifactRendererPort
    media_types: Mapping[ArtifactFormat, str]

    def __post_init__(self) -> None:
        if not self.capability_id.strip():
            raise ValueError("artifact renderer capability_id must not be empty")
        if set(self.media_types) != set(self.descriptor.formats):
            raise ValueError("artifact media types must match advertised formats")
        if any(not value.strip() for value in self.media_types.values()):
            raise ValueError("artifact media types must not be empty")
        if not self.renderer.renderer_version.strip():
            raise ValueError("renderer_version must not be empty")


@dataclass
class _ArtifactRecord:
    entry: ArtifactManifestEntry
    storage_id: str | None = None
    fingerprint: str | None = None
    cancellation: Event = field(default_factory=Event)


@dataclass(frozen=True)
class _RenderTask:
    public_artifact_id: str
    registration: ArtifactRendererRegistration
    request: ArtifactRequest
    format: ArtifactFormat
    options: ArtifactRenderOptions
    source: ArtifactSource


class ArtifactGenerationService:
    """Asynchronous, bounded artifact orchestration independent of HTTP."""

    def __init__(
        self,
        source_port: ArtifactSourcePort,
        storage: ArtifactStoragePort,
        *,
        registrations: tuple[ArtifactRendererRegistration, ...] = (),
        render_timeout_seconds: float = 60.0,
        ttl_seconds: int = DEFAULT_ARTIFACT_TTL_SECONDS,
        clock: Callable[[], float] = time,
        artifact_id_factory: Callable[[], str] | None = None,
        batch_id_factory: Callable[[], str] | None = None,
    ) -> None:
        if (
            isinstance(render_timeout_seconds, bool)
            or not isinstance(render_timeout_seconds, (int, float))
            or render_timeout_seconds <= 0
        ):
            raise ValueError("render_timeout_seconds must be positive")
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or ttl_seconds < 1
        ):
            raise ValueError("ttl_seconds must be a positive integer")

        registry: dict[tuple[str, str], ArtifactRendererRegistration] = {}
        for registration in registrations:
            key = (
                registration.capability_id,
                registration.descriptor.artifact_type,
            )
            if key in registry:
                raise ValueError("duplicate artifact renderer registration")
            registry[key] = registration

        self._source_port = source_port
        self._storage = storage
        self._registry = registry
        self._render_timeout_seconds = float(render_timeout_seconds)
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._artifact_id_factory = artifact_id_factory or (
            lambda: f"artifact-{uuid4().hex}"
        )
        self._batch_id_factory = batch_id_factory or (
            lambda: f"artifact-batch-{uuid4().hex}"
        )
        self._records: dict[str, _ArtifactRecord] = {}
        self._job_batches: dict[str, list[str]] = {}
        self._batch_artifacts: dict[str, tuple[str, ...]] = {}
        self._fingerprints: dict[str, str] = {}
        self._coordinator = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="optees-artifact-coordinator",
        )
        self._renderer = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix="optees-artifact-renderer",
        )
        self._futures: set[Future[None]] = set()
        self._lock = RLock()
        self._accepting = True

    def submit(
        self,
        job_id: str,
        request: ArtifactBatchRequest,
        *,
        request_id: str | None = None,
    ) -> ArtifactBatchOutcome:
        source = self._source_port.artifact_source(job_id)
        if isinstance(source, StructuredError):
            return replace(source, request_id=request_id or source.request_id)

        prepared: list[
            tuple[
                str,
                ArtifactRendererRegistration,
                ArtifactRequest,
                ArtifactFormat,
                ArtifactRenderOptions,
                str,
            ]
        ] = []
        for artifact_request in request.requests:
            registration = self._registry.get(
                (source.capability_id, artifact_request.artifact_type)
            )
            if registration is None:
                return StructuredError(
                    code=ErrorCode.ARTIFACT_NOT_SUPPORTED,
                    message=(
                        "The requested artifact type is not available for this "
                        "capability."
                    ),
                    request_id=request_id,
                    context={
                        "capability_id": source.capability_id,
                        "artifact_type": artifact_request.artifact_type,
                    },
                )
            if (
                registration.descriptor.required_mathematical_statuses
                and source.envelope.mathematical_status
                not in registration.descriptor.required_mathematical_statuses
            ):
                return StructuredError(
                    code=ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE,
                    message="The job result status cannot produce this artifact.",
                    request_id=request_id,
                    context={
                        "job_id": job_id,
                        "artifact_type": artifact_request.artifact_type,
                        "mathematical_status": (
                            source.envelope.mathematical_status.value
                            if source.envelope.mathematical_status
                            else None
                        ),
                    },
                )
            try:
                _validate_declared_options(
                    artifact_request.options,
                    registration.descriptor.options_schema,
                )
                options = _render_options(artifact_request.options)
            except (TypeError, ValueError) as exc:
                return StructuredError(
                    code=ErrorCode.ARTIFACT_REQUEST_INVALID,
                    message=str(exc),
                    request_id=request_id,
                )
            for format_ in artifact_request.formats:
                if format_ not in registration.descriptor.formats:
                    return StructuredError(
                        code=ErrorCode.ARTIFACT_NOT_SUPPORTED,
                        message="The requested artifact format is not available.",
                        request_id=request_id,
                        context={
                            "capability_id": source.capability_id,
                            "artifact_type": artifact_request.artifact_type,
                            "format": format_.value,
                        },
                    )
                fingerprint = _fingerprint(
                    job_id,
                    artifact_request,
                    format_,
                    registration.renderer.renderer_version,
                )
                prepared.append(
                    (
                        self._artifact_id_factory(),
                        registration,
                        artifact_request,
                        format_,
                        options,
                        fingerprint,
                    )
                )

        with self._lock:
            if not self._accepting:
                return StructuredError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="The artifact service is shutting down.",
                    request_id=request_id,
                )
            batch_id = self._batch_id_factory()
            artifact_ids: list[str] = []
            tasks: list[_RenderTask] = []
            now = self._clock()
            for (
                generated_id,
                registration,
                item,
                format_,
                options,
                fingerprint,
            ) in prepared:
                reused_id = self._reusable_artifact_id(fingerprint)
                if reused_id is not None:
                    artifact_ids.append(reused_id)
                    continue

                provenance = ArtifactProvenance(
                    capability_id=source.capability_id,
                    job_id=job_id,
                    problem_schema_version=(
                        source.envelope.metadata.problem_schema_version
                    ),
                    result_schema_version=(
                        source.envelope.metadata.result_schema_version
                    ),
                    renderer_version=registration.renderer.renderer_version,
                    locale=options.locale,
                    theme=options.theme,
                )
                entry = ArtifactManifestEntry(
                    artifact_id=generated_id,
                    artifact_type=item.artifact_type,
                    format=format_,
                    media_type=registration.media_types[format_],
                    status=ArtifactStatus.QUEUED,
                    provenance=provenance,
                    created_at=_iso_timestamp(now),
                    expires_at=_iso_timestamp(now + self._ttl_seconds),
                )
                self._records[generated_id] = _ArtifactRecord(
                    entry=entry,
                    fingerprint=fingerprint,
                )
                artifact_ids.append(generated_id)
                tasks.append(
                    _RenderTask(
                        public_artifact_id=generated_id,
                        registration=registration,
                        request=item,
                        format=format_,
                        options=options,
                        source=source,
                    )
                )
            self._batch_artifacts[batch_id] = tuple(artifact_ids)
            self._job_batches.setdefault(job_id, []).append(batch_id)
            if tasks:
                future = self._coordinator.submit(self._render_batch, tuple(tasks))
                self._futures.add(future)
                future.add_done_callback(self._forget_future)
            return self._manifest(batch_id, job_id)

    def list_for_job(
        self,
        job_id: str,
    ) -> tuple[ArtifactBatchManifest, ...] | StructuredError:
        source = self._source_port.artifact_source(job_id)
        with self._lock:
            batch_ids = tuple(self._job_batches.get(job_id, ()))
            if not batch_ids and isinstance(source, StructuredError):
                return source
            self._refresh_expired()
            return tuple(self._manifest(batch_id, job_id) for batch_id in batch_ids)

    def manifest_entry(
        self,
        artifact_id: str,
    ) -> ArtifactManifestEntry | StructuredError:
        """Return transport-neutral metadata without reading artifact bytes."""

        with self._lock:
            self._refresh_expired()
            record = self._records.get(artifact_id)
            if record is None:
                return _artifact_error(
                    ErrorCode.ARTIFACT_NOT_FOUND,
                    "The artifact was not found.",
                    artifact_id,
                )
            if record.entry.status is ArtifactStatus.EXPIRED:
                return _artifact_error(
                    ErrorCode.ARTIFACT_EXPIRED,
                    "The artifact has expired.",
                    artifact_id,
                )
            return record.entry

    def download(self, artifact_id: str) -> ArtifactDownloadOutcome:
        with self._lock:
            record = self._records.get(artifact_id)
            if record is None:
                return _artifact_error(
                    ErrorCode.ARTIFACT_NOT_FOUND,
                    "The artifact was not found.",
                    artifact_id,
                )
            if record.entry.status is ArtifactStatus.EXPIRED:
                return _artifact_error(
                    ErrorCode.ARTIFACT_EXPIRED,
                    "The artifact has expired.",
                    artifact_id,
                )
            if (
                record.entry.status is not ArtifactStatus.AVAILABLE
                or record.storage_id is None
            ):
                return _artifact_error(
                    ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE,
                    "The artifact is not available for download.",
                    artifact_id,
                )
            storage_id = record.storage_id
        try:
            return self._storage.get(storage_id)
        except ArtifactExpiredError:
            self._mark_expired(artifact_id)
            return _artifact_error(
                ErrorCode.ARTIFACT_EXPIRED,
                "The artifact has expired.",
                artifact_id,
            )
        except ArtifactNotFoundError:
            return _artifact_error(
                ErrorCode.ARTIFACT_NOT_FOUND,
                "The artifact content was not found.",
                artifact_id,
            )
        except (ArtifactIntegrityError, ArtifactStorageClosedError):
            return _artifact_error(
                ErrorCode.ARTIFACT_BACKEND_UNAVAILABLE,
                "The artifact storage could not return verified content.",
                artifact_id,
            )

    def cancel(self, artifact_id: str) -> ArtifactManifestEntry | StructuredError:
        with self._lock:
            record = self._records.get(artifact_id)
            if record is None:
                return _artifact_error(
                    ErrorCode.ARTIFACT_NOT_FOUND,
                    "The artifact was not found.",
                    artifact_id,
                )
            if record.entry.status in {
                ArtifactStatus.AVAILABLE,
                ArtifactStatus.FAILED,
                ArtifactStatus.CANCELLED,
                ArtifactStatus.EXPIRED,
            }:
                return record.entry
            record.cancellation.set()
            self._mark_cancelled(artifact_id)
            return record.entry

    def pin(self, artifact_id: str) -> StructuredError | None:
        """Prevent one available public artifact from expiring during composition."""

        with self._lock:
            self._refresh_expired()
            record = self._records.get(artifact_id)
            if record is None:
                return _artifact_error(
                    ErrorCode.ARTIFACT_NOT_FOUND,
                    "The artifact was not found.",
                    artifact_id,
                )
            if (
                record.entry.status is not ArtifactStatus.AVAILABLE
                or record.storage_id is None
            ):
                return _artifact_error(
                    ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE,
                    "The artifact is not available for report composition.",
                    artifact_id,
                )
            storage_id = record.storage_id
        try:
            self._storage.pin(storage_id)
        except ArtifactExpiredError:
            self._mark_expired(artifact_id)
            return _artifact_error(
                ErrorCode.ARTIFACT_EXPIRED,
                "The artifact has expired.",
                artifact_id,
            )
        except ArtifactNotFoundError:
            return _artifact_error(
                ErrorCode.ARTIFACT_NOT_FOUND,
                "The artifact content was not found.",
                artifact_id,
            )
        except ArtifactStorageClosedError:
            return _artifact_error(
                ErrorCode.ARTIFACT_BACKEND_UNAVAILABLE,
                "The artifact storage is unavailable.",
                artifact_id,
            )
        return None

    def unpin(self, artifact_id: str) -> None:
        """Release a composition pin; cleanup remains owned by artifact storage."""

        with self._lock:
            record = self._records.get(artifact_id)
            storage_id = None if record is None else record.storage_id
        if storage_id is None:
            return
        try:
            self._storage.unpin(storage_id)
        except (ValueError, ArtifactNotFoundError, ArtifactStorageClosedError):
            return

    def close(self, *, wait: bool = True) -> None:
        with self._lock:
            if not self._accepting:
                return
            self._accepting = False
            for record in self._records.values():
                record.cancellation.set()
        self._coordinator.shutdown(wait=wait, cancel_futures=True)
        self._renderer.shutdown(wait=wait, cancel_futures=True)
        self._storage.close()

    def _render_batch(self, tasks: tuple[_RenderTask, ...]) -> None:
        for task in tasks:
            with self._lock:
                record = self._records.get(task.public_artifact_id)
                if record is None or record.cancellation.is_set():
                    self._mark_cancelled(task.public_artifact_id)
                    continue
            self._render_one(task)

    def _render_one(self, task: _RenderTask) -> None:
        source = task.source
        with self._lock:
            record = self._records.get(task.public_artifact_id)
            if record is None:
                return
            if record.cancellation.is_set():
                self._mark_cancelled(task.public_artifact_id)
                return
            record.entry = replace(
                record.entry,
                status=ArtifactStatus.RENDERING,
                progress_percent=10,
                progress_stage="rendering",
            )

        context = ArtifactRenderContext(
            capability_id=source.capability_id,
            artifact_type=task.request.artifact_type,
            format=task.format,
            problem=deepcopy(source.problem),
            envelope=deepcopy(source.envelope),
            options=task.options,
        )
        render_future = self._renderer.submit(
            task.registration.renderer.render,
            context,
        )
        try:
            rendered = render_future.result(timeout=self._render_timeout_seconds)
            with self._lock:
                record = self._records.get(task.public_artifact_id)
                if record is None or record.cancellation.is_set():
                    self._mark_cancelled(task.public_artifact_id)
                    return
            expected_media_type = task.registration.media_types[task.format]
            if rendered.media_type != expected_media_type:
                raise ValueError("renderer returned an unexpected media type")
            stored = self._storage.store(
                rendered.content,
                media_type=rendered.media_type,
                ttl_seconds=self._ttl_seconds,
            )
        except TimeoutError:
            render_future.cancel()
            self._fail(
                task.public_artifact_id,
                ErrorCode.ARTIFACT_RENDER_FAILED,
                "Artifact rendering exceeded its configured timeout.",
            )
            return
        except ArtifactCapacityError:
            self._fail(
                task.public_artifact_id,
                ErrorCode.ARTIFACT_CAPACITY_EXCEEDED,
                "Artifact storage capacity was exceeded.",
            )
            return
        except (ArtifactStorageClosedError, ArtifactIntegrityError):
            self._fail(
                task.public_artifact_id,
                ErrorCode.ARTIFACT_BACKEND_UNAVAILABLE,
                "Artifact storage is unavailable.",
            )
            return
        except Exception:
            self._fail(
                task.public_artifact_id,
                ErrorCode.ARTIFACT_RENDER_FAILED,
                "The artifact renderer failed.",
            )
            return

        with self._lock:
            record = self._records.get(task.public_artifact_id)
            if record is None:
                return
            if record.cancellation.is_set():
                self._mark_cancelled(task.public_artifact_id)
                return
            record.storage_id = stored.artifact_id
            record.entry = replace(
                record.entry,
                status=ArtifactStatus.AVAILABLE,
                media_type=stored.media_type,
                size_bytes=stored.size_bytes,
                sha256=stored.sha256,
                created_at=stored.created_at,
                expires_at=stored.expires_at,
                progress_percent=100,
                progress_stage="complete",
            )
            if record.fingerprint is not None:
                self._fingerprints[record.fingerprint] = task.public_artifact_id

    def _fail(self, artifact_id: str, code: ErrorCode, message: str) -> None:
        with self._lock:
            record = self._records.get(artifact_id)
            if record is None:
                return
            if record.entry.status is ArtifactStatus.CANCELLED:
                return
            record.entry = replace(
                record.entry,
                status=ArtifactStatus.FAILED,
                progress_stage="failed",
                error=StructuredError(code=code, message=message),
            )

    def _mark_cancelled(self, artifact_id: str) -> None:
        with self._lock:
            record = self._records.get(artifact_id)
            if record is None or record.entry.status in {
                ArtifactStatus.AVAILABLE,
                ArtifactStatus.FAILED,
                ArtifactStatus.EXPIRED,
            }:
                return
            record.entry = replace(
                record.entry,
                status=ArtifactStatus.CANCELLED,
                progress_stage="cancelled",
            )

    def _reusable_artifact_id(self, fingerprint: str) -> str | None:
        artifact_id = self._fingerprints.get(fingerprint)
        if artifact_id is None:
            return None
        record = self._records.get(artifact_id)
        if (
            record is None
            or record.entry.status is not ArtifactStatus.AVAILABLE
            or record.storage_id is None
        ):
            self._fingerprints.pop(fingerprint, None)
            return None
        try:
            self._storage.describe(record.storage_id)
        except (ArtifactExpiredError, ArtifactNotFoundError):
            self._mark_expired(artifact_id)
            self._fingerprints.pop(fingerprint, None)
            return None
        return artifact_id

    def _refresh_expired(self) -> None:
        available = [
            (artifact_id, record.storage_id)
            for artifact_id, record in self._records.items()
            if record.entry.status is ArtifactStatus.AVAILABLE
            and record.storage_id is not None
        ]
        for artifact_id, storage_id in available:
            try:
                self._storage.describe(storage_id)
            except (ArtifactExpiredError, ArtifactNotFoundError):
                self._mark_expired(artifact_id)

    def _mark_expired(self, artifact_id: str) -> None:
        with self._lock:
            record = self._records.get(artifact_id)
            if record is None:
                return
            record.entry = replace(
                record.entry,
                status=ArtifactStatus.EXPIRED,
                size_bytes=None,
                sha256=None,
            )
            if record.fingerprint is not None:
                self._fingerprints.pop(record.fingerprint, None)

    def _manifest(self, batch_id: str, job_id: str) -> ArtifactBatchManifest:
        return ArtifactBatchManifest(
            artifact_batch_id=batch_id,
            job_id=job_id,
            artifacts=tuple(
                self._records[artifact_id].entry
                for artifact_id in self._batch_artifacts[batch_id]
            ),
        )

    def _forget_future(self, future: Future[None]) -> None:
        with self._lock:
            self._futures.discard(future)


def _render_options(options: Mapping[str, object]) -> ArtifactRenderOptions:
    extra = {
        key: value
        for key, value in options.items()
        if key not in _STANDARD_OPTION_KEYS
    }
    return ArtifactRenderOptions(
        locale=options.get("locale", "en"),
        theme=options.get("theme", "light"),
        width=options.get("width", 1280),
        height=options.get("height", 720),
        font_family=options.get("font_family", "DejaVu Sans"),
        extra=extra,
    )


def _validate_declared_options(
    options: Mapping[str, object],
    schema: Mapping[str, object],
) -> None:
    """Validate the bounded JSON-schema subset used by artifact discovery."""

    if not schema:
        return
    properties = schema.get("properties", {})
    if not isinstance(properties, Mapping):
        raise ValueError("artifact options schema properties must be an object")
    if schema.get("additionalProperties") is False:
        unknown = sorted(set(options) - set(properties))
        if unknown:
            raise ValueError(
                "unsupported artifact option: " + ", ".join(unknown)
            )
    for key, value in options.items():
        rule = properties.get(key)
        if not isinstance(rule, Mapping):
            continue
        allowed = rule.get("enum")
        if isinstance(allowed, (list, tuple)) and value not in allowed:
            raise ValueError(f"artifact option '{key}' has an unsupported value")
        expected_type = rule.get("type")
        if expected_type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"artifact option '{key}' must be an integer")
            minimum = rule.get("minimum")
            maximum = rule.get("maximum")
            if isinstance(minimum, (int, float)) and value < minimum:
                raise ValueError(
                    f"artifact option '{key}' must be at least {minimum}"
                )
            if isinstance(maximum, (int, float)) and value > maximum:
                raise ValueError(
                    f"artifact option '{key}' must be at most {maximum}"
                )


def _fingerprint(
    job_id: str,
    request: ArtifactRequest,
    format_: ArtifactFormat,
    renderer_version: str,
) -> str:
    return json.dumps(
        {
            "job_id": job_id,
            "artifact_type": request.artifact_type,
            "format": format_.value,
            "options": request.options,
            "renderer_version": renderer_version,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def _artifact_error(code: ErrorCode, message: str, artifact_id: str) -> StructuredError:
    return StructuredError(
        code=code,
        message=message,
        context={"artifact_id": artifact_id},
    )


def _iso_timestamp(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat().replace(
        "+00:00", "Z"
    )
