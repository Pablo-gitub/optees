from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from optees.domain.value_objects.lp.bounds import Bounds
from optees.domain.value_objects.milp.integrality import Integrality


@dataclass(frozen=True)
class ScenarioVariable:
    """Decision variable for scenario models with bounds and integrality."""

    name: str
    label: str = ""
    bounds: Bounds = field(default_factory=lambda: Bounds(0.0, None))
    integrality: Integrality = Integrality.CONTINUOUS

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError(f"ScenarioVariable name must be a non-empty string, got {self.name!r}")
        clean_name = self.name.strip()
        object.__setattr__(self, "name", clean_name)
        object.__setattr__(self, "label", str(self.label or ""))

        kind = (
            self.integrality
            if isinstance(self.integrality, Integrality)
            else Integrality.from_token(self.integrality)
        )
        object.__setattr__(self, "integrality", kind)

        if kind is Integrality.BINARY:
            object.__setattr__(self, "bounds", Bounds(0.0, 1.0))
        elif not isinstance(self.bounds, Bounds):
            raise ValueError(f"bounds must be an instance of Bounds, got {self.bounds!r}")

    def rename(self, new_name: str) -> ScenarioVariable:
        return ScenarioVariable(new_name, self.label, self.bounds, self.integrality)

    def relabel(self, new_label: str) -> ScenarioVariable:
        return ScenarioVariable(self.name, new_label, self.bounds, self.integrality)

    def with_bounds(self, lb: Optional[float], ub: Optional[float]) -> ScenarioVariable:
        if self.integrality is Integrality.BINARY:
            return ScenarioVariable(self.name, self.label, Bounds(0.0, 1.0), self.integrality)
        return ScenarioVariable(self.name, self.label, Bounds(lb, ub), self.integrality)

    def with_integrality(self, integrality: Union[str, Integrality, None]) -> ScenarioVariable:
        kind = Integrality.from_token(integrality)
        if kind is Integrality.BINARY:
            return ScenarioVariable(self.name, self.label, Bounds(0.0, 1.0), kind)
        return ScenarioVariable(self.name, self.label, self.bounds, kind)
