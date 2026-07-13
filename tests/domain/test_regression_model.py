from __future__ import annotations

import pytest

from optees.domain.entities.regression.dataset import RegressionDataset
from optees.domain.models.regression.regression_model import RegressionModel, RegressionOptions
from optees.domain.value_objects.regression.regression_method import RegressionMethod


def _dataset() -> RegressionDataset:
    return RegressionDataset.from_rows(
        feature_names=("size",),
        target_name="price",
        rows=[((1,), 3), ((2,), 5), ((3,), 7), ((4,), 9)],
    )


def test_dataset_normalizes_numeric_rows_and_model_keeps_options() -> None:
    model = RegressionModel(
        dataset=_dataset(),
        options=RegressionOptions(method="ridge", test_fraction=0.25, random_seed=7, ridge_alpha=2),
    )

    assert model.dataset.feature_rows == ((1.0,), (2.0,), (3.0,), (4.0,))
    assert model.dataset.target_values == (3.0, 5.0, 7.0, 9.0)
    assert model.options.method is RegressionMethod.RIDGE
    assert model.options.test_fraction == 0.25
    assert model.options.ridge_alpha == 2.0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"feature_names": (), "target_name": "y", "feature_rows": (), "target_values": ()}, "feature"),
        ({"feature_names": ("x",), "target_name": "x", "feature_rows": ((1,),) * 4, "target_values": (1,) * 4}, "target"),
        ({"feature_names": ("x",), "target_name": "y", "feature_rows": ((1,),) * 3, "target_values": (1,) * 3}, "four"),
        ({"feature_names": ("x",), "target_name": "y", "feature_rows": ((1, 2),) * 4, "target_values": (1,) * 4}, "row"),
        ({"feature_names": ("x",), "target_name": "y", "feature_rows": ((1,),) * 4, "target_values": (1, 2, 3, float("nan"))}, "finite"),
    ],
)
def test_dataset_rejects_invalid_shapes_and_values(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        RegressionDataset(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"test_fraction": 0},
        {"test_fraction": 1},
        {"test_fraction": True},
        {"random_seed": -1},
        {"random_seed": 1.5},
        {"ridge_alpha": 0},
        {"ridge_alpha": float("inf")},
        {"method": "random-forest"},
    ],
)
def test_options_reject_invalid_values(kwargs: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        RegressionOptions(**kwargs)  # type: ignore[arg-type]
