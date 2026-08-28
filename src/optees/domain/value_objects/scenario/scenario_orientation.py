from __future__ import annotations

from enum import Enum


class ScenarioOrientation(str, Enum):
    """Semantic orientation for linear robust scenario optimization."""

    MIN_MAX_LOSS = "minimize_maximum_loss"
    MAX_MIN_REWARD = "maximize_minimum_reward"

    @staticmethod
    def from_str(value: object) -> ScenarioOrientation:
        if isinstance(value, ScenarioOrientation):
            return value
        token = str(value or "").strip().lower()
        public_tokens = {
            "minimize_maximum_loss": ScenarioOrientation.MIN_MAX_LOSS,
            "maximize_minimum_reward": ScenarioOrientation.MAX_MIN_REWARD,
        }
        try:
            return public_tokens[token]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported scenario orientation {value!r}; "
                f"expected 'minimize_maximum_loss' or 'maximize_minimum_reward'."
            ) from exc

    def is_loss_minimization(self) -> bool:
        return self is ScenarioOrientation.MIN_MAX_LOSS

    def is_reward_maximization(self) -> bool:
        return self is ScenarioOrientation.MAX_MIN_REWARD
