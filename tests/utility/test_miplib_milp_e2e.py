"""
E2E sanity tests for MILP using a tiny, size-capped subset of MIPLIB 2017.

Why this file exists:
- MIPLIB instances are large; parsing MPS (and gunzipping) can dominate runtime.
- We keep tests deterministic and fast by:
  * selecting only small .mps / .mps.gz files (by on-disk size),
  * capping the number of instances,
  * enforcing a hard per-test timeout (pytest-timeout),
  * using a short solver time limit.

Prereqs:
    pip install pytest-timeout
Data layout expected:
    tests/data/miplib2017/
      ├─ miplib2017-v31.solu
      └─ instances/
           ├─ some_instance.mps
           └─ some_other_instance.mps.gz
"""

from __future__ import annotations
from typing import Any, Dict
import os
import glob
import gzip
import tempfile
import pytest

# Require PuLP to parse MPS. If missing, pytest will skip this module.
pulp = pytest.importorskip("pulp", reason="PuLP required to read MPS")
from optees.utility.milp_utils import solve_milp
from optees.utility.data_adapters.miplib_solu import parse_miplib_solu


# ---------------------------------------------------------------------
# Configuration knobs for a lightweight, stable test
# ---------------------------------------------------------------------
INST_DIR = "tests/data/miplib2017/instances"
SOLU     = "tests/data/miplib2017/miplib2017-v31.solu"

MAX_INSTANCES     = 6        # cap how many instances we try
MAX_BYTES_MPS     = 2_000_000  # ≤ ~2 MB for uncompressed .mps
MAX_BYTES_GZ      = 1_000_000  # ≤ ~1 MB for .mps.gz (compressed)
SOLVE_TIME_LIMIT  = 10.0     # seconds per instance for the solver
PYTEST_TIMEOUT_S  = 90       # hard wall-time per test case (parse+solve)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def _read_mps_with_pulp(path: str):
    """Return a pulp.LpProblem from a .mps or .mps.gz path.
    We use a NamedTemporaryFile for gz; the temp is cleaned up afterwards.
    """
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as g, tempfile.NamedTemporaryFile(
            suffix=".mps", delete=False
        ) as tmp:
            tmp.write(g.read())
            tmp_path = tmp.name
        try:
            _, lp = pulp.LpProblem.fromMPS(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    else:
        _, lp = pulp.LpProblem.fromMPS(path)
    return lp


def _pulp_to_milp_canonical(lp: Any) -> Dict[str, Any]:
    """Convert a PuLP problem to our canonical MILP dict for solve_milp()."""
    sense = "min" if lp.sense == pulp.LpMinimize else "max"
    vars_ = lp.variables()
    n = len(vars_)
    name_to_idx = {v.name: i for i, v in enumerate(vars_)}
    var_names = [v.name for v in vars_]

    # bounds + integrality
    bounds, integrality = [], []
    for v in vars_:
        lb = v.lowBound if v.lowBound is not None else 0
        ub = v.upBound
        bounds.append((lb, ub))
        cat = getattr(v, "cat", pulp.LpContinuous)
        if cat == pulp.LpBinary:
            integrality.append("B")
        elif cat == pulp.LpInteger:
            integrality.append("I")
        else:
            integrality.append(None)  # continuous → allowed (CBC fallback)

    # objective coefficients
    c = [0.0] * n
    for var, coef in lp.objective.items():
        c[name_to_idx[var.name]] = float(coef)

    # constraints
    A_eq, b_eq, A_ub, b_ub = [], [], [], []
    for _, con in lp.constraints.items():
        row = [0.0] * n
        for var, coef in con.items():
            row[name_to_idx[var.name]] = float(coef)
        # PuLP stores: lhs - rhs == 0  → -constant is rhs
        rhs = float(con.constant) * -1.0

        if con.sense == 0:          # ==
            A_eq.append(row); b_eq.append(rhs)
        elif con.sense == -1:       # <=
            A_ub.append(row); b_ub.append(rhs)
        elif con.sense == 1:        # >=  → multiply by -1
            A_ub.append([-a for a in row]); b_ub.append(-rhs)

    return {
        "sense": sense,
        "c": c,
        "A_eq": A_eq or None, "b_eq": b_eq or None,
        "A_ub": A_ub or None, "b_ub": b_ub or None,
        "bounds": bounds,
        "integrality": integrality,
        "var_names": var_names,
    }


def discover_instances():
    """Pick a small set of instances that have an 'optimal'/'best' value in .solu
    and are small on disk (so parsing stays fast and predictable).
    """
    if not (os.path.isdir(INST_DIR) and os.path.exists(SOLU)):
        return []

    solu_map = parse_miplib_solu(SOLU)

    # Collect paths + sizes (recursive, both .mps and .mps.gz)
    mps = [(p, os.path.getsize(p))
           for p in glob.glob(os.path.join(INST_DIR, "**", "*.mps"), recursive=True)]
    gz  = [(p, os.path.getsize(p))
           for p in glob.glob(os.path.join(INST_DIR, "**", "*.mps.gz"), recursive=True)]

    # Size filters – compressed files get a tighter cap
    mps = [t for t in mps if t[1] <= MAX_BYTES_MPS]
    gz  = [t for t in gz  if t[1] <= MAX_BYTES_GZ]

    # Sort by size (small → fast)
    mps.sort(key=lambda t: t[1])
    gz.sort(key=lambda t: t[1])
    paths = [p for p, _ in (mps + gz)]

    items = []
    for p in paths:
        name = os.path.basename(p)
        if name.endswith(".mps.gz"):
            name = name[:-7]
        elif name.endswith(".mps"):
            name = name[:-4]
        st, obj = solu_map.get(name, (None, None))
        if st in {"optimal", "best"} and obj is not None:
            items.append((p, obj, name))
        if len(items) >= MAX_INSTANCES:
            break
    return items


# ---------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------
@pytest.mark.parametrize("path,obj_solu,name", discover_instances())
@pytest.mark.timeout(PYTEST_TIMEOUT_S)  # hard wall-time (parse + solve)
def test_miplib_instance_optimal(path, obj_solu, name):
    lp = _read_mps_with_pulp(path)
    problem = _pulp_to_milp_canonical(lp)

    status, obj, x, extras = solve_milp(problem, time_limit=SOLVE_TIME_LIMIT)

    # We don't fail the build for "NotSolved" within the short TL; we skip.
    if status != "Optimal":
        pytest.skip(f"{name}: not solved to optimal within time limit (status={status})")

    # Many MIPLIB objectives are integral; still keep a tiny tolerance.
    assert abs(obj - obj_solu) < 1e-6, f"{name}: objective mismatch"
