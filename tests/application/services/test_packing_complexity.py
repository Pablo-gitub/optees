from optees.application.services.packing_complexity import (
    PackingComplexityLevel,
    estimate_packing_complexity,
)
from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)


def _model(quantity: int) -> SingleContainerPackingModel:
    return SingleContainerPackingModel.from_parts(
        PackingContainer("c", "Container", Dimensions3D(100, 100, 100)),
        (PackingItem.from_parts("cube", "Cube", Dimensions3D(1, 1, 1), quantity=quantity),),
    )


def test_complexity_estimate_exposes_quadratic_pair_term() -> None:
    estimate = estimate_packing_complexity(_model(10))

    assert estimate.unit_count == 10
    assert estimate.pair_count == 45
    assert estimate.separation_binary_count == 270
    assert estimate.orientation_binary_count == 10
    assert estimate.approximate_variable_count == 320
    assert estimate.approximate_constraint_count == 895
    assert estimate.level is PackingComplexityLevel.LOW


def test_complexity_tiers_warn_without_predicting_runtime() -> None:
    assert estimate_packing_complexity(_model(15)).level is PackingComplexityLevel.MODERATE
    assert estimate_packing_complexity(_model(25)).level is PackingComplexityLevel.HIGH
