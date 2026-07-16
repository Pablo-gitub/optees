from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ORLibraryBoxType:
    type_id: int
    dimensions: tuple[int, int, int]
    vertical_allowed: tuple[bool, bool, bool]
    quantity: int


@dataclass(frozen=True)
class ORLibraryThpackInstance:
    problem_number: int
    seed: int
    container_dimensions: tuple[int, int, int]
    box_types: tuple[ORLibraryBoxType, ...]

    def unit_count(self) -> int:
        return sum(box.quantity for box in self.box_types)


def read_orlib_thpack(path: Path) -> tuple[ORLibraryThpackInstance, ...]:
    """Read Bischoff/Ratcliff `thpack1`-`thpack7` OR-Library files."""

    tokens = path.read_text(encoding="ascii").split()
    cursor = 0

    def take(label: str) -> int:
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError(f"unexpected end of thpack data while reading {label}")
        try:
            value = int(tokens[cursor])
        except ValueError as exc:
            raise ValueError(f"invalid integer for {label}: {tokens[cursor]!r}") from exc
        cursor += 1
        return value

    problem_count = take("problem count")
    if problem_count <= 0:
        raise ValueError("thpack problem count must be positive")

    instances = []
    for problem_index in range(problem_count):
        number = take(f"problem[{problem_index}].number")
        seed = take(f"problem[{problem_index}].seed")
        container = tuple(
            take(f"problem[{problem_index}].container[{axis}]") for axis in range(3)
        )
        type_count = take(f"problem[{problem_index}].type_count")
        if any(value <= 0 for value in container) or type_count <= 0:
            raise ValueError("thpack dimensions and type counts must be positive")

        box_types = []
        for type_index in range(type_count):
            type_id = take(f"problem[{problem_index}].box[{type_index}].id")
            dimensions = []
            vertical_allowed = []
            for axis in range(3):
                dimensions.append(
                    take(f"problem[{problem_index}].box[{type_index}].dimension[{axis}]")
                )
                flag = take(
                    f"problem[{problem_index}].box[{type_index}].vertical[{axis}]"
                )
                if flag not in (0, 1):
                    raise ValueError("thpack vertical-orientation flags must be 0 or 1")
                vertical_allowed.append(bool(flag))
            quantity = take(f"problem[{problem_index}].box[{type_index}].quantity")
            if any(value <= 0 for value in dimensions) or quantity <= 0:
                raise ValueError("thpack box dimensions and quantities must be positive")
            box_types.append(
                ORLibraryBoxType(
                    type_id=type_id,
                    dimensions=tuple(dimensions),  # type: ignore[arg-type]
                    vertical_allowed=tuple(vertical_allowed),  # type: ignore[arg-type]
                    quantity=quantity,
                )
            )
        instances.append(
            ORLibraryThpackInstance(
                problem_number=number,
                seed=seed,
                container_dimensions=container,  # type: ignore[arg-type]
                box_types=tuple(box_types),
            )
        )

    if cursor != len(tokens):
        raise ValueError("unexpected trailing values in thpack data")
    return tuple(instances)
