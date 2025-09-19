from __future__ import annotations
from typing import Dict, Tuple, Optional
import re

_STATUS_KEYS = {"optimal", "infeasible", "unbounded", "best", "feasible", "limit", "unknown"}
_V31_MAP = {"opt": "optimal", "best": "best", "inf": "infeasible", "unbd": "unbounded", "unkn": "unknown"}

def parse_miplib_solu(path: str) -> Dict[str, Tuple[str, Optional[float]]]:
    """
    Parse a MIPLIB .solu file into: { instance_name: (status, objective or None) }.
    Supports both the 'v31' style lines (e.g., '=opt= inst 123.0 ...')
    and the older 'name status value' or 'status name value' styles.
    """
    out: Dict[str, Tuple[str, Optional[float]]] = {}
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue

            # v31 style: =opt= <name> [objective]
            m = re.match(r"^=([a-zA-Z]+)=\s+(\S+)(?:\s+([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?))?", line)
            if m:
                key, name, obj = m.groups()
                status = _V31_MAP.get(key.lower(), key.lower())
                val = float(obj) if obj is not None else None
                out[name] = (status, val)
                continue

            # permissive fallback: look for a status token somewhere and a trailing numeric as objective
            parts = line.split()
            status_idx = None
            for i, tok in enumerate(parts):
                if tok.lower() in _STATUS_KEYS:
                    status_idx = i
                    break
            if status_idx is None:
                continue
            status = parts[status_idx].lower()
            name = None
            if status_idx > 0:
                name = parts[status_idx - 1]
            elif status_idx + 1 < len(parts):
                name = parts[status_idx + 1]
            if not name:
                continue
            obj = None
            for tok in reversed(parts):
                try:
                    obj = float(tok)
                    break
                except ValueError:
                    pass
            out[name] = (status, obj)
    return out
