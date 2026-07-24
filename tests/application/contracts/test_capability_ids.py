from optees.application.contracts.capability_ids import PUBLIC_CAPABILITY_IDS
from optees.application.services.analytic_artifact_visuals import (
    analytic_visual_definitions,
)
from optees.application.services.canonical_artifact_tables import (
    canonical_table_definitions,
)
from optees.application.services.categorical_artifact_visuals import (
    categorical_visual_definitions,
)
from optees.application.services.lp_artifact_visuals import lp_visual_definitions
from optees.application.services.packing_artifact_scene import (
    packing_scene_definitions,
)
from optees.composition.local_agent import create_local_optimization_service


def test_public_capability_ids_are_unique_and_match_production_registry() -> None:
    assert len(PUBLIC_CAPABILITY_IDS) == len(set(PUBLIC_CAPABILITY_IDS))

    registered_ids = tuple(
        descriptor["id"]
        for descriptor in create_local_optimization_service().list_capabilities()
    )

    assert set(registered_ids) == set(PUBLIC_CAPABILITY_IDS)


def test_artifact_definitions_reference_public_capabilities() -> None:
    definitions = (
        canonical_table_definitions()
        + categorical_visual_definitions()
        + analytic_visual_definitions()
        + lp_visual_definitions()
        + packing_scene_definitions()
    )

    assert {definition.capability_id for definition in definitions} <= set(
        PUBLIC_CAPABILITY_IDS
    )
