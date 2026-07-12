from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphVertex:
    """A graph vertex with a stable identifier and optional human label."""

    identifier: str
    label: str = ""

    def __post_init__(self) -> None:
        identifier = str(self.identifier or "").strip()
        if not identifier:
            raise ValueError("graph vertex identifier must not be empty")
        if len(identifier) > 64:
            raise ValueError("graph vertex identifier must contain at most 64 characters")
        if any(character.isspace() for character in identifier):
            raise ValueError("graph vertex identifier must not contain whitespace")
        object.__setattr__(self, "identifier", identifier)
        object.__setattr__(self, "label", str(self.label or "").strip())
