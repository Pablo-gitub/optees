from __future__ import annotations

from enum import Enum


class RegressionMethod(str, Enum):
    """Transparent linear estimators offered by the first ML workflow."""

    OLS = "OLS"
    RIDGE = "Ridge"

    @classmethod
    def from_str(cls, value: object) -> "RegressionMethod":
        normalized = str(value or "").strip().lower().replace("_", "-")
        aliases = {
            "ols": cls.OLS,
            "linear": cls.OLS,
            "linear-regression": cls.OLS,
            "ordinary-least-squares": cls.OLS,
            "ridge": cls.RIDGE,
            "ridge-regression": cls.RIDGE,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"invalid regression method: {value!r}") from exc
