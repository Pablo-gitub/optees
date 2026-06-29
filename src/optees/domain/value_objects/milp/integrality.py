from __future__ import annotations
from enum import Enum


class Integrality(str, Enum):
    """Decision-variable type for MILP models."""

    CONTINUOUS = "C"
    INTEGER = "I"
    BINARY = "B"

    @staticmethod
    def from_token(token: object) -> "Integrality":
        if isinstance(token, Integrality):
            return token
        value = "C" if token is None else str(token).strip().upper()
        aliases = {
            "": Integrality.CONTINUOUS,
            "C": Integrality.CONTINUOUS,
            "CONTINUOUS": Integrality.CONTINUOUS,
            "R": Integrality.CONTINUOUS,
            "REAL": Integrality.CONTINUOUS,
            "I": Integrality.INTEGER,
            "INTEGER": Integrality.INTEGER,
            "INT": Integrality.INTEGER,
            "Z": Integrality.INTEGER,
            "B": Integrality.BINARY,
            "BINARY": Integrality.BINARY,
            "BOOL": Integrality.BINARY,
            "BOOLEAN": Integrality.BINARY,
        }
        try:
            return aliases[value]
        except KeyError as exc:
            raise ValueError(f"Invalid integrality token: {token!r}") from exc

    def is_discrete(self) -> bool:
        return self in (Integrality.INTEGER, Integrality.BINARY)
