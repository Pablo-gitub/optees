"""View-model coverage for the linear scenario desktop workflow.

Every mathematical expectation in this module comes from the frozen contract's
hand-calculable reference examples, and every result is produced by the real
registered capability through the ordinary application boundary. Nothing here
reimplements the reduction, the guarantee or the binding rule.
"""

from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import QThreadPool

from optees.application.contracts.capability_ids import (
    SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID,
    SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID,
)
from optees.application.contracts.errors import ErrorCode, StructuredError
from optees.composition.local_agent import (
    create_local_optimization_service,
    create_scenario_min_max_loss_optimization_service,
)
from optees.data.adapters.lp.lp_solver_adapter import LPSolverAdapter
from optees.data.adapters.milp.milp_solver_adapter import MILPSolverAdapter
from optees.presentation.viewmodels.scenario_view_model import (
    MAX_MIN_REWARD_ORIENTATION,
    MIN_MAX_LOSS_ORIENTATION,
    ScenarioConstraintInput,
    ScenarioFormInput,
    ScenarioInput,
    ScenarioOptionsInput,
    ScenarioVariableInput,
    ScenarioViewModel,
    build_problem_payload,
)

SOLVE_TIMEOUT_MS = 20_000


@pytest.fixture(scope="module")
def service():
    return create_local_optimization_service()


@pytest.fixture
def view_model(service, qtbot):
    model = ScenarioViewModel(service)
    return model


def _min_max_loss_form() -> ScenarioFormInput:
    """Contract example 1: guarantee 76/7, binding s1 and s2."""
    return ScenarioFormInput(
        variables=(
            ScenarioVariableInput("x1", "Allocation 1", 0.0, None, "C"),
            ScenarioVariableInput("x2", "Allocation 2", 0.0, None, "C"),
        ),
        scenarios=(
            ScenarioInput("s1", "Regime 1", (2.0, -1.0), 5.0),
            ScenarioInput("s2", "Regime 2", (-1.0, 3.0), 2.0),
            ScenarioInput("s3", "Regime 3", (1.0, 1.0), -4.0),
        ),
        constraints=(ScenarioConstraintInput("total_budget", (1.0, 1.0), "=", 10.0),),
    )


def _max_min_reward_form() -> ScenarioFormInput:
    """Contract example 2: negative guarantee -22/13, binding sA and sB."""
    return ScenarioFormInput(
        variables=(
            ScenarioVariableInput("x1", "", 0.0, 4.0, "C"),
            ScenarioVariableInput("x2", "", 0.0, 4.0, "C"),
        ),
        scenarios=(
            ScenarioInput("sA", "", (4.0, -2.0), -10.0),
            ScenarioInput("sB", "", (-2.0, 5.0), -8.0),
            ScenarioInput("sC", "", (1.0, 1.0), -5.0),
        ),
        constraints=(ScenarioConstraintInput("budget", (1.0, 1.0), "<=", 6.0),),
    )


def _binary_form() -> ScenarioFormInput:
    """Contract example 3: binary MILP route, guarantee 15.0, binding s2."""
    return ScenarioFormInput(
        variables=(
            ScenarioVariableInput("x1", "", None, None, "B"),
            ScenarioVariableInput("x2", "", None, None, "B"),
            ScenarioVariableInput("x3", "", None, None, "B"),
        ),
        scenarios=(
            ScenarioInput("s1", "", (10.0, 2.0, 8.0), 0.0),
            ScenarioInput("s2", "", (3.0, 12.0, 4.0), 0.0),
            ScenarioInput("s3", "", (6.0, 5.0, 9.0), 0.0),
        ),
        constraints=(ScenarioConstraintInput("pick_two", (1.0, 1.0, 1.0), "=", 2.0),),
    )


def _submit(view_model: ScenarioViewModel, qtbot, form, *, signal_name="succeeded"):
    signal = getattr(view_model, signal_name)
    with qtbot.waitSignal(signal, timeout=SOLVE_TIMEOUT_MS) as blocker:
        view_model.submit(form)
    return blocker.args[0]


# ---------------------------------------------------------------------------
# Payload mapping
# ---------------------------------------------------------------------------


def test_payload_preserves_declared_order_for_min_max_loss() -> None:
    payload = build_problem_payload(_min_max_loss_form(), orientation=MIN_MAX_LOSS_ORIENTATION)

    assert payload["version"] == "1"
    assert payload["problem_type"] == "linear_scenario"
    assert payload["orientation"] == MIN_MAX_LOSS_ORIENTATION
    assert [variable["name"] for variable in payload["variables"]] == ["x1", "x2"]
    assert [scenario["id"] for scenario in payload["scenarios"]] == ["s1", "s2", "s3"]
    assert payload["scenarios"][0]["coefficients"] == [2.0, -1.0]
    assert payload["scenarios"][2]["offset"] == -4.0
    assert payload["shared_constraints"][0] == {
        "name": "total_budget",
        "coefficients": [1.0, 1.0],
        "relation": "=",
        "rhs": 10.0,
    }


def test_payload_carries_the_reward_orientation_without_sign_flipping() -> None:
    form = _max_min_reward_form()
    payload = build_problem_payload(form, orientation=MAX_MIN_REWARD_ORIENTATION)

    assert payload["orientation"] == MAX_MIN_REWARD_ORIENTATION
    # Coefficients and offsets reach the capability exactly as declared.
    assert payload["scenarios"][0]["coefficients"] == [4.0, -2.0]
    assert payload["scenarios"][0]["offset"] == -10.0


def test_optional_sections_are_omitted_when_absent() -> None:
    form = ScenarioFormInput(
        variables=(ScenarioVariableInput("x1"),),
        scenarios=(ScenarioInput("s1", "", (1.0,), 0.0),),
    )

    payload = build_problem_payload(form, orientation=MIN_MAX_LOSS_ORIENTATION)

    assert "shared_constraints" not in payload
    assert "shared_objective" not in payload
    assert "options" not in payload


def test_options_and_shared_objective_are_mapped_when_provided() -> None:
    form = ScenarioFormInput(
        variables=(ScenarioVariableInput("x1"), ScenarioVariableInput("x2")),
        scenarios=(ScenarioInput("s1", "", (1.0, 1.0), 0.0),),
        shared_objective_coefficients=(0.5, -0.25),
        shared_objective_offset=3.0,
        options=ScenarioOptionsInput(
            tolerance=1e-9, binding_tolerance=1e-5, time_limit_seconds=12.5
        ),
    )

    payload = build_problem_payload(form, orientation=MIN_MAX_LOSS_ORIENTATION)

    assert payload["shared_objective"] == {"coefficients": [0.5, -0.25], "offset": 3.0}
    assert payload["options"] == {
        "tolerance": 1e-9,
        "binding_tolerance": 1e-5,
        "time_limit_seconds": 12.5,
    }


def test_unknown_orientation_is_refused() -> None:
    with pytest.raises(ValueError):
        build_problem_payload(_min_max_loss_form(), orientation="minimise_something")


# ---------------------------------------------------------------------------
# Orientation selection
# ---------------------------------------------------------------------------


def test_orientation_selection_switches_capability_identity(view_model, qtbot) -> None:
    assert view_model.capability_id == SCENARIO_MIN_MAX_LOSS_CAPABILITY_ID
    assert view_model.orientation == MIN_MAX_LOSS_ORIENTATION

    with qtbot.waitSignal(view_model.orientation_changed, timeout=1000) as blocker:
        view_model.set_capability_id(SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID)

    assert blocker.args[0] == MAX_MIN_REWARD_ORIENTATION
    assert view_model.orientation != MIN_MAX_LOSS_ORIENTATION


def test_unknown_capability_is_refused(view_model) -> None:
    with pytest.raises(ValueError):
        view_model.set_capability_id("scenario.linear.unknown")


# ---------------------------------------------------------------------------
# Execution outcomes through the registered capability
# ---------------------------------------------------------------------------


def test_min_max_loss_submission_reports_the_analytic_guarantee(view_model, qtbot) -> None:
    envelope = _submit(view_model, qtbot, _min_max_loss_form())
    payload = envelope.to_dict()

    assert payload["job_status"] == "completed"
    assert payload["mathematical_status"] == "optimal"
    assert payload["termination_reason"] == "completed"
    assert payload["validation"]["status"] == "verified"
    result = payload["result"]
    assert result["orientation"] == MIN_MAX_LOSS_ORIENTATION
    assert result["guaranteed_value"] == pytest.approx(76 / 7)
    assert [entry["scenario_id"] for entry in result["scenario_values"]] == ["s1", "s2", "s3"]
    assert result["binding_scenario_ids"] == ["s1", "s2"]
    assert [variable["name"] for variable in result["variables"]] == ["x1", "x2"]
    assert result["variables"][0]["value"] == pytest.approx(37 / 7)


def test_max_min_reward_submission_keeps_a_negative_guarantee(view_model, qtbot) -> None:
    view_model.set_capability_id(SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID)

    envelope = _submit(view_model, qtbot, _max_min_reward_form())
    result = envelope.to_dict()["result"]

    assert result["orientation"] == MAX_MIN_REWARD_ORIENTATION
    assert result["guaranteed_value"] == pytest.approx(-22 / 13)
    assert result["guaranteed_value"] < 0.0
    assert result["binding_scenario_ids"] == ["sA", "sB"]
    assert [entry["is_binding"] for entry in result["scenario_values"]] == [True, True, False]


def test_binary_variables_route_through_the_discrete_capability(view_model, qtbot) -> None:
    envelope = _submit(view_model, qtbot, _binary_form())
    payload = envelope.to_dict()

    assert payload["mathematical_status"] == "optimal"
    assert payload["result"]["guaranteed_value"] == pytest.approx(15.0)
    assert payload["result"]["binding_scenario_ids"] == ["s2"]
    assert payload["validation"]["status"] == "verified"


def test_the_submitted_orientation_always_matches_the_selected_capability(
    view_model, qtbot
) -> None:
    """The same numbers submitted under each capability keep their own semantics.

    The view-model stamps the orientation of the selected capability, so a user
    can never send a payload that the other capability would have to reinterpret.
    """
    loss_result = _submit(view_model, qtbot, _max_min_reward_form()).to_dict()["result"]
    assert loss_result["orientation"] == MIN_MAX_LOSS_ORIENTATION

    view_model.set_capability_id(SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID)
    reward_result = _submit(view_model, qtbot, _max_min_reward_form()).to_dict()["result"]
    assert reward_result["orientation"] == MAX_MIN_REWARD_ORIENTATION

    # Identical input, opposite worst case: the two capabilities are not aliases.
    assert loss_result["guaranteed_value"] != reward_result["guaranteed_value"]
    assert loss_result["binding_scenario_ids"] != reward_result["binding_scenario_ids"]


def test_dimension_mismatch_is_reported_as_a_structured_rejection(view_model, qtbot) -> None:
    form = ScenarioFormInput(
        variables=(
            ScenarioVariableInput("x1", "", 0.0, None, "C"),
            ScenarioVariableInput("x2", "", 0.0, None, "C"),
        ),
        # One coefficient too many for the declared variables.
        scenarios=(ScenarioInput("s1", "", (1.0, 2.0, 3.0), 0.0),),
    )

    error = _submit(view_model, qtbot, form, signal_name="rejected")

    assert isinstance(error, StructuredError)
    assert error.code is ErrorCode.VALIDATION_FAILED
    assert any(
        detail.code == "scenario.dimension_mismatch"
        and detail.path == "$.scenarios[0].coefficients"
        for detail in error.details
    )


def test_infeasible_problem_reports_no_candidate(view_model, qtbot) -> None:
    form = ScenarioFormInput(
        variables=(ScenarioVariableInput("x1", "", 0.0, None, "C"),),
        scenarios=(ScenarioInput("s1", "", (1.0,), 0.0),),
        constraints=(
            ScenarioConstraintInput("low", (1.0,), "<=", 1.0),
            ScenarioConstraintInput("high", (1.0,), ">=", 5.0),
        ),
    )

    payload = _submit(view_model, qtbot, form).to_dict()

    assert payload["mathematical_status"] == "infeasible"
    assert payload["result"]["guaranteed_value"] is None
    assert payload["result"]["variables"] == []
    assert payload["result"]["scenario_values"] == []
    assert payload["result"]["binding_scenario_ids"] == []
    assert payload["validation"]["status"] == "not_available"


def test_unbounded_problem_reports_no_candidate(view_model, qtbot) -> None:
    form = ScenarioFormInput(
        variables=(ScenarioVariableInput("x1", "", None, None, "C"),),
        scenarios=(ScenarioInput("s1", "", (1.0,), 0.0),),
    )

    payload = _submit(view_model, qtbot, form).to_dict()

    assert payload["mathematical_status"] == "unbounded"
    assert payload["result"]["guaranteed_value"] is None
    assert payload["validation"]["status"] == "not_available"


def test_unavailable_dependency_is_reported_not_hidden(qtbot) -> None:
    unavailable = create_scenario_min_max_loss_optimization_service(
        lp_solver_port=LPSolverAdapter(),
        milp_solver_port=MILPSolverAdapter(),
        dependency_available=False,
    )
    view_model = ScenarioViewModel(unavailable)

    assert view_model.is_available() is False
    assert view_model.unavailable_reason()

    error = _submit(view_model, qtbot, _min_max_loss_form(), signal_name="rejected")

    assert isinstance(error, StructuredError)
    assert error.code is ErrorCode.DEPENDENCY_UNAVAILABLE


def test_missing_service_fails_without_pretending_to_solve(qtbot) -> None:
    view_model = ScenarioViewModel(None)

    with qtbot.waitSignal(view_model.failed, timeout=1000) as blocker:
        view_model.submit(_min_max_loss_form())

    assert blocker.args[0]
    assert view_model.busy is False


# ---------------------------------------------------------------------------
# Asynchronous lifecycle
# ---------------------------------------------------------------------------


class _GatedService:
    """Delays a real service response so async ordering can be observed."""

    def __init__(self, inner) -> None:
        self._inner = inner
        self.release = threading.Event()
        self.calls = 0

    def solve(self, capability_id, payload):
        self.calls += 1
        self.release.wait(timeout=10.0)
        return self._inner.solve(capability_id, payload)

    def list_capabilities(self):
        return self._inner.list_capabilities()


def test_busy_state_brackets_the_submission(view_model, qtbot) -> None:
    states: list[bool] = []
    view_model.busy_changed.connect(states.append)

    _submit(view_model, qtbot, _min_max_loss_form())

    assert states == [True, False]
    assert view_model.busy is False


def test_cancel_discards_the_pending_result(service, qtbot) -> None:
    gated = _GatedService(service)
    view_model = ScenarioViewModel(gated)
    received: list[object] = []
    view_model.succeeded.connect(received.append)

    view_model.submit(_min_max_loss_form())
    assert view_model.busy is True
    view_model.cancel()
    assert view_model.busy is False

    gated.release.set()
    QThreadPool.globalInstance().waitForDone(SOLVE_TIMEOUT_MS)
    qtbot.wait(120)

    assert received == []


def test_a_superseded_submission_never_overwrites_the_newer_one(service, qtbot) -> None:
    gated = _GatedService(service)
    view_model = ScenarioViewModel(gated)
    received: list[object] = []
    view_model.succeeded.connect(received.append)

    # The first submission is still gated when the second one supersedes it.
    view_model.submit(_min_max_loss_form())
    view_model.set_capability_id(SCENARIO_MAX_MIN_REWARD_CAPABILITY_ID)
    view_model.submit(_max_min_reward_form())
    gated.release.set()
    QThreadPool.globalInstance().waitForDone(SOLVE_TIMEOUT_MS)
    qtbot.wait(200)

    assert gated.calls == 2
    assert len(received) == 1
    assert received[0].to_dict()["result"]["orientation"] == MAX_MIN_REWARD_ORIENTATION


def test_last_payload_exposes_exactly_what_was_submitted(view_model, qtbot) -> None:
    _submit(view_model, qtbot, _min_max_loss_form())

    payload = view_model.last_payload
    assert payload is not None
    assert payload["orientation"] == MIN_MAX_LOSS_ORIENTATION
    assert [scenario["id"] for scenario in payload["scenarios"]] == ["s1", "s2", "s3"]
