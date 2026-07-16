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
    assert payload["capabilities"][0]["id"] == "lp.continuous"


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
