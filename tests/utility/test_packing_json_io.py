from __future__ import annotations

import pytest

from optees.utility.packing_json_io import packing_model_from_dict, packing_model_to_dict


def _packing_json() -> dict:
    return {
        "version": "1",
        "problem_type": "packing",
        "variant": "single_container_3d",
        "selection_policy": "all_required",
        "gravity_mode": "simple",
        "container": {
            "id": "c1",
            "name": "Demo container",
            "dimensions": {"length": 10, "width": 5, "height": 4},
            "capacities": [{"name": "weight", "limit": 200}],
        },
        "items": [
            {
                "id": "box",
                "name": "Box",
                "dimensions": {"length": 2, "width": 3, "height": 1},
                "value": 7,
                "quantity": 2,
                "rotation_policy": "custom",
                "allowed_orientations": ["LWH", "WLH"],
                "consumptions": [{"name": "weight", "amount": 12}],
            }
        ],
        "solver_options": {"time_limit": 30, "mip_gap": 0.05},
    }


def test_imports_and_round_trips_single_container_packing_json():
    model = packing_model_from_dict(_packing_json())

    assert model.container.dimensions.as_tuple() == (10.0, 5.0, 4.0)
    assert model.items[0].quantity == 2
    assert [o.code for o in model.items[0].orientations()] == ["LWH", "WLH"]
    assert model.time_limit == pytest.approx(30)
    assert packing_model_to_dict(model) == _packing_json()


def test_import_rejects_unknown_resources():
    data = _packing_json()
    data["items"][0]["consumptions"][0]["name"] = "temperature"

    with pytest.raises(ValueError, match="absent from the container"):
        packing_model_from_dict(data)


def test_import_rejects_invalid_dimensions_and_versions():
    data = _packing_json()
    data["container"]["dimensions"]["length"] = 0
    with pytest.raises(ValueError, match="length must be a finite positive number"):
        packing_model_from_dict(data)

    data = _packing_json()
    data["version"] = "99"
    with pytest.raises(ValueError, match="unsupported packing JSON version"):
        packing_model_from_dict(data)
