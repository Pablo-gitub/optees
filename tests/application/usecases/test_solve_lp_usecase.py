# tests/application/usecases/test_solve_lp_usecase.py
from __future__ import annotations
from typing import Dict, Any

from optees.application.usecases.solve_lp_usecase import SolveLPUseCase
from optees.application.ports.lp_solver_port import LPSolverPort
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.value_objects.lp.objective_sense import ObjectiveSense
from optees.domain.value_objects.lp.solve_status import SolveStatus   # NEW

class FakeSolver(LPSolverPort):
    def __init__(self, response: Dict[str, Any]):
        self.calls = []
        self._response = response

    def solve(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        self.calls.append(problem)
        return self._response

def test_usecase_calls_port_and_maps_response():
    # Arrange: modello minimale con 2 variabili
    model = LPModel.empty(2).set_objective_sense(ObjectiveSense.MIN)

    fake = FakeSolver({
        "status": "Optimal",
        "objective": 42.0,
        "x": {"X1": 1.0, "X2": 2.0},
        "extras": {"method": "highs", "nit": 7},
    })
    uc = SolveLPUseCase(fake)

    # Act: ora execute accetta direttamente LPModel e ritorna LPSolution (domain)
    res = uc.execute(model, method="highs")

    # Assert: LPSolution domain
    assert res.status == SolveStatus.OPTIMAL
    assert res.objective == 42.0
    assert res.values == {"X1": 1.0, "X2": 2.0}
    assert res.diagnostics.method == "highs"
    assert res.diagnostics.nit == 7

    # Il port è stato chiamato una volta e si è portato dietro il method
    assert len(fake.calls) == 1
    called_problem = fake.calls[0]
    assert called_problem.get("method") == "highs"
