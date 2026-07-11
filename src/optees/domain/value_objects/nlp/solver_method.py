from __future__ import annotations

from enum import Enum


class NLPSolverMethod(str, Enum):
    BFGS = "BFGS"
    NELDER_MEAD = "Nelder-Mead"
    L_BFGS_B = "L-BFGS-B"

    @classmethod
    def from_str(cls, value: object) -> "NLPSolverMethod":
        normalized = str(value or "").strip().lower().replace("_", "-")
        aliases = {
            "bfgs": cls.BFGS,
            "nelder-mead": cls.NELDER_MEAD,
            "nelder mead": cls.NELDER_MEAD,
            "l-bfgs-b": cls.L_BFGS_B,
            "lbfgsb": cls.L_BFGS_B,
        }
        try:
            return aliases[normalized]
        except KeyError as exc:
            raise ValueError(f"invalid NLP solver method: {value!r}") from exc

    def supports_bounds(self) -> bool:
        return self is NLPSolverMethod.L_BFGS_B
