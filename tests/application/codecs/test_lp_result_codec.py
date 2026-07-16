from __future__ import annotations

import json

import pytest

from optees.application.codecs.lp_result_codec import LPResultCodec
from optees.application.contracts.execution import (
    ExecutionEnvelope,
    ExecutionMetadata,
    JobStatus,
    MathematicalStatus,
    TerminationReason,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.utility.lp_json_io import lp_model_from_dict


def _solution(
    *,
    status: str = "Optimal",
    objective: float | None = 3.0,
    values: dict[str, float] | None = None,
    extras: dict[str, object] | None = None,
) -> LPSolution:
    return LPSolution.from_utility_tuple(
        status,
        objective,
        values or {"x": 0.0, "y": 3.0},
        extras or {},
    )


def test_lp_codec_serializes_ranges_diagnostics_and_envelope():
    solution = _solution(
        extras={
            "method": "highs",
            "nit": 4,
            "message": "Optimal",
            "status_code": 0,
            "success": True,
            "var_names": ["x", "y"],
            "objective_sense": "max",
            "eqlin": {"marginals": [], "residual": []},
            "alt_opt": {
                "has_alternate_optimum": True,
                "dimension": 1,
                "range_tol": 1e-8,
                "varying_variables": ["x", "y"],
                "ranges": {
                    "x": {"min": 0.0, "max": 3.0, "width": 3.0, "is_fixed": False},
                    "y": {"min": 0.0, "max": 3.0, "width": 3.0, "is_fixed": False},
                },
                "extreme_points": {
                    "A": {"x": 0.0, "y": 3.0},
                    "B": {"x": 3.0, "y": 0.0},
                },
                "auxiliary_failures": [],
            },
        }
    )

    serialized = LPResultCodec().serialize(solution)
    envelope = ExecutionEnvelope(
        job_id="job-lp-1",
        capability_id=LPResultCodec.capability_id,
        job_status=JobStatus.COMPLETED,
        mathematical_status=serialized.mathematical_status,
        termination_reason=TerminationReason.COMPLETED,
        result=serialized.result,
        diagnostics=serialized.diagnostics,
        warnings=serialized.warnings,
        metadata=ExecutionMetadata("0.8.0", "v1", "1", "1"),
    )
    payload = json.loads(envelope.to_json())

    assert serialized.mathematical_status is MathematicalStatus.OPTIMAL
    assert payload["result"]["variables"] == [
        {"name": "x", "value": 0.0},
        {"name": "y", "value": 3.0},
    ]
    assert payload["result"]["optimal_face"]["dimension"] == 1
    assert payload["diagnostics"]["method"] == "highs"
    assert payload["diagnostics"]["highs"]["equalities"]["marginals"] == []


def test_lp_codec_represents_unbounded_optimal_ranges_without_json_infinity():
    solution = _solution(
        extras={
            "alt_opt": {
                "has_alternate_optimum": True,
                "dimension": 1,
                "varying_variables": ["y"],
                "ranges": {
                    "x": {"min": 0.0, "max": 0.0, "width": 0.0, "is_fixed": True},
                    "y": {
                        "min": float("-inf"),
                        "max": float("inf"),
                        "width": float("inf"),
                        "is_fixed": False,
                    },
                },
            }
        }
    )

    serialized = LPResultCodec().serialize(solution)
    y_range = serialized.result["optimal_face"]["ranges"][1]
    encoded = json.dumps(serialized.result, allow_nan=False)

    assert y_range["minimum"] is None
    assert y_range["minimum_unbounded"] is True
    assert y_range["maximum"] is None
    assert y_range["maximum_unbounded"] is True
    assert y_range["width_unbounded"] is True
    assert "Infinity" not in encoded


def test_lp_codec_keeps_missing_diagnostics_explicitly_null():
    serialized = LPResultCodec().serialize(_solution(extras={}))

    assert serialized.diagnostics["method"] is None
    assert serialized.diagnostics["iterations"] is None
    assert serialized.diagnostics["highs"]["equalities"] is None
    assert serialized.result["optimal_face"]["analysis_status"] == "not_available"


@pytest.mark.parametrize(
    ("domain_status", "public_status"),
    [
        ("Optimal", MathematicalStatus.OPTIMAL),
        ("Infeasible", MathematicalStatus.INFEASIBLE),
        ("Unbounded", MathematicalStatus.UNBOUNDED),
        ("NotSolved", MathematicalStatus.NOT_SOLVED),
    ],
)
def test_lp_codec_maps_domain_statuses(domain_status, public_status):
    serialized = LPResultCodec().serialize(
        _solution(status=domain_status, objective=None, values={})
    )

    assert serialized.mathematical_status is public_status


@pytest.mark.parametrize(
    "solution",
    [
        _solution(objective=float("nan")),
        _solution(values={"x": float("inf")}),
        _solution(extras={"eqlin": {"marginals": [float("nan")], "residual": []}}),
    ],
)
def test_lp_codec_rejects_non_finite_public_values(solution):
    with pytest.raises(ValueError, match="finite|NaN"):
        LPResultCodec().serialize(solution)


def test_lp_codec_serializes_a_real_highs_result():
    model = lp_model_from_dict(
        {
            "version": "1",
            "variables": [
                {"name": "x", "label": "", "lb": 0, "ub": None},
                {"name": "y", "label": "", "lb": 0, "ub": None},
            ],
            "objective": {
                "sense": "max",
                "coefficients": [1, 1],
                "offset": 0,
            },
            "constraints": [
                {"coefficients": [1, 1], "relation": "<=", "rhs": 3}
            ],
        }
    )

    solution = SolveLPUseCase(LPSolverAdapter()).execute(model)
    serialized = LPResultCodec().serialize(solution)
    encoded = json.dumps(
        {"result": serialized.result, "diagnostics": serialized.diagnostics},
        allow_nan=False,
    )

    assert serialized.mathematical_status is MathematicalStatus.OPTIMAL
    assert serialized.result["objective"] == pytest.approx(3.0)
    assert serialized.result["optimal_face"]["has_alternate_optimum"] is True
    assert serialized.diagnostics["highs"]["upper_bounds"]["residual"] == [None, None]
    assert serialized.diagnostics["highs"]["upper_bounds"]["residual_non_finite"] == [
        {"index": 0, "kind": "positive_infinity"},
        {"index": 1, "kind": "positive_infinity"},
    ]
    assert "Infinity" not in encoded
