from __future__ import annotations

from optees.application.dtos.multi_dimensional_knapsack_dtos import (
    MultiDimensionalKnapsackRequest,
)
from optees.application.ports.milp_solver_port import MILPSolverPort
from optees.application.ports.multi_dimensional_knapsack_solver_port import (
    MultiDimensionalKnapsackSolverPort,
)
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.application.usecases.solve_multi_dimensional_knapsack_usecase import (
    SolveMultiDimensionalKnapsackUseCase,
)
from optees.domain.entities.knapsack.multi_dimensional_quantity_solution import (
    MultiDimensionalQuantityKnapsackSolution,
)
from optees.domain.entities.knapsack.multi_dimensional_solution import (
    MultiDimensionalKnapsackSolution,
)
from optees.domain.entities.lp.constraint import Constraint
from optees.domain.entities.lp.objective import Objective
from optees.domain.entities.milp.variable import MILPVariable
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.relation import Relation
from optees.domain.value_objects.milp.integrality import Integrality
from optees.utility.knapsack_json_io import (
    DOMAIN_BOUNDED,
    DOMAIN_FRACTIONAL,
    DOMAIN_UNBOUNDED,
    DOMAIN_ZERO_ONE,
)


MultiDimensionalResult = (
    MultiDimensionalKnapsackSolution | MultiDimensionalQuantityKnapsackSolution
)


class SolveMultiDimensionalKnapsackCapabilityUseCase:
    def __init__(
        self,
        binary_solver_port: MultiDimensionalKnapsackSolverPort,
        milp_solver_port: MILPSolverPort,
    ) -> None:
        self._binary_use_case = SolveMultiDimensionalKnapsackUseCase(binary_solver_port)
        self._milp_use_case = SolveMILPUseCase(milp_solver_port)

    def execute(self, request: MultiDimensionalKnapsackRequest) -> MultiDimensionalResult:
        if request.domain == DOMAIN_ZERO_ONE:
            return self._binary_use_case.execute(request.model)

        milp_model, variable_names = _build_milp_model(request)
        milp_solution = self._milp_use_case.execute(milp_model)
        quantities = tuple(
            float(milp_solution.values.get(name, 0.0)) for name in variable_names
        )
        extras = dict(milp_solution.extras)
        extras["method"] = extras.get("method") or _method_for_domain(request.domain)
        extras["multi_domain"] = request.domain
        extras["item_count"] = request.model.n_items()
        extras["resource_count"] = request.model.n_resources()
        extras["resource_names"] = list(request.model.resource_names())
        extras["capacities"] = list(request.model.capacities())
        return MultiDimensionalQuantityKnapsackSolution.from_model_quantities(
            request.model,
            status=milp_solution.status.value,
            objective=milp_solution.objective,
            quantities=quantities,
            extras=extras,
        )


def _build_milp_model(
    request: MultiDimensionalKnapsackRequest,
) -> tuple[MILPModel, tuple[str, ...]]:
    model = request.model
    variable_names = tuple(f"item_{index + 1}" for index in range(model.n_items()))
    integrality = (
        Integrality.CONTINUOUS
        if request.domain == DOMAIN_FRACTIONAL
        else Integrality.INTEGER
    )
    variables = tuple(
        MILPVariable(
            name=variable_names[index],
            label=item.name,
            bounds=Bounds(0.0, request.upper_bounds[index]),
            integrality=integrality,
        )
        for index, item in enumerate(model.items)
    )
    objective = Objective(
        sense=ObjectiveSense.MAX,
        coefs=tuple(item.value for item in model.items),
    )
    constraints = tuple(
        Constraint(
            tuple(item.resource_usage[resource_index] for item in model.items),
            Relation.LE,
            resource.capacity,
        )
        for resource_index, resource in enumerate(model.resources)
    )
    return MILPModel.from_parts(variables, objective, constraints), variable_names


def _method_for_domain(domain: str) -> str:
    return {
        DOMAIN_BOUNDED: "multidimensional_bounded_milp",
        DOMAIN_UNBOUNDED: "multidimensional_unbounded_milp",
        DOMAIN_FRACTIONAL: "multidimensional_fractional_lp",
    }[domain]
