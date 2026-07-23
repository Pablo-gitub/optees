from __future__ import annotations

from importlib import import_module


def import_is_usable(module_name: str, *required_attributes: str) -> bool:
    """Return whether an optional backend can be imported and exposes its API."""
    try:
        module = import_module(module_name)
        return all(hasattr(module, attribute) for attribute in required_attributes)
    except Exception:
        return False


def scipy_highs_is_usable() -> bool:
    """Exercise the same compiled HiGHS path used by continuous LP jobs."""
    try:
        optimize = import_module("scipy.optimize")
        linprog = getattr(optimize, "linprog")
        result = linprog(
            [1.0],
            bounds=[(0.0, 0.0)],
            method="highs",
        )
        return bool(result.success) and int(result.status) == 0
    except Exception:
        return False
