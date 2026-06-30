from __future__ import annotations

from enum import Enum


class KnapsackVariant(str, Enum):
    ZERO_ONE = "zero_one"
    BOUNDED = "bounded"
    UNBOUNDED = "unbounded"
    FRACTIONAL = "fractional"
    MULTI_DIMENSIONAL = "multi_dimensional"

    @staticmethod
    def implemented() -> set["KnapsackVariant"]:
        return {KnapsackVariant.ZERO_ONE}
