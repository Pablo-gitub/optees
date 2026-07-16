from __future__ import annotations

from enum import Enum


class PackingGravityMode(str, Enum):
    NONE = "none"
    SIMPLE = "simple"

    @staticmethod
    def from_str(value: object) -> "PackingGravityMode":
        token = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "no_gravity": PackingGravityMode.NONE,
            "off": PackingGravityMode.NONE,
            "simple_gravity": PackingGravityMode.SIMPLE,
            "on": PackingGravityMode.SIMPLE,
        }
        if token in aliases:
            return aliases[token]
        try:
            return PackingGravityMode(token)
        except ValueError as exc:
            raise ValueError(f"unsupported packing gravity mode: {value!r}") from exc
