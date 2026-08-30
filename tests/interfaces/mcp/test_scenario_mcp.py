from __future__ import annotations

from time import monotonic, sleep

import pytest

from optees.composition.local_agent import create_local_job_service
from optees.interfaces.mcp.local_server import LocalMcpToolFacade


def _wait_for_job(service, job_id: str) -> None:
    deadline = monotonic() + 5
    while monotonic() < deadline:
        snapshot = service.get(job_id)
        if snapshot.job_status.value == "completed":
            return
        sleep(0.01)
    raise AssertionError("job did not complete")


def _loss_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "minimize_maximum_loss",
        "variables": [
            {"name": "x1", "lower_bound": 0.0, "upper_bound": 10.0},
            {"name": "x2", "lower_bound": 0.0, "upper_bound": 10.0},
        ],
        "scenarios": [
            {"id": "s1", "coefficients": [2.0, -1.0], "offset": 5.0},
            {"id": "s2", "coefficients": [-1.0, 3.0], "offset": 2.0},
            {"id": "s3", "coefficients": [1.0, 1.0], "offset": -4.0},
        ],
        "shared_constraints": [
            {
                "name": "budget",
                "coefficients": [1.0, 1.0],
                "relation": "=",
                "rhs": 10.0,
            }
        ],
    }


def _reward_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "maximize_minimum_reward",
        "variables": [
            {"name": "y1", "lower_bound": 0.0, "upper_bound": 5.0},
            {"name": "y2", "lower_bound": 0.0, "upper_bound": 5.0},
        ],
        "scenarios": [
            {"id": "sA", "coefficients": [4.0, -2.0], "offset": -10.0},
            {"id": "sB", "coefficients": [-2.0, 5.0], "offset": -8.0},
        ],
        "shared_constraints": [{"coefficients": [1.0, 1.0], "relation": "<=", "rhs": 6.0}],
    }


def test_mcp_facade_solves_scenario_min_max_loss() -> None:
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    try:
        descriptor = facade.get_capability("scenario.linear.min_max_loss")
        assert descriptor["capability"]["problem_type"] == "linear_scenario"
        assert descriptor["capability"]["problem_schema_version"] == "1"

        validation = facade.validate_problem("scenario.linear.min_max_loss", _loss_payload())
        assert validation["validation"]["valid"] is True

        created = facade.create_job("scenario.linear.min_max_loss", _loss_payload())
        job_id = created["job"]["job_id"]
        _wait_for_job(service, job_id)
        result = facade.get_job_result(job_id)["result"]
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert result["mathematical_status"] == "optimal"
    assert result["result"]["orientation"] == "minimize_maximum_loss"
    assert result["result"]["guaranteed_value"] == pytest.approx(76.0 / 7.0)
    assert result["result"]["binding_scenario_ids"] == ["s1", "s2"]
    assert result["validation"]["status"] == "verified"


def test_mcp_facade_solves_scenario_max_min_reward() -> None:
    service = create_local_job_service()
    facade = LocalMcpToolFacade(service)
    try:
        descriptor = facade.get_capability("scenario.linear.max_min_reward")
        assert descriptor["capability"]["problem_type"] == "linear_scenario"

        validation = facade.validate_problem("scenario.linear.max_min_reward", _reward_payload())
        assert validation["validation"]["valid"] is True

        created = facade.create_job("scenario.linear.max_min_reward", _reward_payload())
        job_id = created["job"]["job_id"]
        _wait_for_job(service, job_id)
        result = facade.get_job_result(job_id)["result"]
    finally:
        service.shutdown(wait=True, cancel_pending=True)

    assert result["mathematical_status"] == "optimal"
    assert result["result"]["orientation"] == "maximize_minimum_reward"
    assert result["result"]["guaranteed_value"] == pytest.approx(-22.0 / 13.0)
    assert result["result"]["binding_scenario_ids"] == ["sA", "sB"]
    assert result["validation"]["status"] == "verified"
