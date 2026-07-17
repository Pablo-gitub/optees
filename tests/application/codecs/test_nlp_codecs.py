from __future__ import annotations

import json

import pytest

from optees.application.codecs.nlp_problem_codec import nlp_model_from_public_dict
from optees.application.codecs.nlp_result_codec import NLPResultCodec
from optees.domain.entities.nlp.solution import NLPSolution
from optees.domain.value_objects.nlp.solver_method import NLPSolverMethod


def _payload() -> dict:
    return {
        "version": "1",
        "problem_type": "nonlinear_programming",
        "variables": [
            {"name": "x", "label": "coordinate", "lb": None, "ub": None, "initial": 0}
        ],
        "objective": {"sense": "min", "expression": "(x - 2)**2"},
        "solver_options": {
            "method": "BFGS",
            "max_iterations": 100,
            "tolerance": 1e-8,
        },
    }


def test_problem_codec_preserves_expression_initial_point_and_options():
    model = nlp_model_from_public_dict(_payload())

    assert model.objective.expression == "(x - 2)**2"
    assert model.initial_point() == (0.0,)
    assert model.options.method is NLPSolverMethod.BFGS
    assert model.options.max_iterations == 100
    assert model.options.tolerance == pytest.approx(1e-8)


def test_problem_codec_requires_explicit_public_sections():
    payload = _payload()
    del payload["objective"]

    with pytest.raises(ValueError, match="missing required fields: objective"):
        nlp_model_from_public_dict(payload)


def test_problem_codec_rejects_unsafe_expression_and_invalid_bound_method():
    payload = _payload()
    payload["objective"]["expression"] = "__import__('os').system('echo no')"
    with pytest.raises(ValueError, match="expression|function|syntax|node"):
        nlp_model_from_public_dict(payload)

    payload = _payload()
    payload["variables"][0]["lb"] = 0
    with pytest.raises(ValueError, match="does not support box bounds"):
        nlp_model_from_public_dict(payload)


def test_result_codec_marks_converged_candidate_as_local_feasible_result():
    solution = NLPSolution.from_solver_result(
        status="Converged",
        objective=0,
        values={"x": 2},
        extras={
            "method": "BFGS",
            "success": True,
            "message": "Optimization terminated successfully.",
            "iterations": 3,
            "evaluations": 8,
            "scipy_status": 0,
            "convergence_history": [4, 1, 0],
        },
    )

    serialized = NLPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.result == {
        "objective": 0.0,
        "variables": [{"name": "x", "value": 2.0}],
        "local_candidate": True,
    }
    assert serialized.diagnostics["method"] == "BFGS"
    assert serialized.diagnostics["convergence_history"] == [4.0, 1.0, 0.0]
    assert "not a certificate" in serialized.warnings[0]


def test_result_codec_preserves_iteration_limit_candidate_with_warning():
    solution = NLPSolution.from_solver_result(
        status="IterationLimit",
        objective=0.1,
        values={"x": 1.9},
        extras={"iterations": 10, "message": "maximum number reached"},
    )

    serialized = NLPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "feasible"
    assert serialized.result["local_candidate"] is True
    assert "iteration limit" in serialized.warnings[0].lower()


def test_result_codec_emits_strict_json_for_failed_run():
    solution = NLPSolution.from_solver_result(
        status="Failed",
        objective=None,
        values={},
        extras={"success": False, "scipy_status": float("inf")},
    )

    serialized = NLPResultCodec().serialize(solution)

    assert serialized.mathematical_status.value == "not_solved"
    assert serialized.result == {
        "objective": None,
        "variables": [],
        "local_candidate": False,
    }
    assert serialized.diagnostics["scipy_status"] is None
    json.dumps(serialized.result, allow_nan=False)
    json.dumps(serialized.diagnostics, allow_nan=False)
