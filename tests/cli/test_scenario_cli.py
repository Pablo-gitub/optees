from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from optees.cli import ExitCode

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, stdin: str | None = None) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "optees.cli", *args],
        cwd=ROOT,
        env=env,
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )


def _stdout_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.stdout.count("\n") == 1
    return json.loads(result.stdout)


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
            {"name": "budget", "coefficients": [1.0, 1.0], "relation": "=", "rhs": 10.0}
        ],
    }


def _reward_payload() -> dict:
    return {
        "version": "1",
        "problem_type": "linear_scenario",
        "orientation": "maximize_minimum_reward",
        "variables": [
            {"name": "x1", "lower_bound": 0.0, "upper_bound": 5.0},
            {"name": "x2", "lower_bound": 0.0, "upper_bound": 5.0},
        ],
        "scenarios": [
            {"id": "sA", "coefficients": [4.0, -2.0], "offset": -10.0},
            {"id": "sB", "coefficients": [-2.0, 5.0], "offset": -8.0},
            {"id": "sC", "coefficients": [1.0, 1.0], "offset": -5.0},
        ],
        "shared_constraints": [{"coefficients": [1.0, 1.0], "relation": "<=", "rhs": 6.0}],
    }


def test_cli_list_capabilities_contains_scenario_capabilities() -> None:
    result = _run("list-capabilities")
    assert result.returncode == ExitCode.SUCCESS
    payload = _stdout_json(result)
    cap_ids = [c["id"] for c in payload["capabilities"]]
    assert "scenario.linear.min_max_loss" in cap_ids
    assert "scenario.linear.max_min_reward" in cap_ids


def test_cli_validate_scenario_min_max_loss() -> None:
    problem = _loss_payload()
    result = _run("validate", "scenario.linear.min_max_loss", stdin=json.dumps(problem))
    assert result.returncode == ExitCode.SUCCESS
    payload = _stdout_json(result)
    assert payload["capability_id"] == "scenario.linear.min_max_loss"
    assert payload["available"] is True


def test_cli_validate_rejects_cross_orientation() -> None:
    problem = _reward_payload()
    result = _run("validate", "scenario.linear.min_max_loss", stdin=json.dumps(problem))
    assert result.returncode == ExitCode.INVALID_INPUT
    payload = _stdout_json(result)
    assert payload["error"]["code"] == "validation_failed"
    assert payload["error"]["details"][0]["code"] == "scenario.orientation_mismatch"


def test_cli_solve_continuous_loss_scenario() -> None:
    problem = _loss_payload()
    result = _run("solve", "scenario.linear.min_max_loss", stdin=json.dumps(problem))
    assert result.returncode == ExitCode.SUCCESS
    payload = _stdout_json(result)
    assert payload["capability_id"] == "scenario.linear.min_max_loss"
    assert payload["job_status"] == "completed"
    assert payload["mathematical_status"] == "optimal"
    assert payload["result"]["orientation"] == "minimize_maximum_loss"
    assert payload["result"]["guaranteed_value"] == pytest.approx(76.0 / 7.0)
    assert payload["result"]["binding_scenario_ids"] == ["s1", "s2"]
    assert payload["validation"]["status"] == "verified"


def test_cli_solve_continuous_reward_scenario() -> None:
    problem = _reward_payload()
    result = _run("solve", "scenario.linear.max_min_reward", stdin=json.dumps(problem))
    assert result.returncode == ExitCode.SUCCESS
    payload = _stdout_json(result)
    assert payload["capability_id"] == "scenario.linear.max_min_reward"
    assert payload["job_status"] == "completed"
    assert payload["mathematical_status"] == "optimal"
    assert payload["result"]["orientation"] == "maximize_minimum_reward"
    assert payload["result"]["guaranteed_value"] == pytest.approx(-22.0 / 13.0)
    assert payload["result"]["binding_scenario_ids"] == ["sA", "sB"]
    assert payload["validation"]["status"] == "verified"
