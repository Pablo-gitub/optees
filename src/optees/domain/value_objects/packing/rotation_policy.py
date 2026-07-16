from __future__ import annotations

from enum import Enum


class RotationPolicy(str, Enum):
    FIXED = "fixed"
    KEEP_UPRIGHT = "keep_upright"
    X_ONLY = "x_only"
    Y_ONLY = "y_only"
    Z_ONLY = "z_only"
    ANY_ORTHOGONAL = "any_orthogonal"
    CUSTOM = "custom"

    @staticmethod
    def from_str(value: object) -> "RotationPolicy":
        token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "none": RotationPolicy.FIXED,
            "upright": RotationPolicy.KEEP_UPRIGHT,
            "x": RotationPolicy.X_ONLY,
            "y": RotationPolicy.Y_ONLY,
            "z": RotationPolicy.Z_ONLY,
            "any": RotationPolicy.ANY_ORTHOGONAL,
            "all": RotationPolicy.ANY_ORTHOGONAL,
        }
        if token in aliases:
            return aliases[token]
        try:
            return RotationPolicy(token)
        except ValueError as exc:
            raise ValueError(f"unsupported rotation policy: {value!r}") from exc
