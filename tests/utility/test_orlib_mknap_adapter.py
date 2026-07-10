from __future__ import annotations

from pathlib import Path

import pytest

from optees.utility.data_adapters.orlib_mknap_adapter import load_orlib_mknap


DATASET = Path("tests/data/knapsack/orlib/mknap1.txt")


def test_loads_first_orlib_mknap_instance_in_optees_matrix_orientation():
    problem = load_orlib_mknap(DATASET, instance_index=1)

    assert problem["known_optimum"] == pytest.approx(3800.0)
    assert problem["values"] == [100.0, 600.0, 1200.0, 2400.0, 500.0, 2000.0]
    assert problem["capacities"] == [80.0, 96.0, 20.0, 36.0, 44.0, 48.0, 10.0, 18.0, 22.0, 24.0]
    assert problem["usage_matrix"][0] == [8.0, 8.0, 3.0, 5.0, 5.0, 5.0, 0.0, 3.0, 3.0, 3.0]
    assert len(problem["usage_matrix"]) == 6
    assert all(len(row) == 10 for row in problem["usage_matrix"])
    assert problem["metadata"] == {
        "source": "OR-Library",
        "dataset": "mknap1",
        "instance_index": 1,
        "source_url": "https://people.brunel.ac.uk/~mastjjb/jeb/orlib/mknapinfo.html",
        "item_count": 6,
        "resource_count": 10,
    }


def test_loads_later_orlib_instance_with_decimal_known_optimum():
    problem = load_orlib_mknap(DATASET, instance_index=2)

    assert problem["known_optimum"] == pytest.approx(8706.1)
    assert len(problem["values"]) == 10
    assert len(problem["capacities"]) == 10
    assert problem["usage_matrix"][0] == [20.0, 20.0, 60.0, 60.0, 60.0, 60.0, 5.0, 45.0, 55.0, 65.0]


@pytest.mark.parametrize("instance_index", [0, -1, True, 8])
def test_rejects_invalid_or_out_of_range_instance_index(instance_index):
    with pytest.raises(ValueError):
        load_orlib_mknap(DATASET, instance_index=instance_index)


def test_rejects_truncated_file(tmp_path):
    path = tmp_path / "truncated.txt"
    path.write_text("1\n2 1 10\n1 2\n3 4\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing capacities"):
        load_orlib_mknap(path, instance_index=1)


def test_rejects_non_finite_coefficients(tmp_path):
    path = tmp_path / "non_finite.txt"
    path.write_text("1\n1 1 10\nnan\n3\n4\n", encoding="utf-8")

    with pytest.raises(ValueError, match="invalid profits"):
        load_orlib_mknap(path, instance_index=1)
