from __future__ import annotations

from dataclasses import dataclass

from optees.domain.value_objects.nlp.objective_sense import NLPObjectiveSense


@dataclass(frozen=True)
class NLPObjective:
    """A scalar nonlinear objective written in the safe expression language."""

    expression: str
    sense: NLPObjectiveSense = NLPObjectiveSense.MIN

    def __post_init__(self) -> None:
        if not isinstance(self.expression, str) or not self.expression.strip():
            raise ValueError("NLP objective expression must be a non-empty string")
        sense = (
            NLPObjectiveSense.from_str(self.sense)
            if not isinstance(self.sense, NLPObjectiveSense)
            else self.sense
        )
        object.__setattr__(self, "expression", self.expression.strip())
        object.__setattr__(self, "sense", sense)
