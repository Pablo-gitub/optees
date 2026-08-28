from __future__ import annotations

from dataclasses import dataclass
from typing import Union

from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.lp.variable import Variable
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.domain.value_objects.scenario.scenario_orientation import (
    ScenarioOrientation,
)


@dataclass(frozen=True)
class ScenarioReductionResult:
    """Exact epigraph/hypograph reduction outcome for a ScenarioModel."""

    model: Union[LPModel, MILPModel]
    auxiliary_variable_name: str
    auxiliary_variable_index: int
    orientation: ScenarioOrientation
    is_discrete: bool


class ScenarioReductionService:
    """Pure, deterministic reduction service transforming ScenarioModel into LPModel or MILPModel."""

    @staticmethod
    def reduce(model: ScenarioModel) -> ScenarioReductionResult:
        """Perform exact epigraph or hypograph reduction conforming to contract v1."""
        if not isinstance(model, ScenarioModel):
            raise TypeError(f"Expected ScenarioModel instance, got {type(model).__name__}")

        n = model.n_vars()
        is_discrete = model.is_discrete()
        is_loss = model.orientation.is_loss_minimization()

        # Deterministic collision-safe auxiliary variable naming
        base_name = "_aux_theta" if is_loss else "_aux_tau"
        user_names = {v.name for v in model.variables}
        aux_name = base_name
        suffix_counter = 1
        while aux_name in user_names:
            aux_name = f"{base_name}_{suffix_counter}"
            suffix_counter += 1

        aux_label = (
            "Robust scenario auxiliary epigraph loss variable"
            if is_loss
            else "Robust scenario auxiliary hypograph reward variable"
        )
        aux_bounds = Bounds(None, None)

        # Build reduced variable sequence
        if not is_discrete:
            lp_vars = tuple(
                Variable(name=v.name, label=v.label, bounds=v.bounds) for v in model.variables
            ) + (Variable(name=aux_name, label=aux_label, bounds=aux_bounds),)
        else:
            milp_vars = tuple(
                MILPVariable(
                    name=v.name,
                    label=v.label,
                    bounds=v.bounds,
                    integrality=v.integrality,
                )
                for v in model.variables
            ) + (
                MILPVariable(
                    name=aux_name,
                    label=aux_label,
                    bounds=aux_bounds,
                    integrality=Integrality.CONTINUOUS,
                ),
            )

        # Build reduced objective: min 1*theta or max 1*tau
        obj_sense = ObjectiveSense.MIN if is_loss else ObjectiveSense.MAX
        obj_coefs = tuple([0.0] * n + [1.0])
        reduced_objective = Objective(
            sense=obj_sense,
            coefs=obj_coefs,
            offset=0.0,
        )

        # Build reduced constraints: shared constraints followed by scenario constraints
        reduced_constraints: list[Constraint] = []

        # 1. Shared constraints (padded with 0 coefficient for auxiliary variable)
        for sc in model.shared_constraints:
            shared_coefs = tuple(list(sc.coefficients) + [0.0])
            reduced_constraints.append(
                Constraint(
                    coefs=shared_coefs,
                    relation=sc.relation,
                    rhs=sc.rhs,
                )
            )

        # 2. Scenario constraints
        for k in range(model.n_scenarios()):
            d_k = model.combined_scenario_coefficients(k)
            delta_k = model.combined_scenario_offset(k)

            if is_loss:
                # Epigraph: d^(k)^T x + delta_k <= theta  <=>  d^(k)^T x - theta <= -delta_k
                scen_coefs = tuple(list(d_k) + [-1.0])
                reduced_constraints.append(
                    Constraint(
                        coefs=scen_coefs,
                        relation=Relation.LE,
                        rhs=-delta_k,
                    )
                )
            else:
                # Hypograph: tau <= d^(k)^T x + delta_k  <=>  -d^(k)^T x + tau <= delta_k
                scen_coefs = tuple([-c for c in d_k] + [1.0])
                reduced_constraints.append(
                    Constraint(
                        coefs=scen_coefs,
                        relation=Relation.LE,
                        rhs=delta_k,
                    )
                )

        # Construct target model
        reduced_model: Union[LPModel, MILPModel]
        if not is_discrete:
            reduced_model = LPModel(
                variables=lp_vars,
                objective=reduced_objective,
                constraints=tuple(reduced_constraints),
            )
        else:
            reduced_model = MILPModel.from_parts(
                variables=milp_vars,
                objective=reduced_objective,
                constraints=reduced_constraints,
                time_limit=model.options.time_limit_seconds,
            )

        return ScenarioReductionResult(
            model=reduced_model,
            auxiliary_variable_name=aux_name,
            auxiliary_variable_index=n,
            orientation=model.orientation,
            is_discrete=is_discrete,
        )


def reduce_scenario_model(model: ScenarioModel) -> Union[LPModel, MILPModel]:
    """Convenience function returning the reduced LPModel or MILPModel."""
    return ScenarioReductionService.reduce(model).model
