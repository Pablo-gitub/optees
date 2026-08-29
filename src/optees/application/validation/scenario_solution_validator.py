from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

from optees.application.contracts.json_value import JsonValue
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.models.scenario.scenario_result import (
    ScenarioResult,
    ScenarioSolveStatus,
)
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


class ScenarioIndependentSolutionValidator:
    """Independent validator for finite linear scenario optimization results.

    In stage C2A (ROBUST-VS), verifies structural integrity, orientation equality,
    variable/scenario identities and ordering, finiteness, status coherence,
    and solution type compatibility without trusting solver diagnostics.
    """

    def __init__(
        self,
        *,
        absolute_tolerance: float = 1e-7,
        relative_tolerance: float = 1e-7,
    ) -> None:
        for value in (absolute_tolerance, relative_tolerance):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("Scenario validation tolerances must be finite and non-negative")
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)

    def __call__(
        self,
        model: ScenarioModel,
        result: ScenarioResult,
    ) -> SolutionValidation:
        if not isinstance(model, ScenarioModel):
            raise TypeError(
                f"model must be an instance of ScenarioModel, got {type(model).__name__}"
            )
        if not isinstance(result, ScenarioResult) and not hasattr(result, "status"):
            raise TypeError(
                f"result must be an instance of ScenarioResult, got {type(result).__name__}"
            )

        status = getattr(result, "status", None)
        is_candidate_status = status in (
            ScenarioSolveStatus.OPTIMAL,
            ScenarioSolveStatus.FEASIBLE,
        )

        # 1. Orientation check
        orientation_check, orientation_violations = self._validate_orientation(model, result)

        # 2. Status coherence & solution type check
        status_check, status_violations = self._validate_status_coherence(model, result)

        # Handling for no-candidate statuses (infeasible, unbounded, not_solved)
        if not is_candidate_status:
            # If structural violations exist on orientation or status/delegated solution, report failure
            initial_checks = [orientation_check, status_check]
            initial_violations = list(orientation_violations) + list(status_violations)

            # Also verify no candidate payload is attached to no-candidate status
            candidate_violations = self._validate_no_candidate_payload(result)
            initial_violations.extend(candidate_violations)

            if initial_violations:
                return self._report(tuple(initial_checks), tuple(initial_violations))

            return SolutionValidation.not_available(
                "No primal candidate is available for independent scenario validation."
            )

        # Candidate statuses (optimal, feasible)
        checks: list[ValidationCheck] = [orientation_check, status_check]
        violations: list[ValidationViolation] = list(orientation_violations) + list(
            status_violations
        )

        # 3. Variable vector & ordering check
        var_check, var_violations = self._validate_variable_vector(model, result)
        checks.append(var_check)
        violations.extend(var_violations)

        # 4. Scenario values & ordering check
        scen_check, scen_violations = self._validate_scenario_values(model, result)
        checks.append(scen_check)
        violations.extend(scen_violations)

        return self._report(tuple(checks), tuple(violations))

    def _validate_orientation(
        self,
        model: ScenarioModel,
        result: Any,
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        result_orientation = getattr(result, "orientation", None)
        passed = result_orientation == model.orientation
        measurements: dict[str, JsonValue] = {
            "model_orientation": model.orientation.value,
            "result_orientation": getattr(result_orientation, "value", str(result_orientation)),
        }
        check = ValidationCheck(
            code="scenario.orientation",
            status=_check_status(passed),
            description="The result orientation matches the problem orientation.",
            measurements=measurements,
        )
        if passed:
            return check, []
        return check, [
            _violation(
                code="orientation_mismatch",
                check_code="scenario.orientation",
                path="$.orientation",
                message=(
                    f"Result orientation '{measurements['result_orientation']}' "
                    f"does not match model orientation '{model.orientation.value}'."
                ),
                measurements=measurements,
            )
        ]

    def _validate_status_coherence(
        self,
        model: ScenarioModel,
        result: Any,
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        violations: list[ValidationViolation] = []
        result_status = getattr(result, "status", None)
        delegated_solution = getattr(result, "delegated_solution", None)

        # Check solution type compatibility
        is_discrete = model.is_discrete()
        expected_type = MILPSolution if is_discrete else LPSolution
        type_passed = isinstance(delegated_solution, expected_type)
        if not type_passed:
            actual_name = type(delegated_solution).__name__
            expected_name = expected_type.__name__
            violations.append(
                _violation(
                    code="solution_type_mismatch",
                    check_code="scenario.status_coherence",
                    path="$.delegated_solution",
                    message=(
                        f"{'Discrete' if is_discrete else 'Continuous'} scenario model requires "
                        f"{expected_name}, got {actual_name}."
                    ),
                    measurements={
                        "is_discrete": is_discrete,
                        "expected_solution_type": expected_name,
                        "actual_solution_type": actual_name,
                    },
                )
            )

        # Check status mapping coherence
        status_passed = False
        delegated_status_str = ""
        if isinstance(delegated_solution, LPSolution):
            delegated_status_str = delegated_solution.status.value
            expected_status = _LP_STATUS_MAP.get(delegated_solution.status)
            status_passed = expected_status is not None and result_status == expected_status
        elif isinstance(delegated_solution, MILPSolution):
            delegated_status_str = delegated_solution.status.value
            expected_status = _MILP_STATUS_MAP.get(delegated_solution.status)
            status_passed = expected_status is not None and result_status == expected_status
        else:
            delegated_status_str = str(getattr(delegated_solution, "status", None))

        if not status_passed:
            violations.append(
                _violation(
                    code="status_mismatch",
                    check_code="scenario.status_coherence",
                    path="$.status",
                    message=(
                        f"Robust solve status '{getattr(result_status, 'value', str(result_status))}' "
                        f"does not match delegated solver status '{delegated_status_str}'."
                    ),
                    measurements={
                        "result_status": getattr(result_status, "value", str(result_status)),
                        "delegated_status": delegated_status_str,
                    },
                )
            )

        # Check candidate presence constraint for no-candidate statuses
        candidate_violations: list[ValidationViolation] = []
        if result_status not in (
            ScenarioSolveStatus.OPTIMAL,
            ScenarioSolveStatus.FEASIBLE,
        ):
            candidate_violations = self._validate_no_candidate_payload(result)
            violations.extend(candidate_violations)

        passed = type_passed and status_passed and not candidate_violations
        check = ValidationCheck(
            code="scenario.status_coherence",
            status=_check_status(passed),
            description="The robust solve status and solution type are coherent with the delegated solver outcome.",
            measurements={
                "result_status": getattr(result_status, "value", str(result_status)),
                "delegated_status": delegated_status_str,
                "is_discrete": is_discrete,
                "solution_type": type(delegated_solution).__name__,
            },
        )
        return check, violations

    def _validate_no_candidate_payload(
        self,
        result: Any,
    ) -> list[ValidationViolation]:
        violations: list[ValidationViolation] = []
        result_status = getattr(result, "status", None)
        status_str = getattr(result_status, "value", str(result_status))

        if getattr(result, "variables", None) is not None:
            violations.append(
                _violation(
                    code="unexpected_candidate",
                    check_code="scenario.status_coherence",
                    path="$.variables",
                    message=f"Status '{status_str}' must not carry candidate variables.",
                )
            )
        if getattr(result, "guaranteed_value", None) is not None:
            violations.append(
                _violation(
                    code="unexpected_candidate",
                    check_code="scenario.status_coherence",
                    path="$.guaranteed_value",
                    message=f"Status '{status_str}' must not carry a guaranteed value.",
                )
            )
        if getattr(result, "auxiliary_value", None) is not None:
            violations.append(
                _violation(
                    code="unexpected_candidate",
                    check_code="scenario.status_coherence",
                    path="$.auxiliary_value",
                    message=f"Status '{status_str}' must not carry an auxiliary value.",
                )
            )
        if getattr(result, "scenario_values", ()):
            violations.append(
                _violation(
                    code="unexpected_candidate",
                    check_code="scenario.status_coherence",
                    path="$.scenario_values",
                    message=f"Status '{status_str}' must not carry scenario values.",
                )
            )
        if getattr(result, "binding_scenario_ids", ()):
            violations.append(
                _violation(
                    code="unexpected_candidate",
                    check_code="scenario.status_coherence",
                    path="$.binding_scenario_ids",
                    message=f"Status '{status_str}' must not carry binding scenario IDs.",
                )
            )
        return violations

    def _validate_variable_vector(
        self,
        model: ScenarioModel,
        result: Any,
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        violations: list[ValidationViolation] = []
        declared_order = model.variable_names()
        declared_set = set(declared_order)

        result_orig_order = getattr(result, "original_variable_order", None)
        if result_orig_order != declared_order:
            violations.append(
                _violation(
                    code="variable_order_mismatch",
                    check_code="scenario.variable_vector",
                    path="$.original_variable_order",
                    message="Result original_variable_order does not match model variable order.",
                    measurements={
                        "expected": list(declared_order),
                        "actual": list(result_orig_order or ()),
                    },
                )
            )

        variables_map = getattr(result, "variables", None)
        if not isinstance(variables_map, Mapping):
            violations.append(
                _violation(
                    code="invalid_variable_vector",
                    check_code="scenario.variable_vector",
                    path="$.variables",
                    message="Candidate variables must be a mapping.",
                )
            )
            check = ValidationCheck(
                code="scenario.variable_vector",
                status=ValidationCheckStatus.FAILED,
                description="The candidate contains finite values for every declared variable in exact original order.",
                measurements={"declared_count": len(declared_order)},
            )
            return check, violations

        var_keys = tuple(variables_map.keys())
        missing = sorted(declared_set - set(var_keys))
        unknown = sorted(set(var_keys) - declared_set)

        if missing or unknown:
            violations.append(
                _violation(
                    code="invalid_variable_vector",
                    check_code="scenario.variable_vector",
                    path="$.variables",
                    message="Candidate variables do not match declared model variables.",
                    measurements={
                        "missing": missing,
                        "unknown": unknown,
                    },
                )
            )
        elif var_keys != declared_order:
            violations.append(
                _violation(
                    code="variable_order_mismatch",
                    check_code="scenario.variable_vector",
                    path="$.variables",
                    message="Candidate variables do not follow exact declared variable order.",
                    measurements={
                        "expected_order": list(declared_order),
                        "actual_order": list(var_keys),
                    },
                )
            )

        # Check finiteness of variable values
        for name, val in variables_map.items():
            if (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
            ):
                violations.append(
                    _violation(
                        code="non_finite_variable",
                        check_code="scenario.variable_vector",
                        path=f"$.variables.{name}",
                        message=f"Variable '{name}' contains non-finite value {val!r}.",
                        measurements={"variable": name, "value": str(val)},
                    )
                )

        # Check finiteness of guarantee
        guarantee = getattr(result, "guaranteed_value", None)
        if (
            guarantee is None
            or isinstance(guarantee, bool)
            or not isinstance(guarantee, (int, float))
            or not math.isfinite(float(guarantee))
        ):
            violations.append(
                _violation(
                    code="non_finite_guarantee",
                    check_code="scenario.variable_vector",
                    path="$.guaranteed_value",
                    message=f"Guaranteed value contains non-finite value {guarantee!r}.",
                    measurements={"guaranteed_value": str(guarantee)},
                )
            )

        # Check finiteness of auxiliary value
        aux_val = getattr(result, "auxiliary_value", None)
        if (
            aux_val is None
            or isinstance(aux_val, bool)
            or not isinstance(aux_val, (int, float))
            or not math.isfinite(float(aux_val))
        ):
            violations.append(
                _violation(
                    code="non_finite_auxiliary",
                    check_code="scenario.variable_vector",
                    path="$.auxiliary_value",
                    message=f"Auxiliary value contains non-finite value {aux_val!r}.",
                    measurements={"auxiliary_value": str(aux_val)},
                )
            )

        passed = not violations
        check = ValidationCheck(
            code="scenario.variable_vector",
            status=_check_status(passed),
            description="The candidate contains finite values for every declared variable in exact original order.",
            measurements={
                "declared_count": len(declared_order),
                "candidate_count": len(variables_map),
            },
        )
        return check, violations

    def _validate_scenario_values(
        self,
        model: ScenarioModel,
        result: Any,
    ) -> tuple[ValidationCheck, list[ValidationViolation]]:
        violations: list[ValidationViolation] = []
        declared_scen_ids = model.scenario_ids()
        declared_scen_set = set(declared_scen_ids)

        result_scen_order = getattr(result, "scenario_order", None)
        if result_scen_order != declared_scen_ids:
            violations.append(
                _violation(
                    code="scenario_order_mismatch",
                    check_code="scenario.scenario_values",
                    path="$.scenario_order",
                    message="Result scenario_order does not match model scenario order.",
                    measurements={
                        "expected": list(declared_scen_ids),
                        "actual": list(result_scen_order or ()),
                    },
                )
            )

        scen_values = getattr(result, "scenario_values", None)
        if not isinstance(scen_values, Sequence) or isinstance(scen_values, (str, bytes)):
            violations.append(
                _violation(
                    code="invalid_scenario_values",
                    check_code="scenario.scenario_values",
                    path="$.scenario_values",
                    message="Scenario values must be a sequence.",
                )
            )
            check = ValidationCheck(
                code="scenario.scenario_values",
                status=ValidationCheckStatus.FAILED,
                description="Every declared scenario has a corresponding finite evaluation in exact original order.",
                measurements={"declared_scenario_count": len(declared_scen_ids)},
            )
            return check, violations

        actual_ids = tuple(getattr(sv, "scenario_id", None) for sv in scen_values)
        missing_ids = sorted(declared_scen_set - set(actual_ids))
        unknown_ids = sorted(set(actual_ids) - declared_scen_set)

        if missing_ids or unknown_ids:
            violations.append(
                _violation(
                    code="invalid_scenario_values",
                    check_code="scenario.scenario_values",
                    path="$.scenario_values",
                    message="Scenario values IDs do not match declared model scenarios.",
                    measurements={
                        "missing": missing_ids,
                        "unknown": unknown_ids,
                    },
                )
            )
        elif actual_ids != declared_scen_ids:
            violations.append(
                _violation(
                    code="scenario_order_mismatch",
                    check_code="scenario.scenario_values",
                    path="$.scenario_values",
                    message="Scenario values do not follow exact declared scenario order.",
                    measurements={
                        "expected_order": list(declared_scen_ids),
                        "actual_order": list(actual_ids),
                    },
                )
            )

        # Check finiteness of each scenario value
        for idx, sv in enumerate(scen_values):
            val = getattr(sv, "value", None)
            scen_id = getattr(sv, "scenario_id", f"index_{idx}")
            if (
                val is None
                or isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
            ):
                violations.append(
                    _violation(
                        code="non_finite_scenario_value",
                        check_code="scenario.scenario_values",
                        path=f"$.scenario_values[{idx}].value",
                        message=f"Scenario value for '{scen_id}' is non-finite: {val!r}.",
                        measurements={"scenario_id": str(scen_id), "value": str(val)},
                    )
                )

        passed = not violations
        check = ValidationCheck(
            code="scenario.scenario_values",
            status=_check_status(passed),
            description="Every declared scenario has a corresponding finite evaluation in exact original order.",
            measurements={
                "declared_scenario_count": len(declared_scen_ids),
                "scenario_value_count": len(scen_values),
            },
        )
        return check, violations

    def _report(
        self,
        checks: tuple[ValidationCheck, ...],
        violations: tuple[ValidationViolation, ...],
    ) -> SolutionValidation:
        return SolutionValidation.from_checks(
            checks,
            violations=violations,
            tolerances={
                "absolute": self._absolute_tolerance,
                "relative": self._relative_tolerance,
            },
            limitations=(
                "Structural validation does not independently prove mathematical optimality.",
                "The validator does not assess whether the scenario model represents business intent.",
            ),
        )


_LP_STATUS_MAP = {
    SolveStatus.OPTIMAL: ScenarioSolveStatus.OPTIMAL,
    SolveStatus.INFEASIBLE: ScenarioSolveStatus.INFEASIBLE,
    SolveStatus.UNBOUNDED: ScenarioSolveStatus.UNBOUNDED,
    SolveStatus.NOT_SOLVED: ScenarioSolveStatus.NOT_SOLVED,
}

_MILP_STATUS_MAP = {
    MILPSolveStatus.OPTIMAL: ScenarioSolveStatus.OPTIMAL,
    MILPSolveStatus.FEASIBLE: ScenarioSolveStatus.FEASIBLE,
    MILPSolveStatus.INFEASIBLE: ScenarioSolveStatus.INFEASIBLE,
    MILPSolveStatus.UNBOUNDED: ScenarioSolveStatus.UNBOUNDED,
    MILPSolveStatus.NOT_SOLVED: ScenarioSolveStatus.NOT_SOLVED,
}


def _check_status(passed: bool) -> ValidationCheckStatus:
    return ValidationCheckStatus.PASSED if passed else ValidationCheckStatus.FAILED


def _violation(
    code: str,
    check_code: str,
    path: str,
    message: str,
    measurements: dict[str, JsonValue] | None = None,
) -> ValidationViolation:
    return ValidationViolation(
        code=code,
        check_code=check_code,
        path=path,
        message=message,
        measurements=measurements or {},
    )
