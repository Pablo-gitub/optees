from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Dict, Optional, Tuple, Union

from optees.application.contracts.execution import MathematicalStatus
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.entities.scenario.scenario_value import ScenarioValue
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


@dataclass(frozen=True)
class ScenarioResult:
    """Immutable domain result for robust scenario optimization."""

    status: MathematicalStatus
    orientation: ScenarioOrientation
    guaranteed_value: Optional[float]
    variables: Optional[Dict[str, float]]
    scenario_values: Tuple[ScenarioValue, ...]
    binding_scenario_ids: Tuple[str, ...]
    delegated_solution: Union[LPSolution, MILPSolution]
    auxiliary_variable_name: str
    auxiliary_value: Optional[float]

    def __post_init__(self) -> None:
        if not isinstance(self.status, MathematicalStatus):
            raise ValueError(f"status must be a MathematicalStatus, got {self.status!r}")
        if not isinstance(self.orientation, ScenarioOrientation):
            raise ValueError(f"orientation must be a ScenarioOrientation, got {self.orientation!r}")
        if not isinstance(self.delegated_solution, (LPSolution, MILPSolution)):
            raise ValueError(
                f"delegated_solution must be LPSolution or MILPSolution, got {type(self.delegated_solution).__name__}"
            )
        if (
            not isinstance(self.auxiliary_variable_name, str)
            or not self.auxiliary_variable_name.strip()
        ):
            raise ValueError(
                f"auxiliary_variable_name must be a non-empty string, got {self.auxiliary_variable_name!r}"
            )

        has_candidate = self.status in (
            MathematicalStatus.OPTIMAL,
            MathematicalStatus.FEASIBLE,
        )
        if has_candidate:
            if (
                self.guaranteed_value is None
                or isinstance(self.guaranteed_value, bool)
                or not isinstance(self.guaranteed_value, (int, float))
                or not math.isfinite(float(self.guaranteed_value))
            ):
                raise ValueError(
                    f"guaranteed_value must be a finite number for status {self.status.value}, got {self.guaranteed_value!r}"
                )
            object.__setattr__(self, "guaranteed_value", float(self.guaranteed_value))

            if not isinstance(self.variables, dict):
                raise ValueError(
                    f"variables mapping must be provided for status {self.status.value}"
                )
            # Ensure variable values are finite
            for k, v in self.variables.items():
                if (
                    isinstance(v, bool)
                    or not isinstance(v, (int, float))
                    or not math.isfinite(float(v))
                ):
                    raise ValueError(f"Variable {k!r} has non-finite value {v!r}")

            if (
                self.auxiliary_value is None
                or isinstance(self.auxiliary_value, bool)
                or not isinstance(self.auxiliary_value, (int, float))
                or not math.isfinite(float(self.auxiliary_value))
            ):
                raise ValueError(
                    f"auxiliary_value must be a finite number for status {self.status.value}, got {self.auxiliary_value!r}"
                )
            object.__setattr__(self, "auxiliary_value", float(self.auxiliary_value))

            if not isinstance(self.scenario_values, tuple):
                object.__setattr__(self, "scenario_values", tuple(self.scenario_values or ()))
            if not isinstance(self.binding_scenario_ids, tuple):
                object.__setattr__(
                    self, "binding_scenario_ids", tuple(self.binding_scenario_ids or ())
                )
        else:
            if self.guaranteed_value is not None:
                raise ValueError(f"guaranteed_value must be None for status {self.status.value}")
            if self.variables is not None:
                raise ValueError(f"variables must be None for status {self.status.value}")
            if self.auxiliary_value is not None:
                raise ValueError(f"auxiliary_value must be None for status {self.status.value}")
            if self.scenario_values:
                raise ValueError(f"scenario_values must be empty for status {self.status.value}")
            if self.binding_scenario_ids:
                raise ValueError(
                    f"binding_scenario_ids must be empty for status {self.status.value}"
                )
            object.__setattr__(self, "scenario_values", ())
            object.__setattr__(self, "binding_scenario_ids", ())

    def is_optimal(self) -> bool:
        return self.status is MathematicalStatus.OPTIMAL

    def has_candidate(self) -> bool:
        return (
            self.status in (MathematicalStatus.OPTIMAL, MathematicalStatus.FEASIBLE)
            and self.variables is not None
        )
