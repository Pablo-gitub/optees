from __future__ import annotations

import asyncio
import json
import sys
from datetime import timedelta
from pathlib import Path
from time import monotonic, sleep

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from optees.composition.local_agent import (
    create_local_artifact_service,
    create_local_job_service,
    create_local_report_service,
)
from optees.interfaces.mcp.local_server import (
    LocalMcpToolFacade,
    create_mcp_server,
)


ROOT = Path(__file__).resolve().parents[3]
LP_PROBLEM = {
    "version": "1",
    "variables": [
        {"name": "product_a", "label": "Product A", "lb": 0, "ub": 4},
        {"name": "product_b", "label": "Product B", "lb": 0, "ub": 5},
    ],
    "objective": {
        "sense": "max",
        "coefficients": [30, 40],
        "offset": 0,
    },
    "constraints": [
        {"coefficients": [2, 4], "relation": "<=", "rhs": 18},
    ],
}
QP_PROBLEM = {
    "version": "1",
    "problem_type": "quadratic_programming",
    "variables": [
        {"name": "x1", "lb": None, "ub": None},
        {"name": "x2", "lb": None, "ub": None},
    ],
    "objective": {
        "sense": "min",
        "linear_coefficients": [-4.0, -6.0],
        "quadratic_matrix": [[2.0, 1.0], [1.0, 2.0]],
    },
    "constraints": [],
}
TOOL_NAMES = {
    "optees_list_capabilities",
    "optees_get_capability",
    "optees_validate_problem",
    "optees_create_job",
    "optees_get_job_status",
    "optees_get_job_result",
    "optees_cancel_job",
    "optees_validate_batch",
    "optees_create_batch",
    "optees_get_batch_status",
    "optees_get_batch_result",
    "optees_cancel_batch",
    "optees_list_result_artifacts",
    "optees_render_result_artifacts",
    "optees_get_artifact",
    "optees_download_artifact",
    "optees_cancel_artifact",
    "optees_compose_report",
    "optees_get_report_backends",
    "optees_cancel_report",
    "optees_get_report_status",
    "optees_get_report",
    "optees_download_report",
}


def test_facade_requires_descriptor_and_exact_validation_before_job():
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    try:
        before_descriptor = facade.validate_problem("lp.continuous", LP_PROBLEM)
        descriptor = facade.get_capability("lp.continuous")
        before_validation = facade.create_job("lp.continuous", LP_PROBLEM)
        validation = facade.validate_problem("lp.continuous", LP_PROBLEM)
        changed = facade.create_job(
            "lp.continuous",
            {**LP_PROBLEM, "constraints": []},
        )
        created = facade.create_job("lp.continuous", LP_PROBLEM)
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert before_descriptor["error"]["code"] == "capability_not_inspected"
    assert descriptor["capability"]["input_schema"]["type"] == "object"
    assert before_validation["error"]["code"] == "problem_not_validated"
    assert validation["validation"]["valid"] is True
    assert changed["error"]["code"] == "problem_not_validated"
    assert created["job"]["capability_id"] == "lp.continuous"


def test_facade_completes_qp_with_frozen_problem_and_result_shapes():
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    try:
        descriptor = facade.get_capability("qp.continuous")
        validation = facade.validate_problem("qp.continuous", QP_PROBLEM)
        created = facade.create_job("qp.continuous", QP_PROBLEM)
        job_id = created["job"]["job_id"]
        _wait_for_job(service, job_id)
        result = facade.get_job_result(job_id)["result"]
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert descriptor["capability"]["input_schema"]["required"] == [
        "version",
        "problem_type",
        "variables",
        "objective",
        "constraints",
    ]
    assert validation["validation"]["valid"] is True
    assert result["termination_reason"] == "completed"
    assert result["result"]["objective_sense"] == "min"
    assert [item["name"] for item in result["result"]["variables"]] == ["x1", "x2"]


def test_mcp_tools_publish_expected_names_and_problem_schemas():
    async def inspect_tools():
        service = create_local_job_service()
        artifacts = create_local_artifact_service(service)
        reports = create_local_report_service(service, artifacts)
        try:
            server = create_mcp_server(service, artifacts, reports)
            return await server.list_tools(), await server.list_resource_templates()
        finally:
            reports.close()
            artifacts.close()
            service.shutdown(wait=True, cancel_pending=True)

    tools, templates = asyncio.run(inspect_tools())
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == TOOL_NAMES
    validate_schema = by_name["optees_validate_problem"].inputSchema
    assert set(validate_schema["required"]) == {"capability_id", "problem"}
    assert validate_schema["properties"]["problem"]["type"] == "object"
    assert by_name["optees_get_job_result"].outputSchema["type"] == "object"
    batch_schema = by_name["optees_validate_batch"].inputSchema
    assert batch_schema["properties"]["items"]["maxItems"] == 32
    render_schema = by_name["optees_render_result_artifacts"].inputSchema
    assert render_schema["properties"]["requests"]["maxItems"] == 8
    assert [str(item.uriTemplate) for item in templates] == [
        "optees-artifact://{artifact_id}",
        "optees-report://{report_id}",
    ]


def test_facade_composes_metadata_only_report_with_explicit_resource_read():
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    reports = create_local_report_service(jobs, artifacts)
    facade = LocalMcpToolFacade(jobs, artifacts, reports)
    try:
        composed = facade.compose_report(
            {
                "contract_version": "1",
                "format": "markdown",
                "locale": "en",
                "title": "MCP report",
                "sections": [
                    {
                        "section_id": "summary",
                        "heading": "Summary",
                        "blocks": [{"type": "markdown", "content": "Result summary."}],
                    }
                ],
            }
        )
        assert composed["ok"] is True
        report_id = composed["report"]["report_id"]
        deadline = monotonic() + 5
        metadata = None
        while monotonic() < deadline:
            metadata = facade.get_report(report_id)
            if metadata.get("resource_uri"):
                break
            sleep(0.01)

        assert metadata is not None
        assert metadata["content_included"] is False
        assert metadata["resource_uri"] == f"optees-report://{report_id}"
        assert b"Optees" in facade.read_report_resource(report_id)
    finally:
        reports.close()
        artifacts.close()
        jobs.shutdown(wait=True, cancel_pending=True)


def test_facade_renders_metadata_only_and_requires_explicit_resource_read():
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    facade = LocalMcpToolFacade(jobs, artifacts)
    try:
        facade.get_capability("lp.continuous")
        validated = facade.validate_problem("lp.continuous", LP_PROBLEM)
        assert validated["validation"]["valid"] is True
        created = facade.create_job("lp.continuous", LP_PROBLEM)
        job_id = created["job"]["job_id"]
        _wait_for_job(jobs, job_id)

        discovery = facade.list_result_artifacts(job_id)
        artifact_types = {item["artifact_type"] for item in discovery["available_artifacts"]}
        assert "solution_table" in artifact_types
        rendered = facade.render_result_artifacts(
            job_id,
            [{"artifact_type": "solution_table", "formats": ["json"]}],
        )
        assert rendered["ok"] is True
        entry = _wait_for_artifact(artifacts, job_id)

        metadata = facade.get_artifact(entry["artifact_id"])
        assert metadata["content_included"] is False
        assert "content" not in metadata
        assert "path" not in str(metadata).lower()
        assert metadata["resource_uri"] == (f"optees-artifact://{entry['artifact_id']}")
        content = facade.read_artifact_resource(entry["artifact_id"])
        assert json.loads(content)["artifact_type"] == "solution_table"

        traversal = facade.get_artifact("../../etc/passwd")
        assert traversal["ok"] is False
        assert "path" not in str(traversal).lower()
    finally:
        artifacts.close()
        jobs.shutdown(wait=True, cancel_pending=True)


def test_mcp_artifact_resource_preserves_the_rendered_media_type():
    jobs = create_local_job_service()
    artifacts = create_local_artifact_service(jobs)
    facade = LocalMcpToolFacade(jobs, artifacts)
    try:
        facade.get_capability("lp.continuous")
        facade.validate_problem("lp.continuous", LP_PROBLEM)
        created = facade.create_job("lp.continuous", LP_PROBLEM)
        job_id = created["job"]["job_id"]
        _wait_for_job(jobs, job_id)
        facade.render_result_artifacts(
            job_id,
            [{"artifact_type": "feasible_region", "formats": ["svg"]}],
        )
        entry = _wait_for_artifact(artifacts, job_id)
        uri = f"optees-artifact://{entry['artifact_id']}"

        server = create_mcp_server(jobs, artifacts)
        resource = asyncio.run(server.read_resource(uri))

        assert len(resource) == 1
        assert resource[0].mime_type == "image/svg+xml"
        assert resource[0].content.startswith(b"<?xml")
    finally:
        artifacts.close()
        jobs.shutdown(wait=True, cancel_pending=True)


def test_facade_requires_inspection_and_exact_validation_before_batch():
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    items = [
        {
            "client_item_id": f"scenario-{index}",
            "capability_id": "lp.continuous",
            "problem": LP_PROBLEM,
        }
        for index in range(1, 3)
    ]
    try:
        before_descriptor = facade.validate_batch("1", items)
        facade.get_capability("lp.continuous")
        before_validation = facade.create_batch("1", items)
        validation = facade.validate_batch("1", items)
        changed = facade.create_batch(
            "1",
            [
                items[0],
                {
                    **items[1],
                    "problem": {**LP_PROBLEM, "constraints": []},
                },
            ],
        )
        created = facade.create_batch("1", items)
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert before_descriptor["error"]["code"] == "capability_not_inspected"
    assert before_validation["error"]["code"] == "batch_not_validated"
    assert validation["validation"]["valid"] is True
    assert changed["error"]["code"] == "batch_not_validated"
    assert created["batch"]["item_count"] == 2


def test_stdio_mcp_client_completes_local_lp_workflow():
    asyncio.run(_run_stdio_lp_workflow())


def test_stdio_mcp_client_completes_local_forecasting_workflow():
    asyncio.run(_run_stdio_forecasting_workflow())


async def _run_stdio_forecasting_workflow() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "optees.mcp_server"],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    timeout = timedelta(seconds=20)
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            inspected = await session.call_tool(
                "optees_get_capability",
                {"capability_id": "ml.forecasting.univariate"},
                read_timeout_seconds=timeout,
            )
            capability = _structured(inspected)["capability"]
            problem = capability["example_problem"]
            validated = await session.call_tool(
                "optees_validate_problem",
                {
                    "capability_id": "ml.forecasting.univariate",
                    "problem": problem,
                },
                read_timeout_seconds=timeout,
            )
            assert _structured(validated)["validation"]["valid"] is True
            created = await session.call_tool(
                "optees_create_job",
                {
                    "capability_id": "ml.forecasting.univariate",
                    "problem": problem,
                },
                read_timeout_seconds=timeout,
            )
            job_id = _structured(created)["job"]["job_id"]

            for _ in range(100):
                status = await session.call_tool(
                    "optees_get_job_status",
                    {"job_id": job_id},
                    read_timeout_seconds=timeout,
                )
                job = _structured(status)["job"]
                if job["job_status"] in {"completed", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.01)
            assert job["job_status"] == "completed"

            result = await session.call_tool(
                "optees_get_job_result",
                {"job_id": job_id},
                read_timeout_seconds=timeout,
            )
            envelope = _structured(result)["result"]
            assert envelope["mathematical_status"] == "feasible"
            assert envelope["validation"]["status"] == "verified"
            assert envelope["result"] == capability["example_result"]


async def _run_stdio_lp_workflow() -> None:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "optees.mcp_server"],
        cwd=ROOT,
        env={"PYTHONPATH": str(ROOT / "src")},
    )
    timeout = timedelta(seconds=20)
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == TOOL_NAMES

            listed = await session.call_tool(
                "optees_list_capabilities",
                {},
                read_timeout_seconds=timeout,
            )
            assert _structured(listed)["ok"] is True
            await session.call_tool(
                "optees_get_capability",
                {"capability_id": "lp.continuous"},
                read_timeout_seconds=timeout,
            )
            validated = await session.call_tool(
                "optees_validate_problem",
                {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
                read_timeout_seconds=timeout,
            )
            assert _structured(validated)["validation"]["valid"] is True
            created = await session.call_tool(
                "optees_create_job",
                {"capability_id": "lp.continuous", "problem": LP_PROBLEM},
                read_timeout_seconds=timeout,
            )
            job_id = _structured(created)["job"]["job_id"]

            for _ in range(100):
                status = await session.call_tool(
                    "optees_get_job_status",
                    {"job_id": job_id},
                    read_timeout_seconds=timeout,
                )
                job = _structured(status)["job"]
                if job["job_status"] in {"completed", "failed", "cancelled"}:
                    break
                await asyncio.sleep(0.01)
            assert job["job_status"] == "completed"

            result = await session.call_tool(
                "optees_get_job_result",
                {"job_id": job_id},
                read_timeout_seconds=timeout,
            )
            envelope = _structured(result)["result"]
            assert envelope["mathematical_status"] == "optimal"
            assert envelope["validation"]["status"] == "verified"
            assert envelope["result"]["objective"] == 220.0

            discovered = await session.call_tool(
                "optees_list_result_artifacts",
                {"job_id": job_id},
                read_timeout_seconds=timeout,
            )
            available = _structured(discovered)["available_artifacts"]
            assert any(item["artifact_type"] == "solution_table" for item in available)
            requested = await session.call_tool(
                "optees_render_result_artifacts",
                {
                    "job_id": job_id,
                    "requests": [
                        {
                            "artifact_type": "feasible_region",
                            "formats": ["svg"],
                        }
                    ],
                },
                read_timeout_seconds=timeout,
            )
            assert _structured(requested)["content_policy"]["embedded_by_default"] is False

            artifact_entry = None
            for _ in range(100):
                listed_artifacts = await session.call_tool(
                    "optees_list_result_artifacts",
                    {"job_id": job_id},
                    read_timeout_seconds=timeout,
                )
                batches = _structured(listed_artifacts)["artifact_batches"]
                if batches:
                    candidate = batches[-1]["artifacts"][0]
                    if candidate["status"] == "available":
                        artifact_entry = candidate
                        break
                await asyncio.sleep(0.01)
            assert artifact_entry is not None
            metadata = await session.call_tool(
                "optees_get_artifact",
                {"artifact_id": artifact_entry["artifact_id"]},
                read_timeout_seconds=timeout,
            )
            artifact_metadata = _structured(metadata)
            assert artifact_metadata["content_included"] is False
            assert "content" not in artifact_metadata

            resource = await session.read_resource(artifact_metadata["resource_uri"])
            assert len(resource.contents) == 1
            assert resource.contents[0].blob is not None
            assert resource.contents[0].mimeType == "image/svg+xml"


def _structured(result) -> dict[str, object]:
    assert result.isError is False
    assert isinstance(result.structuredContent, dict)
    return result.structuredContent


def _wait_for_job(service, job_id: str) -> None:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        snapshot = service.get(job_id)
        if snapshot.job_status.value == "completed":
            return
        sleep(0.01)
    raise AssertionError("job did not complete")


def _wait_for_artifact(service, job_id: str) -> dict[str, object]:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        batches = service.list_for_job(job_id)
        if batches:
            entry = batches[-1].artifacts[0]
            if entry.status.value == "available":
                return entry.to_dict()
        sleep(0.01)
    raise AssertionError("artifact did not become available")
