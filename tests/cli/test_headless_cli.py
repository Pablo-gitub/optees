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
        "qp.continuous",
        "knapsack.zero_one",
        "knapsack.bounded",
        "knapsack.unbounded",
        "knapsack.fractional",
        "knapsack.multi_dimensional",
        "milp.linear",
        "graph.shortest_path.dijkstra",
        "nlp.continuous_local",
        "ml.regression.linear",
        "ml.classification.binary_logistic",
        "ml.forecasting.univariate",
        "packing.single_container_3d",
        "scenario.linear.min_max_loss",
        "scenario.linear.max_min_reward",
    }


def test_solve_forecasting_descriptor_example_through_cli():
    listed = _stdout_json(_run("list-capabilities"))
    descriptor = next(
        item for item in listed["capabilities"] if item["id"] == "ml.forecasting.univariate"
    )

    result = _run(
        "solve",
        "ml.forecasting.univariate",
        stdin=json.dumps(descriptor["example_problem"]),
    )

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "feasible"
    assert output["validation"]["status"] == "verified"
    assert output["result"] == descriptor["example_result"]


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


def test_solve_dijkstra_shortest_path_through_cli():
    payload = {
        "version": "1",
        "problem_type": "shortest_path",
        "directed": True,
        "vertices": [{"id": node} for node in ["A", "B", "C", "D"]],
        "edges": [
            {"from": "A", "to": "B", "weight": 4},
            {"from": "A", "to": "C", "weight": 1},
            {"from": "C", "to": "B", "weight": 2},
            {"from": "B", "to": "D", "weight": 1},
        ],
        "source": "A",
        "destination": "D",
    }

    result = _run(
        "solve",
        "graph.shortest_path.dijkstra",
        stdin=json.dumps(payload),
    )

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["distance"] == pytest.approx(4.0)
    assert output["result"]["path"] == ["A", "C", "B", "D"]


def test_unreachable_dijkstra_path_has_infeasible_exit_code():
    payload = {
        "version": "1",
        "problem_type": "shortest_path",
        "directed": True,
        "vertices": [{"id": "A"}, {"id": "B"}],
        "edges": [],
        "source": "A",
        "destination": "B",
    }

    result = _run(
        "solve",
        "graph.shortest_path.dijkstra",
        stdin=json.dumps(payload),
    )

    output = _stdout_json(result)
    assert result.returncode == ExitCode.INFEASIBLE
    assert output["mathematical_status"] == "infeasible"
    assert output["result"]["path"] == []


def test_solve_local_continuous_nlp_through_cli():
    payload = {
        "version": "1",
        "problem_type": "nonlinear_programming",
        "variables": [{"name": "x", "lb": None, "ub": None, "initial": 0}],
        "objective": {"sense": "max", "expression": "10 - (x - 3)**2"},
        "solver_options": {
            "method": "BFGS",
            "max_iterations": 1000,
            "tolerance": 1e-9,
        },
    }

    result = _run("solve", "nlp.continuous_local", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "feasible"
    assert output["result"]["local_candidate"] is True
    assert output["result"]["objective"] == pytest.approx(10.0, abs=1e-6)
    assert output["result"]["variables"][0]["name"] == "x"
    assert output["result"]["variables"][0]["value"] == pytest.approx(3.0, abs=1e-5)
    assert "local numerical candidate" in output["warnings"][0]


def test_solve_convex_qp_through_cli():
    payload = {
        "version": "1",
        "problem_type": "quadratic_programming",
        "variables": [
            {"name": "x1", "label": "X1", "lb": None, "ub": None},
            {"name": "x2", "label": "X2", "lb": None, "ub": None},
        ],
        "objective": {
            "sense": "min",
            "linear_coefficients": [-4.0, -6.0],
            "quadratic_matrix": [
                [2.0, 1.0],
                [1.0, 2.0],
            ],
            "offset": 0.0,
        },
        "constraints": [],
        "solver_options": {"method": "osqp", "tolerance": 1e-7},
    }

    result = _run("solve", "qp.continuous", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["capability_id"] == "qp.continuous"
    assert output["job_status"] == "completed"
    assert output["mathematical_status"] == "optimal"
    assert output["result"]["objective"] == pytest.approx(-28.0 / 3.0, rel=1e-5)
    values = {item["name"]: item["value"] for item in output["result"]["variables"]}
    assert values["x1"] == pytest.approx(2.0 / 3.0, rel=1e-5)
    assert values["x2"] == pytest.approx(8.0 / 3.0, rel=1e-5)
    assert output["validation"]["status"] in {"verified", "partial"}


def test_train_linear_regression_through_cli():
    payload = {
        "version": "1",
        "problem_type": "regression",
        "dataset": {
            "feature_names": ["size"],
            "target_name": "price",
            "rows": [{"features": [value], "target": 2 + 3 * value} for value in range(1, 9)],
        },
        "training_options": {
            "method": "OLS",
            "test_fraction": 0.25,
            "random_seed": 17,
            "ridge_alpha": 1,
        },
    }

    result = _run("solve", "ml.regression.linear", stdin=json.dumps(payload))

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "feasible"
    assert output["result"]["trained_model"] is True
    assert output["result"]["intercept"] == pytest.approx(2.0)
    assert output["result"]["coefficients"][0]["value"] == pytest.approx(3.0)


def test_train_binary_logistic_classification_through_cli():
    payload = {
        "version": "1",
        "problem_type": "binary_classification",
        "dataset": {
            "feature_names": ["score"],
            "target_name": "approved",
            "rows": [
                {"features": [0], "target": "no"},
                {"features": [1], "target": "no"},
                {"features": [2], "target": "no"},
                {"features": [3], "target": "no"},
                {"features": [7], "target": "yes"},
                {"features": [8], "target": "yes"},
                {"features": [9], "target": "yes"},
                {"features": [10], "target": "yes"},
            ],
        },
        "training_options": {
            "method": "LogisticRegression",
            "test_fraction": 0.25,
            "random_seed": 17,
            "learning_rate": 0.1,
            "max_iterations": 2000,
            "l2_alpha": 0,
        },
    }

    result = _run(
        "solve",
        "ml.classification.binary_logistic",
        stdin=json.dumps(payload),
    )

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "feasible"
    assert output["result"]["trained_model"] is True
    assert output["result"]["negative_label"] == "no"
    assert output["result"]["positive_label"] == "yes"
    assert output["result"]["test_metrics"]["accuracy"] == pytest.approx(1.0)


def test_solve_single_container_packing_through_cli():
    pytest.importorskip("ortools")
    payload = {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "all_required",
        "gravity_mode": "simple",
        "container": {
            "id": "container-1",
            "name": "Container",
            "dimensions": {"length": 4, "width": 3, "height": 2},
            "capacities": [],
        },
        "items": [
            {
                "id": "box",
                "name": "Box",
                "dimensions": {"length": 2, "width": 3, "height": 2},
                "value": 5,
                "quantity": 2,
                "rotation_policy": "fixed",
                "allowed_orientations": [],
                "consumptions": [],
            }
        ],
        "solver_options": {"time_limit": 10, "mip_gap": 0.01},
    }

    result = _run(
        "solve",
        "packing.single_container_3d",
        stdin=json.dumps(payload),
    )

    output = _stdout_json(result)
    assert result.returncode == ExitCode.SUCCESS
    assert output["mathematical_status"] == "optimal"
    assert len(output["result"]["requested"]["placements"]) == 2
    assert output["result"]["recovery"] is None


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
