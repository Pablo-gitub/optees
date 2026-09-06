from __future__ import annotations

import hashlib
from pathlib import Path
from typing import NamedTuple
import pytest

from optees.application.contracts.capability_ids import QP_CAPABILITY_ID
from optees.application.contracts.execution import ExecutionEnvelope
from optees.application.contracts.solution_validation import ValidationCheckStatus
from optees.composition.local_agent import create_local_optimization_service
from optees.utility.data_adapters.qps_adapter import load_qps_file
from scripts.fetch_maros_meszaros_benchmark import (
    DEFAULT_CACHE_DIR,
    SELECTED_INSTANCE_MANIFEST,
)


class BenchmarkCase(NamedTuple):
    name: str
    filename: str
    expected_opt: float
    m_rows: int
    n_vars: int


BENCHMARK_CASES: list[BenchmarkCase] = [
    BenchmarkCase("HS21", "HS21.QPS", -99.9600000, 1, 2),
    BenchmarkCase("QPTEST", "QPTEST.QPS", 4.3718750, 2, 2),
    BenchmarkCase("TAME", "TAME.QPS", 0.0000000, 1, 2),
    BenchmarkCase("ZECEVIC2", "ZECEVIC2.QPS", -4.1250000, 2, 2),
    BenchmarkCase("HS35", "HS35.QPS", 0.11111111, 1, 3),
    BenchmarkCase("HS76", "HS76.QPS", -4.6818182, 3, 4),
    BenchmarkCase("HS51", "HS51.QPS", 0.0000000, 3, 5),
    BenchmarkCase("HS52", "HS52.QPS", 5.3266476, 3, 5),
    BenchmarkCase("GENHS28", "GENHS28.QPS", 0.92717369, 8, 10),
    BenchmarkCase("LOTSCHD", "LOTSCHD.QPS", 2398.4159, 7, 12),
    BenchmarkCase("HS118", "HS118.QPS", 664.82045, 17, 15),
    BenchmarkCase("QAFIRO", "QAFIRO.QPS", -1.5907818, 27, 32),
    BenchmarkCase("CVXQP2_S", "CVXQP2_S.QPS", 8120.9405, 25, 100),
    BenchmarkCase("CVXQP3_S", "CVXQP3_S.QPS", 11943.432, 75, 100),
]


def _resolve_instance_path(case: BenchmarkCase, cache_dir: Path | None = None) -> Path | None:
    base_dir = cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_problems_dir = base_dir / "problems"
    if not cache_problems_dir.is_dir():
        return None

    # Case-insensitive resolution for cross-platform matching
    expected_name = case.filename.upper()
    for child in cache_problems_dir.iterdir():
        if child.is_file() and child.name.upper() == expected_name:
            return child
    return None


@pytest.mark.benchmark
@pytest.mark.parametrize(
    "case",
    BENCHMARK_CASES,
    ids=lambda c: c.name,
)
def test_maros_meszaros_benchmark_instance(case: BenchmarkCase) -> None:
    instance_path = _resolve_instance_path(case)
    if instance_path is None or not instance_path.is_file():
        pytest.skip(
            f"Maros–Mészáros benchmark data not found for {case.name}. "
            f"Run 'python scripts/fetch_maros_meszaros_benchmark.py' to acquire the benchmark."
        )

    expected_archive, expected_digest = SELECTED_INSTANCE_MANIFEST[case.filename]
    assert expected_archive.startswith("QPDATA")
    assert hashlib.sha256(instance_path.read_bytes()).hexdigest() == expected_digest

    # Load problem through the QPS adapter
    problem = load_qps_file(
        instance_path,
        default_tolerance=1e-10,
        default_max_iterations=50000,
    )

    assert problem["version"] == "1"
    assert problem["problem_type"] == "quadratic_programming"
    assert len(problem["variables"]) == case.n_vars
    # Each ranged source row becomes a lower/upper pair in the public model.
    expected_constraints = 29 if case.name == "HS118" else case.m_rows
    assert len(problem["constraints"]) == expected_constraints

    # Execute through the registered production capability
    service = create_local_optimization_service()
    envelope = service.solve(QP_CAPABILITY_ID, problem)

    assert isinstance(envelope, ExecutionEnvelope)
    assert envelope.capability_id == QP_CAPABILITY_ID
    assert envelope.mathematical_status.value == "optimal"
    assert envelope.result is not None

    # Solution vector checks
    variables = envelope.result["variables"]
    assert len(variables) == case.n_vars
    for var in variables:
        assert isinstance(var["value"], float)

    # Objective comparison against published reference value
    # (Tolerances account for ADMM first-order splitting vs interior-point BPMPD)
    computed_obj = envelope.result["objective"]
    assert computed_obj == pytest.approx(case.expected_opt, rel=1e-4, abs=1e-4)

    # Independent solution validation checks
    assert envelope.validation is not None
    assert envelope.validation.status.value == "verified"

    # Inspect each reported validation check
    checks_by_code = {chk.code: chk for chk in envelope.validation.checks}

    assert "qp.variable_vector" in checks_by_code
    assert checks_by_code["qp.variable_vector"].status == ValidationCheckStatus.PASSED

    assert "qp.bounds" in checks_by_code
    assert checks_by_code["qp.bounds"].status == ValidationCheckStatus.PASSED

    assert "qp.constraints" in checks_by_code
    assert checks_by_code["qp.constraints"].status == ValidationCheckStatus.PASSED

    assert "qp.objective" in checks_by_code
    assert checks_by_code["qp.objective"].status == ValidationCheckStatus.PASSED

    assert "qp.kkt_stationarity" in checks_by_code
    assert checks_by_code["qp.kkt_stationarity"].status == ValidationCheckStatus.PASSED


@pytest.mark.benchmark
def test_maros_meszaros_benchmark_skips_when_cache_missing() -> None:
    non_existent_dir = Path("/tmp/non_existent_cache_optees_benchmark_dir_xyz")
    case = BENCHMARK_CASES[0]
    path = _resolve_instance_path(case, cache_dir=non_existent_dir)
    assert path is None
