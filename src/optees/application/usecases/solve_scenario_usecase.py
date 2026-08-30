from __future__ import annotations

from typing import Union

from optees.application.services.scenario_reconstruction_service import (
    ScenarioReconstructionService,
)
from optees.application.services.scenario_reduction_service import (
    ScenarioReductionService,
)
from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.usecases.solve_milp_usecase import SolveMILPUseCase
from optees.domain.entities.lp.solution import LPSolution
from optees.domain.entities.milp.solution import MILPSolution
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.models.milp.milp_model import MILPModel
from optees.domain.models.scenario.scenario_model import ScenarioModel
from optees.domain.models.scenario.scenario_result import ScenarioResult


class SolveScenarioUseCase:
    """Application use case orchestrating robust linear scenario optimization.

    Follows the deterministic sequence:
    1. Validates input boundary.
    2. Reduces ScenarioModel exactly once via ScenarioReductionService.
    3. Routes the reduced model to exactly one delegated use case (SolveLPUseCase or SolveMILPUseCase).
    4. Reconstructs ScenarioResult exactly once via ScenarioReconstructionService.
    5. Returns the pure domain ScenarioResult without serialization or concrete adapter dependencies.
    """

    def __init__(
        self,
        solve_lp_usecase: SolveLPUseCase,
        solve_milp_usecase: SolveMILPUseCase,
    ) -> None:
        if not isinstance(solve_lp_usecase, SolveLPUseCase):
            raise TypeError(
                f"solve_lp_usecase must be an instance of SolveLPUseCase, got {type(solve_lp_usecase).__name__}"
            )
        if not isinstance(solve_milp_usecase, SolveMILPUseCase):
            raise TypeError(
                f"solve_milp_usecase must be an instance of SolveMILPUseCase, got {type(solve_milp_usecase).__name__}"
            )
        self._solve_lp = solve_lp_usecase
        self._solve_milp = solve_milp_usecase

    def execute(self, model: ScenarioModel) -> ScenarioResult:
        if not isinstance(model, ScenarioModel):
            raise TypeError(
                f"model must be an instance of ScenarioModel, got {type(model).__name__}"
            )

        # 1. Reduce ScenarioModel exactly once
        reduction = ScenarioReductionService.reduce(model)

        # 2. Route to exactly one delegated solver use case
        delegated_solution: Union[LPSolution, MILPSolution]
        if reduction.is_discrete:
            if not isinstance(reduction.model, MILPModel):
                raise TypeError(
                    f"Expected discrete reduction to produce MILPModel, got {type(reduction.model).__name__}"
                )
            delegated_solution = self._solve_milp.execute(reduction.model)
        else:
            if not isinstance(reduction.model, LPModel):
                raise TypeError(
                    f"Expected continuous reduction to produce LPModel, got {type(reduction.model).__name__}"
                )
            delegated_solution = self._solve_lp.execute(reduction.model)

        # 3. Reconstruct ScenarioResult exactly once
        return ScenarioReconstructionService.reconstruct(
            model,
            reduction,
            delegated_solution,
        )
