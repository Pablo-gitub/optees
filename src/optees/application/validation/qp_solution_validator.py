from __future__ import annotations

import math
from typing import Any, Mapping, Tuple
import numpy as np

from optees.application.contracts.execution import MathematicalStatus, SerializedResult
from optees.application.contracts.solution_validation import (
    SolutionValidation,
    SolutionValidationStatus,
    ValidationCheck,
    ValidationCheckStatus,
    ValidationViolation,
)
from optees.domain.models.qp.qp_model import QPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation


def _check_status(passed: bool) -> ValidationCheckStatus:
    return ValidationCheckStatus.PASSED if passed else ValidationCheckStatus.FAILED


class QPIndependentSolutionValidator:
    """Recomputes Convex QP candidate invariants without trusting backend claims."""

    DEFAULT_LIMITATIONS = (
        "Independent validation verifies primal feasibility and objective recalculation from the original model definition.",
        "Validation does not prove global optimality when the input problem violates convexity.",
        "Dual KKT stationarity is verified only when complete dual multipliers are provided by the backend.",
    )

    def __init__(self, *, absolute_tolerance: float = 1e-7, relative_tolerance: float = 1e-7):
        for value in (absolute_tolerance, relative_tolerance):
            if isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError("QP validation tolerances must be finite and non-negative")
        self._absolute_tolerance = float(absolute_tolerance)
        self._relative_tolerance = float(relative_tolerance)

    def __call__(
        self,
        model: QPModel,
        serialized: SerializedResult,
    ) -> SolutionValidation:
        if serialized.mathematical_status not in {
            MathematicalStatus.OPTIMAL,
            MathematicalStatus.FEASIBLE,
        }:
            return SolutionValidation.not_available(
                "No primal candidate is available for independent QP validation."
            )

        raw_result = serialized.result if isinstance(serialized.result, dict) else {}
        values_dict, vector_violations = self._extract_candidate_values(model, raw_result)

        vector_check = ValidationCheck(
            code="qp.variable_vector",
            status=_check_status(not vector_violations),
            description="The candidate contains one finite value for every declared variable.",
            measurements={
                "declared_count": len(model.variables),
                "candidate_count": len(values_dict),
            },
        )
        if vector_violations:
            return self._build_report((vector_check,), tuple(vector_violations), has_duals=False)

        checks: list[ValidationCheck] = [vector_check]
        violations: list[ValidationViolation] = []

        # 1. Bounds check
        bound_violations, max_bound_violation = self._validate_bounds(model, values_dict)
        violations.extend(bound_violations)
        checks.append(
            ValidationCheck(
                code="qp.bounds",
                status=_check_status(not bound_violations),
                description="Every candidate value satisfies its declared lower and upper bounds.",
                measurements={"maximum_violation": max_bound_violation},
            )
        )

        # 2. Constraints check
        cons_violations, max_cons_violation = self._validate_constraints(model, values_dict)
        violations.extend(cons_violations)
        checks.append(
            ValidationCheck(
                code="qp.constraints",
                status=_check_status(not cons_violations),
                description="Every linear constraint is satisfied by the candidate vector.",
                measurements={
                    "constraint_count": len(model.constraints),
                    "maximum_violation": max_cons_violation,
                },
            )
        )

        # 3. Objective check
        obj_check, obj_violations = self._validate_objective(model, values_dict, raw_result)
        checks.append(obj_check)
        violations.extend(obj_violations)

        # 4. KKT check (if dual values available)
        dual_data = raw_result.get("dual_values")
        has_duals = False
        if isinstance(dual_data, dict):
            kkt_check, kkt_violations, evaluated = self._validate_kkt(model, values_dict, dual_data)
            if evaluated:
                has_duals = True
                checks.append(kkt_check)
                violations.extend(kkt_violations)

        return self._build_report(tuple(checks), tuple(violations), has_duals=has_duals)

    def _extract_candidate_values(
        self,
        model: QPModel,
        result_dict: Mapping[str, Any],
    ) -> Tuple[dict[str, float], list[ValidationViolation]]:
        values_raw = result_dict.get("variables")
        if not isinstance(values_raw, list):
            return {}, [
                ValidationViolation(
                    code="qp.invalid_candidate_structure",
                    check_code="qp.variable_vector",
                    path="$.result.variables",
                    message="Candidate variables mapping is missing or malformed.",
                )
            ]

        values: dict[str, float] = {}
        violations: list[ValidationViolation] = []
        declared_names = set(model.variable_names())

        for index, item in enumerate(values_raw):
            if not isinstance(item, dict) or set(item) != {"name", "value"}:
                violations.append(
                    ValidationViolation(
                        code="qp.invalid_candidate_structure",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables[{index}]",
                        message="Each candidate entry must contain exactly name and value.",
                    )
                )
                continue
            name = item["name"]
            if not isinstance(name, str) or name in values:
                violations.append(
                    ValidationViolation(
                        code="qp.invalid_candidate_structure",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables[{index}].name",
                        message="Candidate variable names must be unique strings.",
                    )
                )
                continue
            values[name] = item["value"]

        for v in model.variables:
            if v.name not in values:
                violations.append(
                    ValidationViolation(
                        code="qp.missing_variable_value",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables['{v.name}']",
                        message=f"Declared variable '{v.name}' is missing from candidate.",
                    )
                )
                continue

            raw_val = values[v.name]
            if raw_val is None or isinstance(raw_val, bool):
                violations.append(
                    ValidationViolation(
                        code="qp.non_numeric_variable_value",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables['{v.name}']",
                        message=f"Variable '{v.name}' value must be a finite number.",
                    )
                )
                continue

            try:
                num = float(raw_val)
            except (TypeError, ValueError):
                violations.append(
                    ValidationViolation(
                        code="qp.non_numeric_variable_value",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables['{v.name}']",
                        message=f"Variable '{v.name}' value must be a finite number.",
                    )
                )
                continue

            if not math.isfinite(num):
                violations.append(
                    ValidationViolation(
                        code="qp.non_finite_variable_value",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables['{v.name}']",
                        message=f"Variable '{v.name}' has non-finite value {num}.",
                    )
                )
                continue

            values[v.name] = num

        for key in values:
            if key not in declared_names:
                violations.append(
                    ValidationViolation(
                        code="qp.unexpected_variable_value",
                        check_code="qp.variable_vector",
                        path=f"$.result.variables['{key}']",
                        message=f"Candidate contains undeclared variable '{key}'.",
                    )
                )

        return values, violations

    def _validate_bounds(
        self,
        model: QPModel,
        values: Mapping[str, float],
    ) -> Tuple[list[ValidationViolation], float]:
        violations: list[ValidationViolation] = []
        max_violation = 0.0

        for v in model.variables:
            if v.name not in values:
                continue
            x_val = values[v.name]
            lb = v.bounds.lb
            ub = v.bounds.ub

            if lb is not None:
                diff = lb - x_val
                if diff > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.lower_bound_violation",
                            check_code="qp.bounds",
                            path=f"$.result.variables['{v.name}']",
                            message=f"Variable '{v.name}' value {x_val} violates lower bound {lb}.",
                            measurements={"violation": diff, "bound": lb, "value": x_val},
                        )
                    )
                if diff > max_violation:
                    max_violation = diff

            if ub is not None:
                diff = x_val - ub
                if diff > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.upper_bound_violation",
                            check_code="qp.bounds",
                            path=f"$.result.variables['{v.name}']",
                            message=f"Variable '{v.name}' value {x_val} violates upper bound {ub}.",
                            measurements={"violation": diff, "bound": ub, "value": x_val},
                        )
                    )
                if diff > max_violation:
                    max_violation = diff

        return violations, max_violation

    def _validate_constraints(
        self,
        model: QPModel,
        values: Mapping[str, float],
    ) -> Tuple[list[ValidationViolation], float]:
        violations: list[ValidationViolation] = []
        max_violation = 0.0
        var_names = model.variable_names()
        x_vec = np.array([values.get(name, 0.0) for name in var_names], dtype=float)

        for idx, cons in enumerate(model.constraints):
            lhs_val = float(np.dot(cons.coefs, x_vec))
            rhs_val = float(cons.rhs)
            rel = cons.relation

            if rel == Relation.EQ:
                diff = abs(lhs_val - rhs_val)
                if diff > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.equality_constraint_violation",
                            check_code="qp.constraints",
                            path=f"$.problem.constraints[{idx}]",
                            message=f"Constraint '{cons.name or idx}' equality violated: lhs={lhs_val}, rhs={rhs_val}.",
                            measurements={"violation": diff, "lhs": lhs_val, "rhs": rhs_val},
                        )
                    )
                if diff > max_violation:
                    max_violation = diff
            elif rel == Relation.LE:
                diff = lhs_val - rhs_val
                if diff > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.inequality_constraint_violation",
                            check_code="qp.constraints",
                            path=f"$.problem.constraints[{idx}]",
                            message=f"Constraint '{cons.name or idx}' <= violated: lhs={lhs_val} > rhs={rhs_val}.",
                            measurements={"violation": diff, "lhs": lhs_val, "rhs": rhs_val},
                        )
                    )
                if diff > max_violation:
                    max_violation = diff
            elif rel == Relation.GE:
                diff = rhs_val - lhs_val
                if diff > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.inequality_constraint_violation",
                            check_code="qp.constraints",
                            path=f"$.problem.constraints[{idx}]",
                            message=f"Constraint '{cons.name or idx}' >= violated: lhs={lhs_val} < rhs={rhs_val}.",
                            measurements={"violation": diff, "lhs": lhs_val, "rhs": rhs_val},
                        )
                    )
                if diff > max_violation:
                    max_violation = diff

        return violations, max_violation

    def _validate_objective(
        self,
        model: QPModel,
        values: Mapping[str, float],
        result_dict: Mapping[str, Any],
    ) -> Tuple[ValidationCheck, list[ValidationViolation]]:
        reported_obj = result_dict.get("objective")
        violations: list[ValidationViolation] = []

        if reported_obj is None or isinstance(reported_obj, bool):
            violations.append(
                ValidationViolation(
                    code="qp.missing_objective_value",
                    check_code="qp.objective",
                    path="$.result.objective",
                    message="Reported objective value is missing or non-numeric.",
                )
            )
            return (
                ValidationCheck(
                    code="qp.objective",
                    status=ValidationCheckStatus.FAILED,
                    description="The reported objective value matches the recomputed quadratic objective value.",
                    measurements={},
                ),
                violations,
            )

        try:
            rep_val = float(reported_obj)
        except (TypeError, ValueError):
            violations.append(
                ValidationViolation(
                    code="qp.non_numeric_objective_value",
                    check_code="qp.objective",
                    path="$.result.objective",
                    message="Reported objective value is non-numeric.",
                )
            )
            return (
                ValidationCheck(
                    code="qp.objective",
                    status=ValidationCheckStatus.FAILED,
                    description="The reported objective value matches the recomputed quadratic objective value.",
                    measurements={},
                ),
                violations,
            )

        # Recompute objective: 0.5 * x^T * Q * x + c^T * x + offset
        var_names = model.variable_names()
        x_vec = np.array([values.get(name, 0.0) for name in var_names], dtype=float)
        Q = np.array(model.objective.quadratic_matrix, dtype=float)
        c = np.array(model.objective.linear_coefs, dtype=float)
        offset = float(model.objective.offset)

        expected_obj = float(0.5 * (x_vec.T @ Q @ x_vec) + (c.T @ x_vec) + offset)
        diff = abs(rep_val - expected_obj)
        allowed_tol = self._absolute_tolerance + self._relative_tolerance * abs(expected_obj)

        if diff > allowed_tol:
            violations.append(
                ValidationViolation(
                    code="qp.objective_mismatch",
                    check_code="qp.objective",
                    path="$.result.objective",
                    message=f"Reported objective {rep_val} differs from recomputed {expected_obj} (diff {diff:.2e} > allowed {allowed_tol:.2e}).",
                    measurements={
                        "expected_objective": expected_obj,
                        "reported_objective": rep_val,
                        "absolute_difference": diff,
                    },
                )
            )

        check = ValidationCheck(
            code="qp.objective",
            status=_check_status(not violations),
            description="The reported objective value matches the recomputed quadratic objective value.",
            measurements={
                "expected_objective": expected_obj,
                "reported_objective": rep_val,
                "absolute_difference": diff,
            },
        )
        return check, violations

    def _validate_kkt(
        self,
        model: QPModel,
        values: Mapping[str, float],
        dual_dict: Mapping[str, Any],
    ) -> Tuple[ValidationCheck, list[ValidationViolation], bool]:
        cons_duals = dual_dict.get("constraints", ())
        lb_duals = dual_dict.get("lower_bounds", ())
        ub_duals = dual_dict.get("upper_bounds", ())

        n = model.n_vars()
        m = len(model.constraints)

        if len(cons_duals) != m or len(lb_duals) != n or len(ub_duals) != n:
            return (
                ValidationCheck(
                    code="qp.kkt_stationarity",
                    status=ValidationCheckStatus.FAILED,
                    description="The first-order KKT stationarity and complementary slackness conditions are satisfied.",
                    measurements={},
                ),
                [
                    ValidationViolation(
                        code="qp.kkt_dimension_mismatch",
                        check_code="qp.kkt_stationarity",
                        path="$.result.dual_values",
                        message="Dual values length does not match model constraint/bound dimensions.",
                    )
                ],
                True,
            )

        var_names = model.variable_names()
        x_vec = np.array([values.get(name, 0.0) for name in var_names], dtype=float)
        Q = np.array(model.objective.quadratic_matrix, dtype=float)
        c = np.array(model.objective.linear_coefs, dtype=float)

        # Gradient of objective
        grad_f = Q @ x_vec + c

        # Stationarity: grad_f + A^T y - z_lb + z_ub = 0 (for min)
        # Note: for max, sign conventions are mapped in adapter
        y_cons = np.array(cons_duals, dtype=float)
        z_lb = np.array(lb_duals, dtype=float)
        z_ub = np.array(ub_duals, dtype=float)

        A_mat = (
            np.array([cons.coefs for cons in model.constraints], dtype=float)
            if m > 0
            else np.zeros((0, n))
        )

        # Check multiplier non-negativity for inequalities and bounds
        violations: list[ValidationViolation] = []
        complementarity_residual = 0.0
        for index, cons in enumerate(model.constraints):
            lhs = float(np.dot(np.asarray(cons.coefs, dtype=float), x_vec))
            multiplier = float(y_cons[index])
            if cons.relation == Relation.LE:
                if multiplier < -self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.negative_dual_multiplier",
                            check_code="qp.kkt_stationarity",
                            path=f"$.result.dual_values.constraints[{index}]",
                            message="A <= constraint multiplier must be non-negative.",
                        )
                    )
                complementarity_residual = max(
                    complementarity_residual, abs(multiplier * (float(cons.rhs) - lhs))
                )
            elif cons.relation == Relation.GE:
                if multiplier > self._absolute_tolerance:
                    violations.append(
                        ValidationViolation(
                            code="qp.negative_dual_multiplier",
                            check_code="qp.kkt_stationarity",
                            path=f"$.result.dual_values.constraints[{index}]",
                            message="A >= constraint uses a non-positive signed multiplier.",
                        )
                    )
                complementarity_residual = max(
                    complementarity_residual, abs(multiplier * (lhs - float(cons.rhs)))
                )

        for i in range(n):
            if z_lb[i] < -self._absolute_tolerance:
                violations.append(
                    ValidationViolation(
                        code="qp.negative_dual_multiplier",
                        check_code="qp.kkt_stationarity",
                        path=f"$.result.dual_values.lower_bounds[{i}]",
                        message=f"Lower bound multiplier {z_lb[i]} is negative.",
                    )
                )
            variable = model.variables[i]
            if variable.bounds.lb is not None:
                complementarity_residual = max(
                    complementarity_residual,
                    abs(z_lb[i] * (x_vec[i] - float(variable.bounds.lb))),
                )
            if variable.bounds.ub is not None:
                complementarity_residual = max(
                    complementarity_residual,
                    abs(z_ub[i] * (float(variable.bounds.ub) - x_vec[i])),
                )
            if z_ub[i] < -self._absolute_tolerance:
                violations.append(
                    ValidationViolation(
                        code="qp.negative_dual_multiplier",
                        check_code="qp.kkt_stationarity",
                        path=f"$.result.dual_values.upper_bounds[{i}]",
                        message=f"Upper bound multiplier {z_ub[i]} is negative.",
                    )
                )

        is_min = model.objective.sense == ObjectiveSense.MIN
        if is_min:
            stat_res = grad_f + (A_mat.T @ y_cons if m > 0 else 0.0) - z_lb + z_ub
        else:
            stat_res = -grad_f + (A_mat.T @ y_cons if m > 0 else 0.0) - z_lb + z_ub

        max_stat_res = float(np.max(np.abs(stat_res))) if n > 0 else 0.0
        allowed_kkt_tol = (
            self._absolute_tolerance * 10.0
        )  # allow slightly relaxed numerical tolerance for KKT residual

        if max_stat_res > allowed_kkt_tol:
            violations.append(
                ValidationViolation(
                    code="qp.kkt_stationarity_violation",
                    check_code="qp.kkt_stationarity",
                    path="$.result.dual_values",
                    message=f"KKT stationarity residual {max_stat_res:.2e} exceeds tolerance {allowed_kkt_tol:.2e}.",
                    measurements={"stationarity_residual": max_stat_res},
                )
            )

        if complementarity_residual > allowed_kkt_tol:
            violations.append(
                ValidationViolation(
                    code="qp.kkt_complementarity_violation",
                    check_code="qp.kkt_stationarity",
                    path="$.result.dual_values",
                    message=(
                        "KKT complementary-slackness residual "
                        f"{complementarity_residual:.2e} exceeds tolerance "
                        f"{allowed_kkt_tol:.2e}."
                    ),
                    measurements={"complementarity_residual": complementarity_residual},
                )
            )

        check = ValidationCheck(
            code="qp.kkt_stationarity",
            status=_check_status(not violations),
            description="The first-order KKT stationarity and complementary slackness conditions are satisfied within tolerance.",
            measurements={
                "stationarity_residual": max_stat_res,
                "complementarity_residual": complementarity_residual,
            },
        )
        return check, violations, True

    def _build_report(
        self,
        checks: Tuple[ValidationCheck, ...],
        violations: Tuple[ValidationViolation, ...],
        *,
        has_duals: bool,
    ) -> SolutionValidation:
        tolerances = {
            "absolute_tolerance": self._absolute_tolerance,
            "relative_tolerance": self._relative_tolerance,
        }

        if any(c.status is ValidationCheckStatus.FAILED for c in checks):
            status = SolutionValidationStatus.FAILED
        elif has_duals:
            status = SolutionValidationStatus.VERIFIED
        else:
            status = SolutionValidationStatus.PARTIAL

        return SolutionValidation(
            status=status,
            checks=checks,
            violations=violations,
            tolerances=tolerances,
            limitations=self.DEFAULT_LIMITATIONS,
        )
