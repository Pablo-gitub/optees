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
from typing import Any


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
DEFAULT_MAX_TEXT_BYTES = 25_000_000
DEFAULT_MAX_VARIABLES = 2_000
DEFAULT_MAX_ROWS = 5_000
DEFAULT_MAX_DENSE_ENTRIES = 4_000_000


def parse_qps_text(
    text: str,
    *,
    default_tolerance: float | None = None,
    default_max_iterations: int | None = None,
    default_time_limit: float | None = None,
    max_variables: int = DEFAULT_MAX_VARIABLES,
    max_rows: int = DEFAULT_MAX_ROWS,
    max_dense_entries: int = DEFAULT_MAX_DENSE_ENTRIES,
) -> dict[str, Any]:
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
    if not isinstance(text, str):
        raise TypeError("QPS input must be text")
    if len(text.encode("utf-8")) > DEFAULT_MAX_TEXT_BYTES:
        raise ValueError("QPS input exceeds the configured text-size limit")
    for name, value in (
        ("max_variables", max_variables),
        ("max_rows", max_rows),
        ("max_dense_entries", max_dense_entries),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")

    lines = text.splitlines()

    current_section: str | None = None
    seen_sections: set[str] = set()
    endata_seen = False

    row_senses: dict[str, str] = {}
    obj_row_name: str | None = None

    # Column ordering preserves declared sequence
    col_order: list[str] = []
    col_entries: dict[str, dict[str, float]] = {}

    rhs_values: dict[str, float] = {}
    range_values: dict[str, float] = {}
    var_bounds: dict[str, list[float | None]] = {}
    quad_entries: dict[tuple[str, str], float] = {}
    quad_orientations: dict[frozenset[str], tuple[str, str]] = {}
    rhs_vector_name: str | None = None
    range_vector_name: str | None = None
    bounds_vector_name: str | None = None

    for line_idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line or line.startswith("*"):
            continue
        if endata_seen:
            raise ValueError(f"Unexpected content after ENDATA at line {line_idx}")

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
            if header_keyword in seen_sections:
                raise ValueError(f"Duplicate section '{header_keyword}' at line {line_idx}")
            seen_sections.add(header_keyword)
            current_section = header_keyword
            if current_section == "ENDATA":
                endata_seen = True
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
            if rname in row_senses or rname == obj_row_name:
                raise ValueError(f"Duplicate row name '{rname}' at line {line_idx}")
            if stype == "N":
                if obj_row_name is not None:
                    raise ValueError("QPS adapter requires exactly one N objective row")
                obj_row_name = rname
            else:
                row_senses[rname] = stype
                if len(row_senses) > max_rows:
                    raise ValueError("QPS problem exceeds the configured row limit")

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
                col_entries[cname][rname] = col_entries[cname].get(rname, 0.0) + val
                idx += 2
            if len(col_order) > max_variables:
                raise ValueError("QPS problem exceeds the configured variable limit")

        elif current_section == "RHS":
            # tokens[0] is rhs vector name; following tokens are (row_name, value) pairs
            if rhs_vector_name is None:
                rhs_vector_name = tokens[0]
            elif tokens[0] != rhs_vector_name:
                raise ValueError("Multiple RHS vectors are not supported")
            idx = 1
            while idx < len(tokens):
                rname = tokens[idx]
                if idx + 1 >= len(tokens):
                    raise ValueError(
                        f"Missing numeric value for row '{rname}' in RHS at line {line_idx}"
                    )
                val = _parse_float(tokens[idx + 1], line_idx)
                rhs_values[rname] = rhs_values.get(rname, 0.0) + val
                idx += 2

        elif current_section == "RANGES":
            # tokens[0] is range vector name; following tokens are (row_name, value) pairs
            if range_vector_name is None:
                range_vector_name = tokens[0]
            elif tokens[0] != range_vector_name:
                raise ValueError("Multiple RANGES vectors are not supported")
            idx = 1
            while idx < len(tokens):
                rname = tokens[idx]
                if idx + 1 >= len(tokens):
                    raise ValueError(
                        f"Missing numeric value for row '{rname}' in RANGES at line {line_idx}"
                    )
                val = _parse_float(tokens[idx + 1], line_idx)
                if rname in range_values:
                    raise ValueError(f"Duplicate range for row '{rname}'")
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
            if bounds_vector_name is None:
                bounds_vector_name = tokens[1]
            elif tokens[1] != bounds_vector_name:
                raise ValueError("Multiple BOUNDS vectors are not supported")
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
            pair = (c1, c2)
            unordered_pair = frozenset(pair)
            prior_orientation = quad_orientations.get(unordered_pair)
            if c1 != c2 and prior_orientation is not None and prior_orientation != pair:
                raise ValueError(f"Quadratic pair '{c1}', '{c2}' is declared in both orientations")
            quad_orientations[unordered_pair] = pair
            quad_entries[pair] = quad_entries.get(pair, 0.0) + qval

    if not endata_seen:
        raise ValueError("QPS input is missing ENDATA")
    if obj_row_name is None:
        raise ValueError("QPS input must declare exactly one N objective row")

    # Validate variables and index mapping
    n = len(col_order)
    if n == 0:
        raise ValueError("QPS problem has no variables defined in COLUMNS section")
    if n * n > max_dense_entries:
        raise ValueError("QPS problem exceeds the configured dense-matrix limit")
    col_idx = {name: i for i, name in enumerate(col_order)}

    declared_rows = set(row_senses) | {obj_row_name}
    referenced_rows = (
        {row_name for entries in col_entries.values() for row_name in entries}
        | set(rhs_values)
        | set(range_values)
    )
    unknown_rows = sorted(referenced_rows - declared_rows)
    if unknown_rows:
        raise ValueError(f"QPS records reference undeclared rows: {unknown_rows}")
    unknown_bound_variables = sorted(set(var_bounds) - set(col_order))
    if unknown_bound_variables:
        raise ValueError(
            f"BOUNDS records reference undeclared variables: {unknown_bound_variables}"
        )
    invalid_range_rows = sorted(set(range_values) - set(row_senses))
    if invalid_range_rows:
        raise ValueError(f"RANGES records reference non-constraint rows: {invalid_range_rows}")

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
    for (c1, c2), qval in quad_entries.items():
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
        for cname, entries in col_entries.items():
            if rname in entries:
                coeffs[col_idx[cname]] = entries[rname]

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

    problem: dict[str, Any] = {
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
    solver_options: dict[str, Any] = {"method": "osqp"}
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
    default_tolerance: float | None = None,
    default_max_iterations: int | None = None,
    default_time_limit: float | None = None,
    encoding: str = "latin1",
) -> dict[str, Any]:
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
