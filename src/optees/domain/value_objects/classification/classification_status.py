from __future__ import annotations

from enum import Enum


class ClassificationStatus(str, Enum):
    TRAINED = "Trained"
    FAILED = "Failed"
    NOT_TRAINED = "NotTrained"

    @classmethod
    def from_str(cls, value: object) -> "ClassificationStatus":
        normalized = str(value).strip().lower().replace("_", "")
        aliases = {
            "trained": cls.TRAINED,
            "failed": cls.FAILED,
            "nottrained": cls.NOT_TRAINED,
        }
        return aliases.get(normalized, cls.NOT_TRAINED)
