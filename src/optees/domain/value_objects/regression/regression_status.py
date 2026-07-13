from __future__ import annotations

from enum import Enum


class RegressionStatus(str, Enum):
    """Lifecycle state for a local regression training run."""

    TRAINED = "Trained"
    FAILED = "Failed"
    NOT_TRAINED = "NotTrained"

    @classmethod
    def from_str(cls, value: object) -> "RegressionStatus":
        aliases = {
            "trained": cls.TRAINED,
            "success": cls.TRAINED,
            "failed": cls.FAILED,
            "nottrained": cls.NOT_TRAINED,
            "not_trained": cls.NOT_TRAINED,
        }
        normalized = str(value or "").replace(" ", "").lower()
        return aliases.get(normalized, cls.NOT_TRAINED)
