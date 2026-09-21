from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hangboard_packages.board_catalog import (
    BoardInventory,
    BoardModelInstance,
    BoardModelPairedLeadCord,
    BoardModelSingleCordSuspension,
    BoardModelTransform,
    BoardPackage,
    PresentationMediaModel,
    discover_board_packages,
)
from hangboard_packages.cord_audit import CordAuditError, _model_package_topologies


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_reusable_rock_rings_discovers_documented_per_instance_topology() -> None:
    inventory = discover_board_packages(
        REPO_ROOT / "Hangboards", require_complete_inventory=True
    )

    topologies = _model_package_topologies(inventory)

    assert topologies["metolius.rock-rings-3d"] == "pairedLeadCord"


def _paired_lead() -> BoardModelPairedLeadCord:
    return BoardModelPairedLeadCord((), object(), object(), object(), {})


def _single_cord() -> BoardModelSingleCordSuspension:
    return BoardModelSingleCordSuspension(object(), object(), object(), {})


def _reusable_inventory(*suspensions: object | None) -> BoardInventory:
    transform = BoardModelTransform((0.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0), None)
    instances = tuple(
        BoardModelInstance(
            equipment_object_id=f"unit-{index}",
            base_transform=transform,
            contact_ids_by_slot_id={},
            suspension=suspension,
            position_transforms={},
        )
        for index, suspension in enumerate(suspensions)
    )
    media = PresentationMediaModel(
        asset_path="assets/primary.usdz",
        descriptor_path="assets/primary.model.json",
        display={},
        instances=instances,  # type: ignore[arg-type]
    )
    board = SimpleNamespace(
        id="fixture.reusable",
        presentations=(SimpleNamespace(media=media),),
    )
    return BoardInventory(
        packages=(BoardPackage(root=Path("fixture"), board=board),),  # type: ignore[arg-type]
        drafts=(),
    )


@pytest.mark.parametrize(
    "second_suspension",
    [None, _single_cord(), object()],
    ids=["partially-suspended", "mixed-known", "unknown"],
)
def test_reusable_instance_topology_disagreements_fail_closed(
    second_suspension: object | None,
) -> None:
    inventory = _reusable_inventory(_paired_lead(), second_suspension)

    with pytest.raises(CordAuditError):
        _model_package_topologies(inventory)
