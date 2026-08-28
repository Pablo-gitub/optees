from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Optional, Tuple

from optees.domain.entities.scenario.constraint import ScenarioConstraint
from optees.domain.entities.scenario.scenario import Scenario
from optees.domain.entities.scenario.shared_objective import (
    ScenarioSharedObjective,
)
from optees.domain.entities.scenario.variable import ScenarioVariable
from optees.domain.value_objects.scenario.scenario_options import ScenarioOptions
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


@dataclass(frozen=True)
class ScenarioModel:
    """Immutable aggregate root for finite linear robust scenario optimization."""

    orientation: ScenarioOrientation
    variables: Tuple[ScenarioVariable, ...]
    scenarios: Tuple[Scenario, ...]
    shared_objective: Optional[ScenarioSharedObjective] = None
    shared_constraints: Tuple[ScenarioConstraint, ...] = ()
    options: ScenarioOptions = field(default_factory=ScenarioOptions)

    def __post_init__(self) -> None:
        # Orientation validation
        orient = (
            self.orientation
            if isinstance(self.orientation, ScenarioOrientation)
            else ScenarioOrientation.from_str(self.orientation)
        )
        object.__setattr__(self, "orientation", orient)

        # Variables validation
        vars_t = tuple(self.variables or ())
        if not vars_t:
            raise ValueError("ScenarioModel must contain at least one variable.")
        if len(vars_t) > 500:
            raise ValueError(f"ScenarioModel variables count {len(vars_t)} exceeds limit of 500.")

        seen_var_names: set[str] = set()
        for idx, var in enumerate(vars_t):
            if not isinstance(var, ScenarioVariable):
                raise ValueError(f"variables[{idx}] must be a ScenarioVariable, got {var!r}")
            if var.name in seen_var_names:
                raise ValueError(f"Duplicate variable name: {var.name!r}")
            seen_var_names.add(var.name)
        object.__setattr__(self, "variables", vars_t)
        n = len(vars_t)

        # Scenarios validation
        scens_t = tuple(self.scenarios or ())
        if not scens_t:
            raise ValueError("ScenarioModel must contain at least one scenario.")
        if len(scens_t) > 2000:
            raise ValueError(f"ScenarioModel scenarios count {len(scens_t)} exceeds limit of 2000.")

        seen_scen_ids: set[str] = set()
        validated_scenarios: list[Scenario] = []
        for idx, scen in enumerate(scens_t):
            if not isinstance(scen, Scenario):
                raise ValueError(f"scenarios[{idx}] must be a Scenario, got {scen!r}")
            if scen.id in seen_scen_ids:
                raise ValueError(f"Duplicate scenario ID: {scen.id!r}")
            seen_scen_ids.add(scen.id)
            if len(scen.coefficients) != n:
                raise ValueError(
                    f"Scenario {scen.id!r} has {len(scen.coefficients)} coefficients, "
                    f"but model declares {n} variables."
                )
            validated_scenarios.append(scen)
        object.__setattr__(self, "scenarios", tuple(validated_scenarios))

        # Shared objective validation
        if self.shared_objective is not None:
            if not isinstance(self.shared_objective, ScenarioSharedObjective):
                raise ValueError(
                    f"shared_objective must be a ScenarioSharedObjective, got {self.shared_objective!r}"
                )
            if len(self.shared_objective.coefficients) != n:
                raise ValueError(
                    f"shared_objective has {len(self.shared_objective.coefficients)} coefficients, "
                    f"but model declares {n} variables."
                )

        # Shared constraints validation
        cons_t = tuple(self.shared_constraints or ())
        if len(cons_t) > 1000:
            raise ValueError(
                f"ScenarioModel constraints count {len(cons_t)} exceeds limit of 1000."
            )

        for idx, con in enumerate(cons_t):
            if not isinstance(con, ScenarioConstraint):
                raise ValueError(
                    f"shared_constraints[{idx}] must be a ScenarioConstraint, got {con!r}"
                )
            if len(con.coefficients) != n:
                raise ValueError(
                    f"shared_constraints[{idx}] has {len(con.coefficients)} coefficients, "
                    f"but model declares {n} variables."
                )
        object.__setattr__(self, "shared_constraints", cons_t)

        # Options validation
        opts = self.options if isinstance(self.options, ScenarioOptions) else ScenarioOptions()
        object.__setattr__(self, "options", opts)

    def n_vars(self) -> int:
        return len(self.variables)

    def n_scenarios(self) -> int:
        return len(self.scenarios)

    def n_constraints(self) -> int:
        return len(self.shared_constraints)

    def is_discrete(self) -> bool:
        return any(v.integrality.is_discrete() for v in self.variables)

    def variable_names(self) -> Tuple[str, ...]:
        return tuple(v.name for v in self.variables)

    def scenario_ids(self) -> Tuple[str, ...]:
        return tuple(s.id for s in self.scenarios)

    def combined_scenario_coefficients(self, k: int) -> Tuple[float, ...]:
        """Return combined linear coefficient vector d^(k) = c^(0) + c^(k)."""
        scen = self.scenarios[k]
        if self.shared_objective is None:
            return scen.coefficients
        base_c = self.shared_objective.coefficients
        return tuple(b + s for b, s in zip(base_c, scen.coefficients))

    def combined_scenario_offset(self, k: int) -> float:
        """Return combined scalar offset delta_k = gamma_0 + gamma_k."""
        scen = self.scenarios[k]
        base_off = self.shared_objective.offset if self.shared_objective is not None else 0.0
        return float(base_off + scen.offset)

    def evaluate_scenario(self, k: int, x: Mapping[str, float] | Sequence[float]) -> float:
        """Evaluate linear expression v_k(x) = d^(k)^T x + delta_k under scenario k."""
        d_k = self.combined_scenario_coefficients(k)
        delta_k = self.combined_scenario_offset(k)

        if isinstance(x, Mapping):
            total = sum(d_k[j] * float(x[v.name]) for j, v in enumerate(self.variables))
        else:
            if len(x) != len(self.variables):
                raise ValueError(
                    f"Candidate vector length {len(x)} does not match variable count {len(self.variables)}"
                )
            total = sum(c * float(val) for c, val in zip(d_k, x))
        return float(total + delta_k)

    def evaluate_all_scenarios(self, x: Mapping[str, float] | Sequence[float]) -> Tuple[float, ...]:
        return tuple(self.evaluate_scenario(k, x) for k in range(self.n_scenarios()))

    def evaluate_worst_case(self, x: Mapping[str, float] | Sequence[float]) -> float:
        vals = self.evaluate_all_scenarios(x)
        if self.orientation.is_loss_minimization():
            return max(vals)
        return min(vals)

    def binding_scenario_ids(
        self,
        x: Mapping[str, float] | Sequence[float],
        tolerance: Optional[float] = None,
    ) -> Tuple[str, ...]:
        """Return list of scenario IDs whose evaluation matches the worst-case value within tolerance."""
        tol = float(tolerance) if tolerance is not None else self.options.binding_tolerance
        vals = self.evaluate_all_scenarios(x)
        if self.orientation.is_loss_minimization():
            worst = max(vals)
            threshold = worst - tol * max(1.0, abs(worst))
            return tuple(self.scenarios[k].id for k, v in enumerate(vals) if v >= threshold - 1e-14)
        else:
            worst = min(vals)
            threshold = worst + tol * max(1.0, abs(worst))
            return tuple(self.scenarios[k].id for k, v in enumerate(vals) if v <= threshold + 1e-14)
