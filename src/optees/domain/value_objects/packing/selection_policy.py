from __future__ import annotations

from enum import Enum


class PackingSelectionPolicy(str, Enum):
    OPTIONAL = "optional"
    ALL_REQUIRED = "all_required"

    @staticmethod
    def from_str(value: object) -> "PackingSelectionPolicy":
        token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "maximize": PackingSelectionPolicy.OPTIONAL,
            "required": PackingSelectionPolicy.ALL_REQUIRED,
            "all": PackingSelectionPolicy.ALL_REQUIRED,
        }
        if token in aliases:
            return aliases[token]
        try:
            return PackingSelectionPolicy(token)
        except ValueError as exc:
            raise ValueError(f"unsupported packing selection policy: {value!r}") from exc
