from __future__ import annotations

from enum import Enum


class ClassificationMethod(str, Enum):
    """Transparent estimators available in the first binary workflow."""

    LOGISTIC_REGRESSION = "LogisticRegression"

    @classmethod
    def from_str(cls, value: object) -> "ClassificationMethod":
        normalized = str(value).strip().lower().replace("_", "-")
        aliases = {
            "logisticregression": cls.LOGISTIC_REGRESSION,
            "logistic-regression": cls.LOGISTIC_REGRESSION,
            "logistic": cls.LOGISTIC_REGRESSION,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"unsupported classification method: {value!r}") from exc
