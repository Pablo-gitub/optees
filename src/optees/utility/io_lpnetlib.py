"""
Adapter for LPnetlib (.mat) problems (SuiteSparse Matrix Collection).

This loader tries to be resilient to different field namings and structures:
- Either a top-level dict or a 'Problem' struct is present.
- Objective vector `c` may live under `aux.c` (or `aux.f`, `aux.cost`) rather than top-level.
- Row bounds can be given as `rl/ru` (lower/upper row bounds) or as a single RHS `b` (Ax = b).
- Variable bounds often appear as `lo/hi` (lower/upper variable bounds).
- Some instances provide an objective constant term `z0` (objective offset).

The function returns a canonical problem dict for `solve_lp(...)`:
{
    "sense": "min",
    "c": [...],
    "A_eq": scipy.sparse.csr_matrix,   # optional
    "b_eq": [...],                     # optional
    "A_ub": scipy.sparse.csr_matrix,   # optional
    "b_ub": [...],                     # optional
    "bounds": [[lb, ub], ...],
    "var_names": ["x0","x1",...],
    "obj_offset": <float>,             # optional, if present in .mat
    "metadata": {"source": "LPnetlib", "path": <path>}
}
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.io import loadmat
from scipy import sparse


__all__ = ["load_lpnetlib_mat"]


# ---------------------------
# helpers
# ---------------------------

def _fetch_field(container: Any, *names: str):
    """Return the first matching field among `names` from a MATLAB struct-like object or a dict."""
    # MATLAB struct (mat_struct) via attribute access
    for n in names:
        if hasattr(container, n):
            return getattr(container, n)
    # Top-level dict (from loadmat) via keys
    if isinstance(container, dict):
        for n in names:
            if n in container:
                return container[n]
    return None


def _fetch_primary_then_aux(primary: Any, aux: Any, *names: str):
    """Try to fetch from primary; if not found, try from aux."""
    v = _fetch_field(primary, *names)
    if v is None and aux is not None:
        v = _fetch_field(aux, *names)
    return v


def _ensure_1d_float(arr: Any) -> np.ndarray:
    """Convert input to 1D float ndarray."""
    return np.atleast_1d(np.asarray(arr, dtype=float)).ravel()


def _to_csr(A: Any) -> sparse.csr_matrix:
    """Convert to CSR sparse matrix (dense inputs are converted to sparse)."""
    return A.tocsr() if sparse.isspmatrix(A) else sparse.csr_matrix(A)


# ---------------------------
# public API
# ---------------------------

def load_lpnetlib_mat(path: str, *, eq_tol: float = 1e-12) -> Dict[str, Any]:
    """
    Load an LP problem stored in a SuiteSparse/LPnetlib `.mat` file
    and produce a canonical dict suitable for `solve_lp(...)`.

    - If `rl/ru` (row lower/upper) are present, they are mapped to:
        * equality rows where rl == ru (within `eq_tol`),
        * <= rows for finite ru,
        * >= rows for finite rl (mapped as -A x <= -rl).
    - Else, if `b` is present, we build Ax = b.
    - Variable bounds come from lo/hi (if absent, default to [0, +inf)).
    - If an objective offset (z0) exists, it's saved as `obj_offset`.

    Parameters
    ----------
    path : str
        Path to the `.mat` file.
    eq_tol : float
        Tolerance to detect `rl == ru` equalities.

    Returns
    -------
    Dict[str, Any]
        Canonical LP problem dict (see module docstring).
    """
    mat = loadmat(path, squeeze_me=True, struct_as_record=False)

    # Some files have a top-level struct named 'Problem'
    prob = None
    for key in ("Problem", "problem", "PROBLEM"):
        if key in mat:
            prob = mat[key]
            break

    container = prob if prob is not None else mat
    aux = _fetch_field(container, "aux", "Aux", "AUX")  # objective & bounds often live here

    # Extract pieces with fallbacks and aliasing
    A  = _fetch_primary_then_aux(container, aux, "A", "a", "M", "mat")
    c  = _fetch_primary_then_aux(container, aux, "c", "f", "cost", "obj", "objective")
    b  = _fetch_primary_then_aux(container, aux, "b", "rhs", "beq")

    rl = _fetch_primary_then_aux(container, aux, "rl", "r_l", "rowl", "bl", "lower_row", "row_lower")
    ru = _fetch_primary_then_aux(container, aux, "ru", "r_u", "rowu", "bu", "upper_row", "row_upper")

    lo = _fetch_primary_then_aux(container, aux, "lo", "l", "lb", "lower", "xl", "xlow")
    hi = _fetch_primary_then_aux(container, aux, "hi", "u", "ub", "upper", "xu", "xupp")

    z0 = _fetch_primary_then_aux(container, aux, "z0", "objconst", "offset")  # optional objective constant

    # Fallback: sometimes the only sparse object is A
    if A is None:
        for k, v in mat.items():
            if sparse.isspmatrix(v):
                A = v
                break

    if A is None or c is None:
        raise ValueError("Invalid .mat: missing A or c (unrecognized structure).")

    A = _to_csr(A)
    c = _ensure_1d_float(c)
    m, n = A.shape
    if c.size != n:
        raise ValueError(f"Inconsistent sizes: len(c)={c.size} != n={n} (columns of A).")

    # Variable bounds
    if lo is None:
        lo = np.zeros(n, dtype=float)
    else:
        lo = _ensure_1d_float(lo)

    if hi is None:
        hi = np.full(n, np.inf, dtype=float)
    else:
        hi = _ensure_1d_float(hi)

    if lo.size != n or hi.size != n:
        raise ValueError("Inconsistent variable bounds: len(lo/hi) != n.")

    bounds = [
        (None if not np.isfinite(L) else float(L),
         None if not np.isfinite(U) else float(U))
        for L, U in zip(lo, hi)
    ]

    # Build row constraints
    A_eq = None
    b_eq = None
    A_ub_blocks: List[sparse.csr_matrix] = []
    b_ub_blocks: List[np.ndarray] = []

    if rl is not None or ru is not None:
        rl_vec = _ensure_1d_float(rl) if rl is not None else np.full(m, -np.inf)
        ru_vec = _ensure_1d_float(ru) if ru is not None else np.full(m,  np.inf)
        if rl_vec.size != m or ru_vec.size != m:
            raise ValueError("Inconsistent row bounds: len(rl/ru) != m (rows of A).")

        # Equalities: finite rl == ru
        is_eq = np.isfinite(rl_vec) & np.isfinite(ru_vec) & (np.abs(rl_vec - ru_vec) <= eq_tol)
        eq_idx = np.where(is_eq)[0]
        if eq_idx.size > 0:
            A_eq = A[eq_idx, :]
            b_eq = ru_vec[eq_idx]

        # <= rows: finite ru (excluding equalities already handled)
        le_idx = np.where(np.isfinite(ru_vec) & ~is_eq)[0]
        if le_idx.size > 0:
            A_ub_blocks.append(A[le_idx, :])
            b_ub_blocks.append(ru_vec[le_idx])

        # >= rows: finite rl (excluding equalities) → -A x <= -rl
        ge_idx = np.where(np.isfinite(rl_vec) & ~is_eq)[0]
        if ge_idx.size > 0:
            A_ub_blocks.append((-A[ge_idx, :]).tocsr())
            b_ub_blocks.append(-rl_vec[ge_idx])

    elif b is not None:
        b = _ensure_1d_float(b)
        if b.size != m:
            raise ValueError(f"Inconsistent sizes: len(b)={b.size} != m={m} (rows of A).")
        A_eq = A
        b_eq = b
    # else: no row constraints → only variable bounds

    A_ub = None
    b_ub = None
    if A_ub_blocks:
        A_ub = sparse.vstack(A_ub_blocks, format="csr")
        b_ub = np.concatenate(b_ub_blocks, axis=0)

    var_names = [f"x{i}" for i in range(n)]

    problem: Dict[str, Any] = {
        "sense": "min",              # LPnetlib instances are typically minimization
        "c": c.tolist(),
        "bounds": bounds,
        "var_names": var_names,
        "metadata": {"source": "LPnetlib", "path": path},
    }
    if A_eq is not None:
        problem["A_eq"] = A_eq
        problem["b_eq"] = b_eq.tolist()
    if A_ub is not None:
        problem["A_ub"] = A_ub
        problem["b_ub"] = b_ub.tolist()
    if z0 is not None:
        try:
            problem["obj_offset"] = float(np.asarray(z0).ravel()[0])
        except Exception:
            # non-fatal: ignore if z0 has unexpected shape/type
            pass

    return problem
