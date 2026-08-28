from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ScenarioValue:
    """Individual scenario evaluation value and binding status."""

    scenario_id: str
    value: float
    is_binding: bool

    def __post_init__(self) -> None:
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError(
                f"ScenarioValue scenario_id must be a non-empty string, got {self.scenario_id!r}"
            )
        object.__setattr__(self, "scenario_id", self.scenario_id.strip())

        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not math.isfinite(float(self.value))
        ):
            raise ValueError(f"ScenarioValue value must be a finite number, got {self.value!r}")
        object.__setattr__(self, "value", float(self.value))

        if not isinstance(self.is_binding, bool):
            raise ValueError(f"ScenarioValue is_binding must be a boolean, got {self.is_binding!r}")
