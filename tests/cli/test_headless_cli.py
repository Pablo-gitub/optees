from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from optees.cli import ExitCode


ROOT = Path(__file__).resolve().parents[2]


def _payload() -> dict:
    return {
        "version": "1",
        "variables": [
            {"name": "x", "label": "", "lb": 0, "ub": None},
            {"name": "y", "label": "", "lb": 0, "ub": None},
        ],
        "objective": {
            "sense": "max",
            "coefficients": [3, 2],
            "offset": 0,
        },
        "constraints": [
            {"coefficients": [1, 1], "relation": "<=", "rhs": 4},
            {"coefficients": [1, 0], "relation": "<=", "rhs": 2},
        ],
    }


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


def test_list_capabilities_emits_one_versioned_json_document():
    result = _run("list-capabilities")

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert result.stderr == ""
    assert payload["contract_version"] == "1"
    assert {item["id"] for item in payload["capabilities"]} == {
        "lp.continuous",
        "knapsack.zero_one",
        "knapsack.bounded",
        "knapsack.unbounded",
        "knapsack.fractional",
        "knapsack.multi_dimensional",
        "milp.linear",
    }


def test_solve_zero_one_knapsack_through_cli():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "zero_one",
        "capacity": 5,
        "items": [
            {"name": "A", "value": 6, "weight": 2},
            {"name": "B", "value": 10, "weight": 4},
            {"name": "C", "value": 5, "weight": 3},
        ],
    }

    result = _run("solve", "knapsack.zero_one", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["selected_indices"] == [0, 2]
    assert output["result"]["objective"] == pytest.approx(11.0)


def test_solve_bounded_knapsack_through_cli():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "bounded",
        "capacity": 10,
        "items": [
            {"name": "A", "value": 6, "weight": 2, "max_quantity": 3},
            {"name": "B", "value": 10, "weight": 3, "max_quantity": 2},
        ],
    }

    result = _run("solve", "knapsack.bounded", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["quantities"] == [2, 2]
    assert output["result"]["objective"] == pytest.approx(32.0)


def test_solve_unbounded_knapsack_through_cli():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "unbounded",
        "capacity": 8,
        "items": [
            {"name": "A", "value": 10, "weight": 1},
            {"name": "B", "value": 30, "weight": 2},
            {"name": "C", "value": 44, "weight": 3},
        ],
    }

    result = _run("solve", "knapsack.unbounded", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["quantities"] == [0, 4, 0]
    assert output["result"]["objective"] == pytest.approx(120.0)


def test_mathematically_unbounded_knapsack_has_dedicated_exit_code():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "unbounded",
        "capacity": 8,
        "items": [{"name": "Free value", "value": 1, "weight": 0}],
    }

    result = _run("solve", "knapsack.unbounded", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.UNBOUNDED
    assert output["mathematical_status"] == "unbounded"
    assert output["result"]["objective"] is None


def test_solve_fractional_knapsack_through_cli():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "fractional",
        "capacity": 50,
        "items": [
            {"name": "A", "value": 60, "weight": 10},
            {"name": "B", "value": 100, "weight": 20},
            {"name": "C", "value": 120, "weight": 30},
        ],
    }

    result = _run("solve", "knapsack.fractional", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["fractions"] == pytest.approx([1.0, 1.0, 2 / 3])
    assert output["result"]["objective"] == pytest.approx(240.0)


def test_solve_binary_multi_dimensional_knapsack_through_cli():
    payload = {
        "version": "1",
        "problem_type": "knapsack",
        "variant": "multi_dimensional",
        "domain": "zero_one",
        "resources": [
            {"name": "weight", "capacity": 10},
            {"name": "volume", "capacity": 6},
        ],
        "items": [
            {"name": "A", "value": 8, "usage": [4, 1.5]},
            {"name": "B", "value": 9, "usage": [5, 2]},
            {"name": "C", "value": 14, "usage": [6, 4.5]},
            {"name": "D", "value": 7, "usage": [3, 2]},
        ],
    }

    result = _run("solve", "knapsack.multi_dimensional", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["objective"] == pytest.approx(22.0)
    assert output["result"]["selected_indices"] == [0, 2]


def test_solve_milp_through_cli():
    pytest.importorskip("ortools")
    payload = {
        "version": "1",
        "variables": [
            {"name": "x", "lb": 0, "ub": 4, "integrality": "I"},
            {"name": "open", "lb": 0, "ub": 1, "integrality": "B"},
        ],
        "objective": {"sense": "max", "coefficients": [3, -1]},
        "constraints": [
            {"coefficients": [1, -4], "relation": "<=", "rhs": 0},
        ],
    }

    result = _run("solve", "milp.linear", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["objective"] == pytest.approx(11.0)


def test_validate_accepts_problem_from_stdin_without_solving():
    result = _run("validate", "lp.continuous", stdin=json.dumps(_payload()))

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert result.stderr == ""
    assert payload["valid"] is True
    assert payload["problem_schema_version"] == "1"


def test_validate_accepts_explicit_json_file(tmp_path: Path):
    path = tmp_path / "problem.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")

    result = _run("validate", "lp.continuous", str(path))

    assert result.returncode == ExitCode.SUCCESS
    assert _stdout_json(result)["valid"] is True


def test_solve_accepts_stdin_and_emits_versioned_execution_envelope():
    result = _run("solve", "lp.continuous", stdin=json.dumps(_payload()))

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert result.stderr == ""
    assert payload["capability_id"] == "lp.continuous"
    assert payload["mathematical_status"] == "optimal"
    assert payload["result"]["objective"] == pytest.approx(10.0)
    assert payload["diagnostics"]["backend_id"] == "scipy.highs"


def test_invalid_json_returns_contract_error_and_safe_stderr():
    confidential = "CONFIDENTIAL_ORDER_428"
    result = _run("solve", "lp.continuous", stdin=f'{{"{confidential}":')

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.INVALID_INPUT
    assert payload["error"]["code"] == "invalid_request"
    assert "line 1" in payload["error"]["details"][0]["message"]
    assert confidential not in result.stderr
    assert "not valid JSON" in result.stderr


def test_missing_file_returns_invalid_input_without_exposing_path_on_stderr():
    secret_path = "/private/customer/acme/orders.json"
    result = _run("validate", "lp.continuous", secret_path)

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.INVALID_INPUT
    assert payload["error"]["code"] == "invalid_request"
    assert secret_path not in result.stderr


def test_unknown_capability_has_stable_unavailable_exit_code():
    result = _run("solve", "missing.capability", stdin="{}")

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.CAPABILITY_UNAVAILABLE
    assert payload["error"]["code"] == "capability_not_found"


def test_infeasible_lp_has_result_envelope_and_dedicated_exit_code():
    payload = _payload()
    payload["variables"] = [{"name": "x", "label": "", "lb": 0, "ub": None}]
    payload["objective"]["coefficients"] = [1]
    payload["constraints"] = [
        {"coefficients": [1], "relation": ">=", "rhs": 1},
        {"coefficients": [1], "relation": "<=", "rhs": 0},
    ]

    result = _run("solve", "lp.continuous", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.INFEASIBLE
    assert output["job_status"] == "completed"
    assert output["mathematical_status"] == "infeasible"


def test_unbounded_lp_has_dedicated_exit_code():
    payload = _payload()
    payload["variables"] = [{"name": "x", "label": "", "lb": 0, "ub": None}]
    payload["objective"]["coefficients"] = [1]
    payload["constraints"] = []

    result = _run("solve", "lp.continuous", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.UNBOUNDED
    assert output["mathematical_status"] == "unbounded"


def test_invalid_cli_arguments_are_returned_as_json_error():
    result = _run("solve")

    payload = _stdout_json(result)
    assert result.returncode == ExitCode.INVALID_INPUT
    assert payload["error"]["code"] == "invalid_request"


def test_importing_cli_does_not_import_qt_or_presentation():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    script = (
        "import sys; import optees.cli; "
        "assert 'PySide6' not in sys.modules; "
        "assert not any(n.startswith('optees.presentation') for n in sys.modules)"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
