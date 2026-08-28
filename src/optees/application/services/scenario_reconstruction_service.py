from __future__ import annotations

import math
from typing import Mapping, Union

from optees.application.contracts.execution import MathematicalStatus
from optees.application.services.scenario_reduction_service import (
    ScenarioReductionResult,
)
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.entities.scenario.scenario_value import ScenarioValue
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.models.scenario.scenario_result import ScenarioResult
from optees.domain.value_objects.lp.solve_status import SolveStatus
from optees.domain.value_objects.milp.solve_status import MILPSolveStatus


class ScenarioReconstructionError(ValueError):
    """Raised when a delegated solution cannot be reconstructed into a consistent ScenarioResult."""


class ScenarioReconstructionService:
    """Pure service reconstructing an immutable ScenarioResult from ScenarioModel, ScenarioReductionResult, and delegated solution."""

    @staticmethod
    def reconstruct(
        model: ScenarioModel,
        reduction: ScenarioReductionResult,
        delegated_solution: Union[LPSolution, MILPSolution],
        *,
        consistency_tolerance: float = 1e-5,
    ) -> ScenarioResult:
        if not isinstance(model, ScenarioModel):
            raise TypeError(f"Expected ScenarioModel instance, got {type(model).__name__}")
        if not isinstance(reduction, ScenarioReductionResult):
            raise TypeError(
                f"Expected ScenarioReductionResult instance, got {type(reduction).__name__}"
            )
        if not isinstance(delegated_solution, (LPSolution, MILPSolution)):
            raise TypeError(
                f"Expected LPSolution or MILPSolution instance, got {type(delegated_solution).__name__}"
            )
        if (
            isinstance(consistency_tolerance, bool)
            or not isinstance(consistency_tolerance, (int, float))
            or not math.isfinite(float(consistency_tolerance))
            or float(consistency_tolerance) <= 0
        ):
            raise ValueError(
                f"consistency_tolerance must be a finite positive number, got {consistency_tolerance!r}"
            )
        tol = float(consistency_tolerance)

        # Map delegated solver status to MathematicalStatus
        mapped_status = _map_status(delegated_solution)

        # Non-candidate states: INFEASIBLE, UNBOUNDED, NOT_SOLVED
        if mapped_status not in (
            MathematicalStatus.OPTIMAL,
            MathematicalStatus.FEASIBLE,
        ):
            return ScenarioResult(
                status=mapped_status,
                orientation=model.orientation,
                guaranteed_value=None,
                variables=None,
                scenario_values=(),
                binding_scenario_ids=(),
                delegated_solution=delegated_solution,
                auxiliary_variable_name=reduction.auxiliary_variable_name,
                auxiliary_value=None,
            )

        # Candidate states: OPTIMAL, FEASIBLE
        values_raw = delegated_solution.values
        if not isinstance(values_raw, Mapping):
            raise ScenarioReconstructionError("Delegated solution values must be a mapping.")

        aux_name = reduction.auxiliary_variable_name
        if aux_name not in values_raw:
            raise ScenarioReconstructionError(
                f"Auxiliary variable {aux_name!r} is missing from solver solution values."
            )

        raw_aux_val = values_raw[aux_name]
        if (
            isinstance(raw_aux_val, bool)
            or not isinstance(raw_aux_val, (int, float))
            or not math.isfinite(float(raw_aux_val))
        ):
            raise ScenarioReconstructionError(
                f"Auxiliary variable {aux_name!r} has non-finite value {raw_aux_val!r}."
            )
        aux_val = float(raw_aux_val)

        # Validate user variables
        declared_names = model.variable_names()
        declared_set = set(declared_names)
        allowed_keys = declared_set | {aux_name}

        unknown_keys = sorted(set(values_raw.keys()) - allowed_keys)
        if unknown_keys:
            raise ScenarioReconstructionError(
                f"Unknown variables present in solution values: {unknown_keys}."
            )

        missing_keys = sorted(declared_set - set(values_raw.keys()))
        if missing_keys:
            raise ScenarioReconstructionError(
                f"Declared variables missing from solution values: {missing_keys}."
            )

        # Build user_variables dictionary preserving original_variable_order
        user_variables: dict[str, float] = {}
        for name in declared_names:
            raw_v = values_raw[name]
            if (
                isinstance(raw_v, bool)
                or not isinstance(raw_v, (int, float))
                or not math.isfinite(float(raw_v))
            ):
                raise ScenarioReconstructionError(
                    f"Variable {name!r} has non-finite value {raw_v!r}."
                )
            user_variables[name] = float(raw_v)

        # Recompute scenario values and guaranteed bound using ScenarioModel
        all_evals = model.evaluate_all_scenarios(user_variables)
        is_loss = model.orientation.is_loss_minimization()
        guaranteed_val = max(all_evals) if is_loss else min(all_evals)

        # Derive binding set with frozen binding tolerance
        binding_tol = model.options.binding_tolerance
        scenario_values_list: list[ScenarioValue] = []
        binding_ids_list: list[str] = []

        for k, scen in enumerate(model.scenarios):
            v_k = all_evals[k]
            if is_loss:
                threshold = guaranteed_val - binding_tol * max(1.0, abs(guaranteed_val))
                is_bind = v_k >= threshold - 1e-14
            else:
                threshold = guaranteed_val + binding_tol * max(1.0, abs(guaranteed_val))
                is_bind = v_k <= threshold + 1e-14

            scenario_values_list.append(
                ScenarioValue(
                    scenario_id=scen.id,
                    value=v_k,
                    is_binding=is_bind,
                )
            )
            if is_bind:
                binding_ids_list.append(scen.id)

        # Consistency check 1: Compare recomputed guaranteed_value with auxiliary_value
        diff_aux = abs(guaranteed_val - aux_val)
        allowed_aux = tol * max(1.0, abs(guaranteed_val), abs(aux_val))
        if diff_aux > allowed_aux:
            raise ScenarioReconstructionError(
                f"Recomputed guaranteed value ({guaranteed_val}) diverges from auxiliary variable value "
                f"({aux_val}) by {diff_aux:.6e} (allowed: {allowed_aux:.6e})."
            )

        # Consistency check 2: Compare recomputed guaranteed_value with delegated objective
        if (
            delegated_solution.objective is None
            or isinstance(delegated_solution.objective, bool)
            or not isinstance(delegated_solution.objective, (int, float))
            or not math.isfinite(float(delegated_solution.objective))
        ):
            raise ScenarioReconstructionError(
                f"Delegated solution has missing or non-finite objective {delegated_solution.objective!r}."
            )
        obj_val = float(delegated_solution.objective)
        diff_obj = abs(guaranteed_val - obj_val)
        allowed_obj = tol * max(1.0, abs(guaranteed_val), abs(obj_val))
        if diff_obj > allowed_obj:
            raise ScenarioReconstructionError(
                f"Recomputed guaranteed value ({guaranteed_val}) diverges from delegated objective "
                f"({obj_val}) by {diff_obj:.6e} (allowed: {allowed_obj:.6e})."
            )

        return ScenarioResult(
            status=mapped_status,
            orientation=model.orientation,
            guaranteed_value=guaranteed_val,
            variables=user_variables,
            scenario_values=tuple(scenario_values_list),
            binding_scenario_ids=tuple(binding_ids_list),
            delegated_solution=delegated_solution,
            auxiliary_variable_name=aux_name,
            auxiliary_value=aux_val,
        )


def _map_status(solution: Union[LPSolution, MILPSolution]) -> MathematicalStatus:
    if isinstance(solution, LPSolution):
        if solution.status == SolveStatus.OPTIMAL:
            return MathematicalStatus.OPTIMAL
        if solution.status == SolveStatus.INFEASIBLE:
            return MathematicalStatus.INFEASIBLE
        if solution.status == SolveStatus.UNBOUNDED:
            return MathematicalStatus.UNBOUNDED
        return MathematicalStatus.NOT_SOLVED
    elif isinstance(solution, MILPSolution):
        if solution.status == MILPSolveStatus.OPTIMAL:
            return MathematicalStatus.OPTIMAL
        if solution.status == MILPSolveStatus.FEASIBLE:
            return MathematicalStatus.FEASIBLE
        if solution.status == MILPSolveStatus.INFEASIBLE:
            return MathematicalStatus.INFEASIBLE
        if solution.status == MILPSolveStatus.UNBOUNDED:
            return MathematicalStatus.UNBOUNDED
        return MathematicalStatus.NOT_SOLVED
    raise TypeError(f"Unknown solution type: {type(solution).__name__}")
