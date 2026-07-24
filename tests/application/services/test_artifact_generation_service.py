from __future__ import annotations

from time import monotonic, sleep

from optees.application.contracts.artifact import (
    ArtifactBatchManifest,
    ArtifactBatchRequest,
    ArtifactFormat,
    ArtifactRequest,
    ArtifactStatus,
    AvailableArtifact,
)
from optees.application.contracts.artifact_rendering import (
    ArtifactRenderContext,
    RenderedArtifact,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.application.contracts.execution import MathematicalStatus
from optees.application.contracts.job import JobSnapshot
from optees.application.services.artifact_generation_service import (
    ArtifactGenerationService,
    ArtifactRendererRegistration,
)
from optees.composition.local_agent import create_local_job_service
from optees.data.adapters.artifacts.local_artifact_store import LocalArtifactStore


class CsvRenderer:
    renderer_version = "test-1"

    def __init__(self, *, delay: float = 0.0, fail: bool = False) -> None:
        self.delay = delay
        self.fail = fail
        self.calls = 0

    def render(self, context: ArtifactRenderContext) -> RenderedArtifact:
        self.calls += 1
        if self.delay:
            sleep(self.delay)
        if self.fail:
            raise RuntimeError("private renderer detail")
        assert context.capability_id == "lp.continuous"
        return RenderedArtifact("text/csv", b"variable,value\nx,1\n")


def _lp_payload() -> dict:
    return {
        "version": "1",
        "variables": [{"name": "x", "label": "", "lb": 0, "ub": 1}],
        "objective": {"sense": "max", "coefficients": [1], "offset": 0},
        "constraints": [],
    }


def _registration(renderer: CsvRenderer) -> ArtifactRendererRegistration:
    return ArtifactRendererRegistration(
        capability_id="lp.continuous",
        descriptor=AvailableArtifact(
            artifact_type="solution_table",
            title="Solution table",
            formats=(ArtifactFormat.CSV,),
            required_mathematical_statuses=(MathematicalStatus.OPTIMAL,),
        ),
        renderer=renderer,
        media_types={ArtifactFormat.CSV: "text/csv"},
    )


def _request(**options) -> ArtifactBatchRequest:
    return ArtifactBatchRequest(
        (
            ArtifactRequest(
                "solution_table",
                (ArtifactFormat.CSV,),
                options,
            ),
        )
    )


def _completed_job(service) -> str:
    submitted = service.submit("lp.continuous", _lp_payload())
    assert isinstance(submitted, JobSnapshot)
    deadline = monotonic() + 5
    while monotonic() < deadline:
        snapshot = service.get(submitted.job_id)
        assert isinstance(snapshot, JobSnapshot)
        if snapshot.job_status.value == "completed":
            return submitted.job_id
        sleep(0.01)
    raise AssertionError("LP job did not complete")


def _terminal_manifest(
    service: ArtifactGenerationService,
    job_id: str,
) -> ArtifactBatchManifest:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        outcome = service.list_for_job(job_id)
        assert not isinstance(outcome, StructuredError)
        manifest = outcome[-1]
        if all(
            item.status
            in {ArtifactStatus.AVAILABLE, ArtifactStatus.FAILED, ArtifactStatus.EXPIRED}
            for item in manifest.artifacts
        ):
            return manifest
        sleep(0.01)
    raise AssertionError("artifact generation did not finish")


def test_service_renders_downloads_and_reuses_equivalent_available_artifact(tmp_path):
    jobs = create_local_job_service()
    renderer = CsvRenderer()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(_registration(renderer),),
    )
    try:
        job_id = _completed_job(jobs)
        first = artifacts.submit(job_id, _request(locale="it"))
        assert isinstance(first, ArtifactBatchManifest)
        completed = _terminal_manifest(artifacts, job_id)
        entry = completed.artifacts[0]

        assert entry.status is ArtifactStatus.AVAILABLE
        assert entry.sha256 is not None
        downloaded = artifacts.download(entry.artifact_id)
        assert not isinstance(downloaded, StructuredError)
        assert downloaded.content == b"variable,value\nx,1\n"

        second = artifacts.submit(job_id, _request(locale="it"))
        assert isinstance(second, ArtifactBatchManifest)
        assert second.artifacts[0].artifact_id == entry.artifact_id
        assert renderer.calls == 1
    finally:
        artifacts.close()
        jobs.shutdown()


def test_service_rejects_invalid_options_before_creating_a_manifest(tmp_path):
    jobs = create_local_job_service()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(_registration(CsvRenderer()),),
    )
    try:
        job_id = _completed_job(jobs)
        outcome = artifacts.submit(job_id, _request(locale="fr"))

        assert isinstance(outcome, StructuredError)
        assert outcome.code is ErrorCode.ARTIFACT_REQUEST_INVALID
        assert artifacts.list_for_job(job_id) == ()
    finally:
        artifacts.close()
        jobs.shutdown()


def test_renderer_timeout_becomes_sanitized_failed_manifest_entry(tmp_path):
    jobs = create_local_job_service()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(_registration(CsvRenderer(delay=0.05)),),
        render_timeout_seconds=0.01,
    )
    try:
        job_id = _completed_job(jobs)
        submitted = artifacts.submit(job_id, _request())
        assert isinstance(submitted, ArtifactBatchManifest)
        failed = _terminal_manifest(artifacts, job_id).artifacts[0]

        assert failed.status is ArtifactStatus.FAILED
        assert failed.error is not None
        assert failed.error.code is ErrorCode.ARTIFACT_RENDER_FAILED
        assert "timeout" in failed.error.message
        download = artifacts.download(failed.artifact_id)
        assert isinstance(download, StructuredError)
        assert download.code is ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE
    finally:
        artifacts.close()
        jobs.shutdown()


def test_renderer_exception_does_not_expose_private_backend_details(tmp_path):
    jobs = create_local_job_service()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(_registration(CsvRenderer(fail=True)),),
    )
    try:
        job_id = _completed_job(jobs)
        artifacts.submit(job_id, _request())
        failed = _terminal_manifest(artifacts, job_id).artifacts[0]

        assert failed.error is not None
        assert failed.error.code is ErrorCode.ARTIFACT_RENDER_FAILED
        assert "private renderer detail" not in str(failed.error.to_dict())
    finally:
        artifacts.close()
        jobs.shutdown()


def test_rendering_artifact_can_be_cancelled_without_late_publication(tmp_path):
    jobs = create_local_job_service()
    artifacts = ArtifactGenerationService(
        jobs,
        LocalArtifactStore(parent_directory=tmp_path),
        registrations=(_registration(CsvRenderer(delay=0.15)),),
    )
    try:
        job_id = _completed_job(jobs)
        submitted = artifacts.submit(job_id, _request())
        assert isinstance(submitted, ArtifactBatchManifest)
        artifact_id = submitted.artifacts[0].artifact_id
        deadline = monotonic() + 2
        while monotonic() < deadline:
            entry = artifacts.manifest_entry(artifact_id)
            assert not isinstance(entry, StructuredError)
            if entry.status is ArtifactStatus.RENDERING:
                break
            sleep(0.005)

        cancelled = artifacts.cancel(artifact_id)
        assert not isinstance(cancelled, StructuredError)
        assert cancelled.status is ArtifactStatus.CANCELLED
        assert cancelled.progress_stage == "cancelled"
        sleep(0.2)

        final = artifacts.manifest_entry(artifact_id)
        assert not isinstance(final, StructuredError)
        assert final.status is ArtifactStatus.CANCELLED
        unavailable = artifacts.download(artifact_id)
        assert isinstance(unavailable, StructuredError)
        assert unavailable.code is ErrorCode.ARTIFACT_RESULT_NOT_AVAILABLE
    finally:
        artifacts.close()
        jobs.shutdown()
