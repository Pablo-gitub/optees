from pathlib import Path

import pytest

from optees.utility.orlib_thpack_io import read_orlib_thpack


DATA = Path(__file__).parents[1] / "data" / "packing" / "orlib" / "thpack1.txt"


def test_reads_original_orlib_thpack1_file() -> None:
    instances = read_orlib_thpack(DATA)

    assert len(instances) == 100
    first = instances[0]
    assert first.problem_number == 1
    assert first.seed == 2502505
    assert first.container_dimensions == (587, 233, 220)
    assert first.unit_count() == 112
    assert first.box_types[0].dimensions == (108, 76, 30)
    assert first.box_types[0].vertical_allowed == (False, False, True)
    assert first.box_types[0].quantity == 40


def test_rejects_truncated_thpack_file(tmp_path: Path) -> None:
    path = tmp_path / "truncated.txt"
    path.write_text("1 1 2 10 10", encoding="ascii")

    with pytest.raises(ValueError, match="unexpected end"):
        read_orlib_thpack(path)
