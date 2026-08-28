from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence, Tuple


@dataclass(frozen=True)
class Scenario:
    """Individual scenario declaring linear coefficients and constant offset."""

    id: str
    label: str = ""
    coefficients: Tuple[float, ...] = ()
    offset: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError(f"Scenario id must be a non-empty string, got {self.id!r}")
        clean_id = self.id.strip()
        object.__setattr__(self, "id", clean_id)
        object.__setattr__(self, "label", str(self.label or ""))

        coefs = tuple(float(c) for c in self.coefficients)
        for idx, c in enumerate(coefs):
            if not math.isfinite(c):
                raise ValueError(
                    f"Scenario {clean_id!r} coefficient at index {idx} must be a finite number, got {c!r}"
                )
        object.__setattr__(self, "coefficients", coefs)

        off = float(self.offset) if self.offset is not None else 0.0
        if not math.isfinite(off):
            raise ValueError(f"Scenario {clean_id!r} offset must be a finite number, got {off!r}")
        object.__setattr__(self, "offset", off)

    def with_size(self, n: int) -> Scenario:
        """Pad or truncate coefficients to length n."""
        current = list(self.coefficients)
        if len(current) < n:
            current.extend([0.0] * (n - len(current)))
        elif len(current) > n:
            current = current[:n]
        return Scenario(
            id=self.id,
            label=self.label,
            coefficients=tuple(current),
            offset=self.offset,
        )

    def with_coefficients(self, coefs: Sequence[float]) -> Scenario:
        return Scenario(
            id=self.id,
            label=self.label,
            coefficients=tuple(float(c) for c in coefs),
            offset=self.offset,
        )

    def with_offset(self, offset: float) -> Scenario:
        return Scenario(
            id=self.id,
            label=self.label,
            coefficients=self.coefficients,
            offset=float(offset),
        )
