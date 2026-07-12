from __future__ import annotations

from enum import Enum


class ShortestPathStatus(str, Enum):
    PATH_FOUND = "PathFound"
    UNREACHABLE = "Unreachable"
    NOT_SOLVED = "NotSolved"

    @classmethod
    def from_str(cls, value: object) -> "ShortestPathStatus":
        normalized = str(value or "").strip().lower().replace("_", "")
        return {
            "pathfound": cls.PATH_FOUND,
            "optimal": cls.PATH_FOUND,
            "unreachable": cls.UNREACHABLE,
        }.get(normalized, cls.NOT_SOLVED)
