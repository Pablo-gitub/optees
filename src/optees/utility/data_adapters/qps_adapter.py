"""
Adapter for Quadratic Programming Standard (QPS) benchmark files.

Translates continuous convex QP instances in QPS/MPS format (e.g. from the
Maros–Mészáros collection) into Optees ContinuousConvexQPProblem v1 dictionaries.

Mathematical formulation convention:
    min 1/2 x^T Q x + c^T x + alpha
    s.t. A_eq x = b_eq
         A_ineq x <= b_ineq
         l <= x <= u

This adapter resides at the utility data-adapters boundary and is not a public
product API or CLI command.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SUPPORTED_SECTIONS = {
    "NAME",
    "ROWS",
    "COLUMNS",
    "RHS",
    "RANGES",
    "BOUNDS",
    "QUADOBJ",
    "QSECTION",
    "ENDATA",
}

SUPPORTED_ROW_SENSES = {"N", "E", "L", "G"}
SUPPORTED_BOUND_TYPES = {"UP", "LO", "FX", "FR", "MI", "PL"}


def parse_qps_text(
    text: str,
    *,
    default_tolerance: Optional[float] = None,
    default_max_iterations: Optional[int] = None,
    default_time_limit: Optional[float] = None,
) -> Dict[str, Any]:
    """Parse a QPS-formatted string into an Optees QP problem dictionary (schema v1).

    Parameters
    ----------
    text : str
        QPS / MPS content with LF or CRLF line terminators.
    default_tolerance : float, optional
        Optional solver tolerance to inject into solver_options.
    default_max_iterations : int, optional
        Optional maximum iterations to inject into solver_options.
    default_time_limit : float, optional
        Optional time limit in seconds to inject into solver_options.

    Returns
    -------
    dict
        Dictionary conforming to Optees ContinuousConvexQPProblem schema version 1.
    """
    lines = text.splitlines()

    current_section: Optional[str] = None

    row_senses: Dict[str, str] = {}
    obj_row_name: Optional[str] = None

    # Column ordering preserves declared sequence
    col_order: List[str] = []
    col_entries: Dict[str, Dict[str, float]] = {}

    rhs_values: Dict[str, float] = {}
    range_values: Dict[str, float] = {}
    var_bounds: Dict[str, List[Optional[float]]] = {}
    quad_entries: List[Tuple[str, str, float]] = []

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue

        # Header lines start at column 0 (no leading whitespace)
        is_header = not raw_line[0].isspace()
        if is_header:
            tokens = line.split()
            header_keyword = tokens[0].upper()
            if header_keyword not in SUPPORTED_SECTIONS:
                raise ValueError(
                    f"Unsupported section '{header_keyword}' at line {line_idx}. "
                    f"Supported sections: {sorted(SUPPORTED_SECTIONS)}"
                )
            current_section = header_keyword
            if current_section == "ENDATA":
                break
            continue

        if current_section is None:
            raise ValueError(f"Data line before any section header at line {line_idx}: {line}")

        tokens = line.split()
        if not tokens:
            continue

        if current_section == "ROWS":
            stype = tokens[0].upper()
            if stype not in SUPPORTED_ROW_SENSES:
                raise ValueError(
                    f"Unsupported row sense '{stype}' for row at line {line_idx}. "
                    f"Expected one of {sorted(SUPPORTED_ROW_SENSES)}"
                )
            if len(tokens) < 2:
                raise ValueError(f"Missing row name in ROWS section at line {line_idx}")
            rname = tokens[1]
            if stype == "N":
                if obj_row_name is None:
                    obj_row_name = rname
            else:
                row_senses[rname] = stype

        elif current_section == "COLUMNS":
            # Check for integer marker cards
            upper_tokens = [t.strip("'\"").upper() for t in tokens]
            if "MARKER" in upper_tokens or "INTORG" in upper_tokens or "INTEND" in upper_tokens:
                raise ValueError(
                    f"Discrete/integer marker found at line {line_idx}. "
                    f"Discrete variables are not supported by the continuous QP adapter."
                )
            cname = tokens[0]
            if cname not in col_entries:
                col_order.append(cname)
                col_entries[cname] = {}

            # Parse (row_name, value) pairs
            idx = 1
            while idx < len(tokens):
                rname = tokens[idx]
                if idx + 1 >= len(tokens):
                    raise ValueError(
                        f"Missing numeric value for row '{rname}' of column '{cname}' at line {line_idx}"
                    )
                val_str = tokens[idx + 1]
                val = _parse_float(val_str, line_idx)
                col_entries[cname][rname] = val
                idx += 2

        elif current_section == "RHS":
            # tokens[0] is rhs vector name; following tokens are (row_name, value) pairs
            idx = 1
            while idx < len(tokens):
                rname = tokens[idx]
                if idx + 1 >= len(tokens):
                    raise ValueError(
                        f"Missing numeric value for row '{rname}' in RHS at line {line_idx}"
                    )
                val = _parse_float(tokens[idx + 1], line_idx)
                rhs_values[rname] = val
                idx += 2

        elif current_section == "RANGES":
            # tokens[0] is range vector name; following tokens are (row_name, value) pairs
            idx = 1
            while idx < len(tokens):
                rname = tokens[idx]
                if idx + 1 >= len(tokens):
                    raise ValueError(
                        f"Missing numeric value for row '{rname}' in RANGES at line {line_idx}"
                    )
                val = _parse_float(tokens[idx + 1], line_idx)
                range_values[rname] = val
                idx += 2

        elif current_section == "BOUNDS":
            btype = tokens[0].upper()
            if btype not in SUPPORTED_BOUND_TYPES:
                raise ValueError(
                    f"Unsupported bound type '{btype}' at line {line_idx}. "
                    f"Supported types: {sorted(SUPPORTED_BOUND_TYPES)}"
                )
            if len(tokens) < 3:
                raise ValueError(f"Malformed BOUNDS record at line {line_idx}: {line}")
            # tokens[1] is bounds vector name; tokens[2] is column name
            cname = tokens[2]
            if cname not in var_bounds:
                # Default MPS bound: [0.0, None] -> 0 <= x < +inf
                var_bounds[cname] = [0.0, None]

            if btype in ("UP", "LO", "FX"):
                if len(tokens) < 4:
                    raise ValueError(f"Missing bound value for '{btype}' at line {line_idx}")
                bval = _parse_float(tokens[3], line_idx)
                if btype == "UP":
                    var_bounds[cname][1] = bval
                elif btype == "LO":
                    var_bounds[cname][0] = bval
                elif btype == "FX":
                    var_bounds[cname][0] = bval
                    var_bounds[cname][1] = bval
            elif btype == "FR":
                var_bounds[cname][0] = None
                var_bounds[cname][1] = None
            elif btype == "MI":
                var_bounds[cname][0] = None
                if var_bounds[cname][1] is None:
                    var_bounds[cname][1] = 0.0
            elif btype == "PL":
                var_bounds[cname][1] = None

        elif current_section in ("QUADOBJ", "QSECTION"):
            if len(tokens) < 3:
                raise ValueError(f"Malformed QUADOBJ record at line {line_idx}: {line}")
            c1, c2 = tokens[0], tokens[1]
            qval = _parse_float(tokens[2], line_idx)
            quad_entries.append((c1, c2, qval))

    # Validate variables and index mapping
    n = len(col_order)
    if n == 0:
        raise ValueError("QPS problem has no variables defined in COLUMNS section")
    col_idx = {name: i for i, name in enumerate(col_order)}

    # Build variables array
    variables_payload = []
    for cname in col_order:
        lb, ub = var_bounds.get(cname, [0.0, None])
        variables_payload.append({"name": cname, "lb": lb, "ub": ub})

    # Build linear objective vector c
    c_vec = [0.0] * n
    for cname, entries in col_entries.items():
        if obj_row_name and obj_row_name in entries:
            c_vec[col_idx[cname]] = entries[obj_row_name]

    # Objective offset c_0 from RHS of obj_row: in MPS, obj_row + c^T x = RHS -> min c^T x - RHS
    # so offset = -RHS[obj_row]
    offset = 0.0
    if obj_row_name and obj_row_name in rhs_values:
        offset = -rhs_values[obj_row_name]

    # Build quadratic matrix Q (symmetric n x n)
    q_matrix = [[0.0] * n for _ in range(n)]
    for c1, c2, qval in quad_entries:
        if c1 not in col_idx:
            raise ValueError(f"QUADOBJ references undeclared variable '{c1}'")
        if c2 not in col_idx:
            raise ValueError(f"QUADOBJ references undeclared variable '{c2}'")
        i, j = col_idx[c1], col_idx[c2]
        q_matrix[i][j] = qval
        q_matrix[j][i] = qval

    # Build linear constraints
    constraints_payload = []
    for rname, stype in row_senses.items():
        b = rhs_values.get(rname, 0.0)
        coeffs = [0.0] * n
        has_nonzero = False
        for cname, entries in col_entries.items():
            if rname in entries:
                coeffs[col_idx[cname]] = entries[rname]
                has_nonzero = True

        if not has_nonzero:
            # Row has no column coefficients; can be skipped if satisfied
            continue

        r_val = range_values.get(rname)
        if r_val is not None:
            # Range constraint: expand to paired inequalities
            if stype == "E":
                if r_val > 0:
                    constraints_payload.append(
                        {"name": f"{rname}_lb", "coefficients": coeffs, "relation": ">=", "rhs": b}
                    )
                    constraints_payload.append(
                        {
                            "name": f"{rname}_ub",
                            "coefficients": coeffs,
                            "relation": "<=",
                            "rhs": b + r_val,
                        }
                    )
                else:
                    constraints_payload.append(
                        {
                            "name": f"{rname}_lb",
                            "coefficients": coeffs,
                            "relation": ">=",
                            "rhs": b + r_val,
                        }
                    )
                    constraints_payload.append(
                        {"name": f"{rname}_ub", "coefficients": coeffs, "relation": "<=", "rhs": b}
                    )
            elif stype == "L":
                constraints_payload.append(
                    {"name": f"{rname}_ub", "coefficients": coeffs, "relation": "<=", "rhs": b}
                )
                constraints_payload.append(
                    {
                        "name": f"{rname}_lb",
                        "coefficients": coeffs,
                        "relation": ">=",
                        "rhs": b - abs(r_val),
                    }
                )
            elif stype == "G":
                constraints_payload.append(
                    {"name": f"{rname}_lb", "coefficients": coeffs, "relation": ">=", "rhs": b}
                )
                constraints_payload.append(
                    {
                        "name": f"{rname}_ub",
                        "coefficients": coeffs,
                        "relation": "<=",
                        "rhs": b + abs(r_val),
                    }
                )
        else:
            rel = "=" if stype == "E" else ("<=" if stype == "L" else ">=")
            constraints_payload.append(
                {"name": rname, "coefficients": coeffs, "relation": rel, "rhs": b}
            )

    problem: Dict[str, Any] = {
        "version": "1",
        "problem_type": "quadratic_programming",
        "variables": variables_payload,
        "objective": {
            "sense": "min",
            "quadratic_matrix": q_matrix,
            "linear_coefficients": c_vec,
            "offset": offset,
        },
        "constraints": constraints_payload,
    }

    # Optional solver options
    solver_options: Dict[str, Any] = {"method": "osqp"}
    if default_tolerance is not None:
        solver_options["tolerance"] = float(default_tolerance)
    if default_max_iterations is not None:
        solver_options["max_iterations"] = int(default_max_iterations)
    if default_time_limit is not None:
        solver_options["time_limit_seconds"] = float(default_time_limit)

    if len(solver_options) > 1:
        problem["solver_options"] = solver_options

    return problem


def load_qps_file(
    path: str | Path,
    *,
    default_tolerance: Optional[float] = None,
    default_max_iterations: Optional[int] = None,
    default_time_limit: Optional[float] = None,
    encoding: str = "latin1",
) -> Dict[str, Any]:
    """Load and parse a QPS file from disk.

    Parameters
    ----------
    path : str or Path
        Path to the .qps file.
    default_tolerance : float, optional
        Optional solver tolerance to inject into solver_options.
    default_max_iterations : int, optional
        Optional maximum iterations to inject into solver_options.
    default_time_limit : float, optional
        Optional time limit in seconds to inject into solver_options.
    encoding : str
        File encoding (default 'latin1' to tolerate legacy ASCII/extended ASCII).

    Returns
    -------
    dict
        Dictionary conforming to Optees ContinuousConvexQPProblem schema version 1.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"QPS file not found: {file_path}")

    text = file_path.read_text(encoding=encoding)
    return parse_qps_text(
        text,
        default_tolerance=default_tolerance,
        default_max_iterations=default_max_iterations,
        default_time_limit=default_time_limit,
    )


def _parse_float(val_str: str, line_idx: int) -> float:
    """Parse a float string, supporting Fortran/D exponent notation and rejecting non-finite."""
    normalized = val_str.replace("D", "e").replace("d", "e").replace("E", "e")
    try:
        val = float(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid floating-point literal '{val_str}' at line {line_idx}") from exc
    if not math.isfinite(val):
        raise ValueError(f"Non-finite floating-point value '{val_str}' at line {line_idx}")
    return val
