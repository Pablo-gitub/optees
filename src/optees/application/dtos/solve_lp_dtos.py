# src/optees/application/dtos/solve_lp_dtos.py
from __future__ import annotations
from dataclasses import dataclass
from optees.domain.models.lp.lp_model import LPModel
from optees.domain.entities.lp.solution import LPSolution

@dataclass(frozen=True)
class SolveLPRequestDTO:
    """Use case input: domain LP + optional solver method choice."""
    model: LPModel
    method: str = "highs"

# Option A (recommended): the use case returns LPSolution directly.
# Option B: keep a thin DTO wrapping the domain object.
@dataclass(frozen=True)
class SolveResultDTO:
    solution: LPSolution
