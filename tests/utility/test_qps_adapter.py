from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from optees.utility.data_adapters.qps_adapter import load_qps_file, parse_qps_text
from optees.composition.local_agent import create_local_optimization_service
from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope


SAMPLE_QPS_LF = """NAME          SAMPLE_QP
ROWS
  N  OBJ
  E  EQ1
  L  LEQ1
  G  GEQ1
COLUMNS
    X1        OBJ               -2.0   EQ1                1.0
    X1        LEQ1               1.0
    X2        OBJ               -3.0   EQ1                1.0
    X2        GEQ1               1.0
RHS
    RHS1      OBJ               -5.0
    RHS1      EQ1                2.0
    RHS1      LEQ1               3.0
    RHS1      GEQ1               0.5
BOUNDS
 LO BND       X1                 0.0
 UP BND       X1                 5.0
 FR BND       X2
QUADOBJ
    X1        X1                 4.0
    X1        X2                 1.0
    X2        X2                 2.0
ENDATA
"""


def test_qps_adapter_basic_parsing() -> None:
    problem = parse_qps_text(SAMPLE_QPS_LF)
    assert problem["version"] == "1"
    assert problem["problem_type"] == "quadratic_programming"

    variables = problem["variables"]
    assert len(variables) == 2
    assert variables[0] == {"name": "X1", "lb": 0.0, "ub": 5.0}
    assert variables[1] == {"name": "X2", "lb": None, "ub": None}

    obj = problem["objective"]
    assert obj["sense"] == "min"
    assert obj["linear_coefficients"] == [-2.0, -3.0]
    # In MPS, RHS for obj is -5.0 -> offset = -(-5.0) = 5.0
    assert obj["offset"] == 5.0
    assert obj["quadratic_matrix"] == [[4.0, 1.0], [1.0, 2.0]]

    constraints = problem["constraints"]
    assert len(constraints) == 3
    eq1 = next(c for c in constraints if c["name"] == "EQ1")
    assert eq1["relation"] == "="
    assert eq1["rhs"] == 2.0
    assert eq1["coefficients"] == [1.0, 1.0]

    leq1 = next(c for c in constraints if c["name"] == "LEQ1")
    assert leq1["relation"] == "<="
    assert leq1["rhs"] == 3.0
    assert leq1["coefficients"] == [1.0, 0.0]

    geq1 = next(c for c in constraints if c["name"] == "GEQ1")
    assert geq1["relation"] == ">="
    assert geq1["rhs"] == 0.5
    assert geq1["coefficients"] == [0.0, 1.0]


def test_qps_adapter_crlf_handling() -> None:
    crlf_text = SAMPLE_QPS_LF.replace("\n", "\r\n")
    problem = parse_qps_text(crlf_text)
    assert len(problem["variables"]) == 2
    assert problem["objective"]["offset"] == 5.0


def test_qps_adapter_load_file() -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".qps", delete=False, encoding="utf-8") as tmp:
        tmp.write(SAMPLE_QPS_LF)
        tmp_path = Path(tmp.name)
    try:
        problem = load_qps_file(tmp_path, default_tolerance=1e-8, default_max_iterations=5000)
        assert problem["solver_options"]["tolerance"] == 1e-8
        assert problem["solver_options"]["max_iterations"] == 5000
    finally:
        tmp_path.unlink(missing_ok=True)


def test_qps_adapter_file_not_found() -> None:
    with pytest.raises(FileNotFoundError, match="QPS file not found"):
        load_qps_file("non_existent_file.qps")


def test_qps_adapter_bounds_variations() -> None:
    qps_bounds = """NAME          BOUNDS_TEST
ROWS
  N  OBJ
COLUMNS
    X_DEFAULT OBJ                1.0
    X_FX      OBJ                2.0
    X_MI      OBJ                3.0
    X_PL      OBJ                4.0
    X_LO_UP   OBJ                5.0
BOUNDS
 FX BND       X_FX               10.0
 MI BND       X_MI
 PL BND       X_PL
 LO BND       X_LO_UP            2.5
 UP BND       X_LO_UP            7.5
ENDATA
"""
    problem = parse_qps_text(qps_bounds)
    vmap = {v["name"]: (v["lb"], v["ub"]) for v in problem["variables"]}

    # X_DEFAULT: default MPS [0, None]
    assert vmap["X_DEFAULT"] == (0.0, None)
    # X_FX: fixed at 10.0
    assert vmap["X_FX"] == (10.0, 10.0)
    # X_MI: minus infinity to 0.0
    assert vmap["X_MI"] == (None, 0.0)
    # X_PL: 0.0 to +inf
    assert vmap["X_PL"] == (0.0, None)
    # X_LO_UP: 2.5 to 7.5
    assert vmap["X_LO_UP"] == (2.5, 7.5)


def test_qps_adapter_ranges() -> None:
    qps_ranges = """NAME          RANGE_TEST
ROWS
  N  OBJ
  E  ROW_E_POS
  E  ROW_E_NEG
  L  ROW_L
  G  ROW_G
COLUMNS
    X1        OBJ                1.0
    X1        ROW_E_POS          1.0
    X1        ROW_E_NEG          1.0
    X1        ROW_L              1.0
    X1        ROW_G              1.0
RHS
    RHS1      ROW_E_POS          10.0
    RHS1      ROW_E_NEG          10.0
    RHS1      ROW_L              20.0
    RHS1      ROW_G              30.0
RANGES
    RNG1      ROW_E_POS          2.0
    RNG1      ROW_E_NEG         -3.0
    RNG1      ROW_L              5.0
    RNG1      ROW_G              4.0
ENDATA
"""
    problem = parse_qps_text(qps_ranges)
    cmap = {c["name"]: (c["relation"], c["rhs"]) for c in problem["constraints"]}

    # ROW_E_POS (E with r=2): [10, 12]
    assert cmap["ROW_E_POS_lb"] == (">=", 10.0)
    assert cmap["ROW_E_POS_ub"] == ("<=", 12.0)

    # ROW_E_NEG (E with r=-3): [7, 10]
    assert cmap["ROW_E_NEG_lb"] == (">=", 7.0)
    assert cmap["ROW_E_NEG_ub"] == ("<=", 10.0)

    # ROW_L (L with r=5, b=20): [15, 20]
    assert cmap["ROW_L_lb"] == (">=", 15.0)
    assert cmap["ROW_L_ub"] == ("<=", 20.0)

    # ROW_G (G with r=4, b=30): [30, 34]
    assert cmap["ROW_G_lb"] == (">=", 30.0)
    assert cmap["ROW_G_ub"] == ("<=", 34.0)


def test_qps_adapter_fail_closed_discrete_variables() -> None:
    qps_mip = """NAME          MIP_TEST
ROWS
  N  OBJ
COLUMNS
    MARK0000  'MARKER'                 'INTORG'
    X1        OBJ                1.0
    MARK0001  'MARKER'                 'INTEND'
ENDATA
"""
    with pytest.raises(ValueError, match="Discrete variables are not supported"):
        parse_qps_text(qps_mip)


def test_qps_adapter_fail_closed_unknown_section() -> None:
    qps_bad_section = """NAME          BAD_SECTION
UNKNOWN_SECTION
    DATA      LINE
ENDATA
"""
    with pytest.raises(ValueError, match="Unsupported section 'UNKNOWN_SECTION'"):
        parse_qps_text(qps_bad_section)


def test_qps_adapter_fail_closed_unknown_row_sense() -> None:
    qps_bad_row = """NAME          BAD_ROW
ROWS
  X  BAD_ROW_NAME
ENDATA
"""
    with pytest.raises(ValueError, match="Unsupported row sense 'X'"):
        parse_qps_text(qps_bad_row)


def test_qps_adapter_fail_closed_undeclared_quadobj_var() -> None:
    qps_bad_quad = """NAME          BAD_QUAD
ROWS
  N  OBJ
COLUMNS
    X1        OBJ                1.0
QUADOBJ
    X1        UNDECLARED         2.0
ENDATA
"""
    with pytest.raises(ValueError, match="QUADOBJ references undeclared variable 'UNDECLARED'"):
        parse_qps_text(qps_bad_quad)


def test_qps_adapter_solves_through_optimization_service() -> None:
    # A simple 2D strictly convex unconstrained problem:
    # min 1/2 (2 x1^2 + 2 x2^2 + 2 x1 x2) - 4 x1 - 6 x2
    # optimum at x1 = 2/3, x2 = 8/3, obj = -28/3 = -9.3333333
    toy_qps = """NAME          TOY_QP
ROWS
  N  COST
COLUMNS
    X1        COST              -4.0
    X2        COST              -6.0
BOUNDS
 FR BND       X1
 FR BND       X2
QUADOBJ
    X1        X1                 2.0
    X1        X2                 1.0
    X2        X2                 2.0
ENDATA
"""
    problem = parse_qps_text(toy_qps)
    service = create_local_optimization_service()
    envelope = service.solve(QP_CAPABILITY_ID, problem)

    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.mathematical_status.value == "optimal"
    assert envelope.result is not None
    assert envelope.result["objective"] == pytest.approx(-28.0 / 3.0, rel=1e-5, abs=1e-5)
    assert envelope.validation is not None
    assert envelope.validation.status.value in {"verified", "partial"}
