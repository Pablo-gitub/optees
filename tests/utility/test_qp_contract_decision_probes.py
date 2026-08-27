from __future__ import annotations

import json
import math
from pathlib import Path
import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPOSITORY_ROOT / "docs" / "contracts" / "quadratic-programming-contract.md"


def _schema_subset_errors(value: object, schema: dict, path: str = "$") -> list[str]:
    """Validate the JSON Schema vocabulary used by the contract examples."""
    errors: list[str] = []
    expected = schema.get("type")
    expected_types = [expected] if isinstance(expected, str) else expected or []
    matches_type = not expected_types or any(
        (
            (kind == "null" and value is None)
            or (kind == "object" and isinstance(value, dict))
            or (kind == "array" and isinstance(value, list))
            or (kind == "string" and isinstance(value, str))
            or (kind == "integer" and isinstance(value, int) and not isinstance(value, bool))
            or (
                kind == "number"
                and isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
            )
        )
        for kind in expected_types
    )
    if not matches_type:
        return [f"{path}: wrong type"]
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path}: wrong constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: outside enum")
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: shorter than minLength")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: shorter than minItems")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: longer than maxItems")
        for index, item in enumerate(value):
            errors.extend(_schema_subset_errors(item, schema.get("items", {}), f"{path}[{index}]"))
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{path}: missing {required}")
        for key, item in value.items():
            if key in properties:
                errors.extend(_schema_subset_errors(item, properties[key], f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}: unexpected {key}")
    return errors


def test_qp_contract_interior_optimum_analytical_recomputation() -> None:
    """Verify analytical solution for the interior unconstrained QP reference problem."""
    # Problem: min 0.5 * (2*x1^2 + 2*x2^2 + 2*x1*x2) - 4*x1 - 6*x2
    # Q = [[2, 1], [1, 2]], c = [-4, -6], offset = 0.0
    Q = np.array([[2.0, 1.0], [1.0, 2.0]], dtype=float)
    c = np.array([-4.0, -6.0], dtype=float)
    offset = 0.0

    # Gradient: Q x + c = 0 => x* = -Q^{-1} c
    x_star = np.linalg.solve(Q, -c)
    expected_x = np.array([2.0 / 3.0, 8.0 / 3.0], dtype=float)
    assert np.allclose(x_star, expected_x, atol=1e-12)

    # Objective: 0.5 * x^T Q x + c^T x + offset
    f_star = float(0.5 * x_star.T @ Q @ x_star + c.T @ x_star + offset)
    expected_f = -28.0 / 3.0
    assert math.isclose(f_star, expected_f, abs_tol=1e-12)


def test_qp_contract_boundary_optimum_analytical_recomputation() -> None:
    """Verify analytical solution for the boundary constrained QP reference problem."""
    # Problem: min 0.5 * (x1^2 + x2^2) s.t. x1 + x2 >= 2, x1 >= 0, x2 >= 0
    Q = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float)
    c = np.array([0.0, 0.0], dtype=float)
    offset = 0.0

    # Unconstrained min is (0, 0) which violates x1 + x2 >= 2.
    # On the boundary x1 + x2 = 2, by symmetry x1* = 1.0, x2* = 1.0.
    x_star = np.array([1.0, 1.0], dtype=float)
    f_star = float(0.5 * x_star.T @ Q @ x_star + c.T @ x_star + offset)
    assert math.isclose(f_star, 1.0, abs_tol=1e-12)

    # KKT stationarity: Q x* + c - y (1, 1)^T = (1, 1)^T - y (1, 1)^T = 0 => y* = 1.0 >= 0
    y_star = 1.0
    grad = Q @ x_star + c
    assert np.allclose(grad - y_star * np.array([1.0, 1.0]), [0.0, 0.0], atol=1e-12)


def test_qp_contract_concave_maximization_transformation() -> None:
    """Verify analytical solution and internal transformation for concave maximization."""
    # Problem: max -0.5 * (2*x1^2 + 2*x2^2) + 4*x1 + 6*x2 s.t. x >= 0
    # Q_user = [[-2, 0], [0, -2]] <= 0 (negative definite), c_user = [4, 6]
    Q_user = np.array([[-2.0, 0.0], [0.0, -2.0]], dtype=float)
    c_user = np.array([4.0, 6.0], dtype=float)
    offset_user = 0.0

    # Check that Q_user is negative semi-definite (i.e. -Q_user >= 0)
    eigenvalues = np.linalg.eigvalsh(Q_user)
    assert np.all(eigenvalues <= 1e-8), "Q_user must be negative semi-definite for concave max"

    # Internal transformed minimization: Q_int = -Q_user, c_int = -c_user, offset_int = -offset_user
    Q_int = -Q_user
    c_int = -c_user
    x_star = np.linalg.solve(Q_int, -c_int)
    expected_x = np.array([2.0, 3.0], dtype=float)
    assert np.allclose(x_star, expected_x, atol=1e-12)

    # Transformed min objective:
    f_min = float(0.5 * x_star.T @ Q_int @ x_star + c_int.T @ x_star)
    # Restored max objective: f_max = -f_min
    f_max = -f_min
    expected_max = float(0.5 * x_star.T @ Q_user @ x_star + c_user.T @ x_star + offset_user)
    assert math.isclose(f_max, 13.0, abs_tol=1e-12)
    assert math.isclose(expected_max, 13.0, abs_tol=1e-12)


def test_qp_contract_symmetry_check_and_symmetrization() -> None:
    """Verify matrix symmetry tolerance and symmetrization rules."""
    eps_sym = 1e-8

    # Case 1: Significantly asymmetric matrix
    Q_asym = np.array([[2.0, 3.0], [1.0, 2.0]], dtype=float)
    asym_norm = float(np.max(np.abs(Q_asym - Q_asym.T)))
    threshold_1 = eps_sym * max(1.0, float(np.max(np.abs(Q_asym))))
    assert asym_norm > threshold_1, "Must reject significantly asymmetric matrix"

    # Case 2: Slightly perturbed symmetric matrix (numerical rounding)
    Q_perturbed = np.array([[2.0, 1.0 + 1e-10], [1.0 - 1e-10, 2.0]], dtype=float)
    pert_norm = float(np.max(np.abs(Q_perturbed - Q_perturbed.T)))
    threshold_2 = eps_sym * max(1.0, float(np.max(np.abs(Q_perturbed))))
    assert pert_norm <= threshold_2, "Must accept matrix within symmetry tolerance"

    # Symmetrize
    Q_sym = 0.5 * (Q_perturbed + Q_perturbed.T)
    assert np.allclose(Q_sym, Q_sym.T, atol=0.0)


def test_qp_contract_psd_convexity_check() -> None:
    """Verify positive semi-definiteness (PSD) eigenvalue convexity checks."""
    eps_psd = 1e-8

    # Case 1: Strictly convex PSD matrix
    Q_psd = np.array([[2.0, 1.0], [1.0, 2.0]], dtype=float)
    min_eig_1 = float(np.min(np.linalg.eigvalsh(Q_psd)))
    assert min_eig_1 >= -eps_psd, "Must accept positive definite matrix"
    assert min_eig_1 > 0.0

    # Case 2: Indefinite / Non-convex matrix
    Q_indef = np.array([[1.0, 2.0], [2.0, 1.0]], dtype=float)
    min_eig_2 = float(np.min(np.linalg.eigvalsh(Q_indef)))
    assert min_eig_2 < -eps_psd, "Must reject indefinite matrix (min eigenvalue -1.0)"

    # Case 3: Numerical rounding of rank-deficient PSD matrix (e.g. eigenvalue -1e-12)
    Q_near_zero = np.array([[1.0, 1.0], [1.0, 1.0 - 1e-12]], dtype=float)
    Q_sym = 0.5 * (Q_near_zero + Q_near_zero.T)
    min_eig_3 = float(np.min(np.linalg.eigvalsh(Q_sym)))
    threshold_3 = -eps_psd * max(1.0, float(np.max(np.abs(Q_sym))))
    assert min_eig_3 >= threshold_3, "Small negative eigenvalue within tolerance is acceptable"


def test_qp_contract_infeasible_problem_structure() -> None:
    """Verify infeasibility detection logic on contradictory constraints."""
    # Constraints: x1 + x2 <= 1 and x1 + x2 >= 3, with x1 >= 0, x2 >= 0
    # For any x >= 0, 3 <= x1 + x2 <= 1 is empty (infeasible).
    A = np.array([[1.0, 1.0], [-1.0, -1.0]], dtype=float)
    b = np.array([1.0, -3.0], dtype=float)  # x1 + x2 <= 1 and -x1 - x2 <= -3

    # Farkas certificate of primal infeasibility for linear inequalities A x <= b, x >= 0:
    # Exists y >= 0 such that A^T y >= 0 and b^T y < 0.
    # Take y = [1, 1]^T >= 0:
    y = np.array([1.0, 1.0], dtype=float)
    AT_y = A.T @ y  # [1 - 1, 1 - 1] = [0, 0] >= 0
    b_y = float(b.T @ y)  # 1.0 - 3.0 = -2.0 < 0
    assert np.all(AT_y >= -1e-12)
    assert b_y < 0.0, "Proves mathematical infeasibility via Farkas certificate"


def test_qp_contract_unbounded_problem_structure() -> None:
    """Verify unboundedness certificate structure on unbounded QP problem."""
    # Problem: min 0.5 * x1^2 - 2*x2 s.t. x1 >= 0, x2 >= 0
    # Q = [[1, 0], [0, 0]], c = [0, -2]
    Q = np.array([[1.0, 0.0], [0.0, 0.0]], dtype=float)
    c = np.array([0.0, -2.0], dtype=float)

    # Certificate of dual infeasibility (primal unboundedness ray):
    # Exists d >= 0 such that Q d = 0 and c^T d < 0.
    d = np.array([0.0, 1.0], dtype=float)  # direction along +x2
    assert np.allclose(Q @ d, [0.0, 0.0], atol=1e-12)
    assert float(c.T @ d) < 0.0, "Proves unboundedness below along recession direction d"


def test_qp_independent_validation_arithmetic() -> None:
    """Verify the arithmetic checks of the proposed independent solution validator."""
    # Given model:
    variables = ["x1", "x2"]
    lb = [0.0, 0.0]
    ub = [None, None]
    Q = np.array([[1.0, 0.0], [0.0, 1.0]], dtype=float)
    c = np.array([0.0, 0.0], dtype=float)
    offset = 0.0
    constraint_A = np.array([[1.0, 1.0]], dtype=float)
    constraint_rhs = [2.0]

    # Reported candidate:
    candidate_x = {"x1": 1.0, "x2": 1.0}
    reported_obj = 1.0
    reported_y = [1.0]

    # Check 1: Variable vector
    assert set(candidate_x.keys()) == set(variables)
    x_vec = np.array([candidate_x[v] for v in variables], dtype=float)
    assert np.all(np.isfinite(x_vec))

    # Check 2: Bounds
    tol = 1e-7
    for i, v in enumerate(variables):
        if lb[i] is not None:
            assert x_vec[i] >= lb[i] - tol
        if ub[i] is not None:
            assert x_vec[i] <= ub[i] + tol

    # Check 3: Constraints
    lhs = constraint_A @ x_vec
    assert float(lhs[0]) >= constraint_rhs[0] - tol

    # Check 4: Objective recomputation
    recomputed_obj = float(0.5 * x_vec.T @ Q @ x_vec + c.T @ x_vec + offset)
    assert math.isclose(recomputed_obj, reported_obj, abs_tol=tol, rel_tol=tol)

    # Check 5: KKT Stationarity
    grad = Q @ x_vec + c  # [1, 1]
    # For >= constraint: grad - y * A^T = 0
    kkt_stat = grad - reported_y[0] * constraint_A[0]
    assert np.allclose(kkt_stat, [0.0, 0.0], atol=1e-6)


def test_qp_contract_document_json_examples() -> None:
    """Verify that all JSON code blocks in the QP contract document are valid JSON and check invariants."""
    assert CONTRACT_PATH.exists(), f"Contract file missing: {CONTRACT_PATH}"
    text = CONTRACT_PATH.read_text(encoding="utf-8")

    parts = text.split("```json")
    assert len(parts) >= 11, f"Expected at least 10 JSON blocks, found {len(parts)-1}"

    json_blocks: list[dict] = []
    for part in parts[1:]:
        code = part.split("```")[0].strip()
        data = json.loads(code)
        assert isinstance(data, dict)
        json_blocks.append(data)

    # First two blocks are input and result JSON schemas
    input_schema = json_blocks[0]
    result_schema = json_blocks[1]
    assert input_schema.get("title") == "ContinuousConvexQPProblem"
    assert result_schema.get("title") == "ContinuousConvexQPResult"

    # Every problem example is a structurally valid v1 document. The examples
    # labelled invalid violate cross-field mathematical rules that JSON Schema
    # cannot express (dimensions, symmetry, or convexity).
    for index in range(2, 10):
        assert _schema_subset_errors(json_blocks[index], input_schema) == []

    # Blocks 2..4: Valid Examples (Interior, Boundary, Concave Max)
    for index in (2, 3, 4):
        ex = json_blocks[index]
        assert ex["version"] == "1"
        assert "variables" in ex
        assert "objective" in ex
        n = len(ex["variables"])
        assert len(ex["objective"]["linear_coefficients"]) == n
        Q = np.array(ex["objective"]["quadratic_matrix"], dtype=float)
        assert Q.shape == (n, n)
        # Symmetry check
        assert np.allclose(Q, Q.T, atol=1e-8)
        # PSD or NSD check depending on sense
        eigvals = np.linalg.eigvalsh(Q)
        if ex["objective"]["sense"] == "min":
            assert np.min(eigvals) >= -1e-8
        else:
            assert np.max(eigvals) <= 1e-8

    # Block 5: Invalid Example 1 (Dimension mismatch)
    inv1 = json_blocks[5]
    n_vars = len(inv1["variables"])
    n_linear = len(inv1["objective"]["linear_coefficients"])
    Q_inv1 = np.array(inv1["objective"]["quadratic_matrix"], dtype=float)
    assert n_vars != n_linear or Q_inv1.shape != (n_vars, n_vars), "Must exhibit dimension mismatch"

    # Block 6: Invalid Example 2 (Asymmetric matrix)
    inv2 = json_blocks[6]
    Q_inv2 = np.array(inv2["objective"]["quadratic_matrix"], dtype=float)
    asym = np.max(np.abs(Q_inv2 - Q_inv2.T))
    assert asym > 1e-8, "Must exhibit asymmetry exceeding tolerance"

    # Block 7: Invalid Example 3 (Non-PSD matrix)
    inv3 = json_blocks[7]
    Q_inv3 = np.array(inv3["objective"]["quadratic_matrix"], dtype=float)
    min_eig = np.min(np.linalg.eigvalsh(Q_inv3))
    assert min_eig < -1e-8, "Must exhibit negative eigenvalue"
