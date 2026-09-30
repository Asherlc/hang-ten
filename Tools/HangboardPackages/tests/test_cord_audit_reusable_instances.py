from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from hangboard_packages.board_catalog import (
    BoardInventory,
    BoardModelCADRoutedCord,
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
    # Penta Evo's CAD package uses separate per-instance native route graphs.
    assert topologies["yy.penta-evo"] == "cadRoutedCord"


def _paired_lead() -> BoardModelPairedLeadCord:
    return BoardModelPairedLeadCord((), object(), object(), object(), {})


def _single_cord() -> BoardModelSingleCordSuspension:
    return BoardModelSingleCordSuspension(object(), object(), object(), {})


def _cad_routed_cord() -> BoardModelCADRoutedCord:
    return BoardModelCADRoutedCord("body", (), object(), {})


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
    [None, _single_cord(), _cad_routed_cord(), object()],
    ids=["partially-suspended", "mixed-known", "mixed-native", "unknown"],
)
def test_reusable_instance_topology_disagreements_fail_closed(
    second_suspension: object | None,
) -> None:
    inventory = _reusable_inventory(_paired_lead(), second_suspension)

    with pytest.raises(CordAuditError):
        _model_package_topologies(inventory)


def test_reusable_native_routes_preserve_per_instance_topology() -> None:
    inventory = _reusable_inventory(_cad_routed_cord(), _cad_routed_cord())

    assert _model_package_topologies(inventory) == {"fixture.reusable": "cadRoutedCord"}


def test_reusable_native_routes_cannot_leave_one_instance_unsuspended() -> None:
    with pytest.raises(CordAuditError):
        _model_package_topologies(_reusable_inventory(_cad_routed_cord(), None))


def test_native_configurations_keep_one_consistent_package_topology() -> None:
    inventory = _reusable_inventory(_cad_routed_cord(), _cad_routed_cord())
    board = inventory.packages[0].board
    # A physical configurable board may export several native model assets.
    board.presentations = board.presentations * 3

    assert _model_package_topologies(inventory) == {"fixture.reusable": "cadRoutedCord"}


def test_native_configurations_cannot_hide_a_topology_disagreement() -> None:
    inventory = _reusable_inventory(_cad_routed_cord(), _cad_routed_cord())
    board = inventory.packages[0].board
    other = _reusable_inventory(_paired_lead(), _paired_lead()).packages[0].board
    board.presentations += other.presentations

    with pytest.raises(CordAuditError):
        _model_package_topologies(inventory)
