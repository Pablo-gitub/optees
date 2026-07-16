from __future__ import annotations

import json
from pathlib import Path

from optees.domain.entities.packing.container import PackingContainer
from optees.domain.entities.packing.geometry import Dimensions3D
from optees.domain.entities.packing.item import PackingItem
from optees.domain.entities.packing.resource import ResourceCapacity, ResourceConsumption
from optees.domain.models.packing.single_container_packing_model import (
    SingleContainerPackingModel,
)
from optees.domain.value_objects.packing.rotation_policy import RotationPolicy
from optees.domain.value_objects.packing.selection_policy import PackingSelectionPolicy
from optees.domain.value_objects.packing.gravity_mode import PackingGravityMode


PACKING_JSON_VERSION = "1"
SINGLE_CONTAINER_VARIANT = "single_container_3d"


def packing_model_from_file(path: str | Path) -> SingleContainerPackingModel:
    return packing_model_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def packing_model_to_file(model: SingleContainerPackingModel, path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(packing_model_to_dict(model), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def packing_model_from_dict(data: object) -> SingleContainerPackingModel:
    if not isinstance(data, dict):
        raise ValueError("packing JSON root must be an object")
    version = str(data.get("version", PACKING_JSON_VERSION))
    if version != PACKING_JSON_VERSION:
        raise ValueError(f"unsupported packing JSON version: {version!r}")
    if str(data.get("problem_type", "packing")).strip().lower() != "packing":
        raise ValueError("problem_type must be 'packing'")
    if str(data.get("variant", SINGLE_CONTAINER_VARIANT)).strip().lower() != SINGLE_CONTAINER_VARIANT:
        raise ValueError(f"variant must be {SINGLE_CONTAINER_VARIANT!r}")

    raw_container = data.get("container")
    if not isinstance(raw_container, dict):
        raise ValueError("container must be an object")
    container = PackingContainer.from_parts(
        container_id=str(raw_container.get("id", "container-1")),
        name=str(raw_container.get("name", "Container 1")),
        dimensions=_dimensions_from_json(raw_container.get("dimensions"), "container.dimensions"),
        capacities=_capacities_from_json(raw_container.get("capacities", ())),
    )

    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("items must be a non-empty array")
    items = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        policy = RotationPolicy.from_str(raw.get("rotation_policy", "any_orthogonal"))
        custom_codes = raw.get("allowed_orientations", ())
        if not isinstance(custom_codes, list):
            raise ValueError(f"items[{index}].allowed_orientations must be an array")
        items.append(
            PackingItem.from_parts(
                item_id=str(raw.get("id", f"item-{index + 1}")),
                name=str(raw.get("name", f"Item {index + 1}")),
                dimensions=_dimensions_from_json(raw.get("dimensions"), f"items[{index}].dimensions"),
                value=raw.get("value", 1.0),
                quantity=_positive_int(raw.get("quantity", 1), f"items[{index}].quantity"),
                rotation_policy=policy,
                custom_orientation_codes=custom_codes,
                consumptions=_consumptions_from_json(raw.get("consumptions", ()), index),
            )
        )

    solver_options = data.get("solver_options", {})
    if not isinstance(solver_options, dict):
        raise ValueError("solver_options must be an object")
    return SingleContainerPackingModel.from_parts(
        container,
        items,
        selection_policy=PackingSelectionPolicy.from_str(data.get("selection_policy", "optional")),
        gravity_mode=PackingGravityMode.from_str(data.get("gravity_mode", "simple")),
        time_limit=solver_options.get("time_limit"),
        mip_gap=solver_options.get("mip_gap"),
    )


def packing_model_to_dict(model: SingleContainerPackingModel) -> dict:
    return {
        "version": PACKING_JSON_VERSION,
        "problem_type": "packing",
        "variant": SINGLE_CONTAINER_VARIANT,
        "selection_policy": model.selection_policy.value,
        "gravity_mode": model.gravity_mode.value,
        "container": {
            "id": model.container.container_id,
            "name": model.container.name,
            "dimensions": _dimensions_to_json(model.container.dimensions),
            "capacities": [
                {"name": capacity.name, "limit": capacity.limit}
                for capacity in model.container.capacities
            ],
        },
        "items": [
            {
                "id": item.item_id,
                "name": item.name,
                "dimensions": _dimensions_to_json(item.dimensions),
                "value": item.value,
                "quantity": item.quantity,
                "rotation_policy": item.rotation_policy.value,
                "allowed_orientations": list(item.custom_orientation_codes),
                "consumptions": [
                    {"name": consumption.name, "amount": consumption.amount}
                    for consumption in item.consumptions
                ],
            }
            for item in model.items
        ],
        "solver_options": {
            "time_limit": model.time_limit,
            "mip_gap": model.mip_gap,
        },
    }


def _dimensions_from_json(value: object, label: str) -> Dimensions3D:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    try:
        return Dimensions3D(value["length"], value["width"], value["height"])
    except KeyError as exc:
        raise ValueError(f"{label} requires length, width, and height") from exc


def _dimensions_to_json(value: Dimensions3D) -> dict:
    return {"length": value.length, "width": value.width, "height": value.height}


def _capacities_from_json(value: object) -> tuple[ResourceCapacity, ...]:
    if not isinstance(value, list):
        raise ValueError("container.capacities must be an array")
    capacities = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"container.capacities[{index}] must be an object")
        capacities.append(ResourceCapacity(str(raw.get("name", "")), raw.get("limit")))
    return tuple(capacities)


def _consumptions_from_json(value: object, item_index: int) -> tuple[ResourceConsumption, ...]:
    if not isinstance(value, list):
        raise ValueError(f"items[{item_index}].consumptions must be an array")
    consumptions = []
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{item_index}].consumptions[{index}] must be an object")
        consumptions.append(ResourceConsumption(str(raw.get("name", "")), raw.get("amount")))
    return tuple(consumptions)


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a positive integer")
    parsed = float(value)  # type: ignore[arg-type]
    if not parsed.is_integer() or parsed <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return int(parsed)
