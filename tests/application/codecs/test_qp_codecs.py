from __future__ import annotations

import pytest

from optees.application.codecs.qp_problem_codec import qp_model_from_public_dict
from optees.application.codecs.qp_result_codec import QPResultCodec
from optees.application.contracts.execution import MathematicalStatus
from optees.domain.entities.qp.solution import QPSolution
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.qp.qp_dual_values import QPDualValues
from optees.domain.value_objects.qp.qp_kkt_residuals import QPKKTResiduals
from optees.domain.value_objects.qp.qp_solve_status import QPSolveStatus
from optees.domain.value_objects.qp.qp_solver_diagnostics import QPSolverDiagnostics
from optees.utility.qp_json_io import qp_model_to_dict


def test_qp_problem_codec_roundtrip() -> None:
    payload = {
        "contract_version": "1",
        "problem_schema_version": "1",
        "capability_id": "qp.continuous",
        "problem_type": "quadratic_programming",
        "variables": [
            {"name": "x1", "label": "X1", "lower_bound": 0.0, "upper_bound": 5.0},
            {"name": "x2", "label": "X2", "lower_bound": None, "upper_bound": None},
        ],
        "objective": {
            "sense": "min",
            "linear_coefs": [-4.0, -6.0],
            "quadratic_matrix": [
                [2.0, 1.0],
                [1.0, 2.0],
            ],
            "offset": 1.5,
        },
        "constraints": [
            {"name": "c1", "coefs": [1.0, 1.0], "relation": "<=", "rhs": 10.0}
        ],
        "options": {
            "method": "osqp",
            "tolerance": 1e-6,
            "max_iterations": 2000,
            "time_limit_seconds": 30.0,
            "warm_start": True,
            "initial_primal": [1.0, 2.0],
        },
    }

    model = qp_model_from_public_dict(payload)
    assert model.n_vars() == 2
    assert model.objective.sense == ObjectiveSense.MIN
    assert model.objective.offset == 1.5
    assert model.options.warm_start is True

    serialized = qp_model_to_dict(model)
    assert serialized["capability_id"] == "qp.continuous"
    assert serialized["variables"][0]["name"] == "x1"
    assert serialized["objective"]["linear_coefs"] == [-4.0, -6.0]
    assert serialized["constraints"][0]["rhs"] == 10.0


def test_qp_problem_codec_rejects_missing_required() -> None:
    with pytest.raises(ValueError, match="missing required fields"):
        qp_model_from_public_dict({"contract_version": "1"})


def test_qp_result_codec_optimal() -> None:
    solution = QPSolution(
        status=QPSolveStatus.OPTIMAL,
        objective=-9.333333333333334,
        values={"x1": 0.6666666666666666, "x2": 2.6666666666666665},
        dual_values=QPDualValues(
            constraints=(-1.0,),
            lower_bounds=(0.0, 0.0),
            upper_bounds=(0.0, 0.0),
        ),
        kkt_residuals=QPKKTResiduals(
            primal_residual=0.0,
            dual_residual=1.7e-5,
            duality_gap=None,
            complementarity_residual=None,
        ),
        diagnostics=QPSolverDiagnostics(
            backend="osqp",
            backend_version="0.6.7.post3",
            status="solved",
            status_code=1,
            iterations=25,
            solve_time_seconds=1e-5,
            setup_time_seconds=2e-5,
            message=None,
            success=True,
        ),
        extras={"pri_res": 0.0, "dua_res": 1.7e-5},
    )

    codec = QPResultCodec()
    serialized = codec.serialize(solution)

    assert serialized.mathematical_status == MathematicalStatus.OPTIMAL
    assert serialized.result["objective"] == -9.333333333333334
    assert serialized.result["variables"]["x1"] == 0.6666666666666666
    assert serialized.result["dual_values"]["constraints"] == [-1.0]
    assert serialized.diagnostics["backend"] == "osqp"
    assert serialized.diagnostics["iterations"] == 25


def test_qp_result_codec_infeasible() -> None:
    solution = QPSolution(
        status=QPSolveStatus.INFEASIBLE,
        objective=None,
        values={},
        diagnostics=QPSolverDiagnostics(
            backend="osqp",
            backend_version="0.6.7.post3",
            status="primal infeasible",
            status_code=-3,
            iterations=15,
            success=False,
        ),
    )
    codec = QPResultCodec()
    serialized = codec.serialize(solution)
    assert serialized.mathematical_status == MathematicalStatus.INFEASIBLE
    assert serialized.result["objective"] is None
    assert serialized.result["variables"] == {}
