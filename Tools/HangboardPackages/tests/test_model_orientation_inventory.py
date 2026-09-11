from __future__ import annotations

import math
from pathlib import Path

import pytest

from test_model_first_packages import write_model_package
from conftest import load_board_catalog_module


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPOSITORY_ROOT / "Hangboards"
ORIENTATION_AUDIT = (
    REPOSITORY_ROOT
    / "docs"
    / "source-audits"
    / "2026-09-11-3d-board-orientation-audit.md"
)

MODEL_PACKAGE_IDS = {
    "beastmaker-1000",
    "metolius.wood-grips-compact-ii",
    "nature.stone-hanger",
    "yy.baguette-evo",
}


def _discovered_model_packages() -> dict[str, object]:
    module = load_board_catalog_module()
    inventory = module.discover_board_packages(
        HANGBOARDS_ROOT, require_complete_inventory=True
    )
    model_packages: dict[str, object] = {}
    for package in inventory.packages:
        model_presentations = [
            presentation
            for presentation in package.board.presentations
            if isinstance(presentation.media, module.PresentationMediaModel)
        ]
        if model_presentations:
            assert len(model_presentations) == 1, (
                f"{package.board.id} must have exactly one model presentation"
            )
            model_packages[package.board.id] = package
    return model_packages


def _assert_exact_model_position_partition(board: object) -> None:
    hold_ids = tuple(hold.id for hold in board.holds)
    positions = board.positions
    assert positions, "a model with orientation metadata must declare positions"
    assert all(position.hold_ids_authored for position in positions)

    flattened = [hold_id for position in positions for hold_id in position.hold_ids]
    assert all(position.hold_ids for position in positions)
    assert set(flattened) == set(hold_ids)
    assert len(flattened) == len(hold_ids)
    assert len(flattened) == len(set(flattened))
    for position in positions:
        assert tuple(position.hold_ids) == tuple(
            hold_id for hold_id in hold_ids if hold_id in position.hold_ids
        )


def _orientation() -> dict[str, object]:
    return {
        "pivot": "modelBoundsCenter",
        "rotations": {
            "reverse": [0, 1, 0, 0],
            "front": [0, 0, 0, 1],
        },
    }


def _positions() -> list[dict[str, object]]:
    return [
        {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
        {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
    ]


def test_model_orientation_is_normalized_and_membership_is_exact(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, orientation=_orientation(), positions=_positions())
    board = load_board_catalog_module().load_board_package(package).board
    assert board.positions[0].hold_ids == ("hold-left",)
    assert tuple(board.presentations[0].media.orientation.rotations) == ("front", "reverse")
    assert board.hold_ids_for_position("reverse") == ("hold-right",)


def test_legacy_model_positions_materialize_complete_inventory(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, positions=[
        {"id": "front", "presentationID": "primary"},
    ])
    board = load_board_catalog_module().load_board_package(package).board
    assert board.positions[0].hold_ids == ("hold-left", "hold-right")


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("pivot", "wrong", "orientation.pivot"),
        ("rotations", {"front": [0, 0, 0, 1], "unknown": [0, 1, 0, 0]}, "orientation.rotations"),
        ("rotations", {"front": [0, 0, 0, 1]}, "orientation.rotations"),
    ],
)
def test_model_orientation_rejects_invalid_rotation_inventory(
    tmp_path: Path, field: str, value: object, reason: str
) -> None:
    orientation = _orientation()
    orientation[field] = value
    with pytest.raises(ValueError, match=reason):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_unknown_keys_inside_orientation(tmp_path: Path) -> None:
    orientation = _orientation()
    orientation["unexpected"] = True
    with pytest.raises(ValueError, match="orientation has unknown keys"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


@pytest.mark.parametrize("quaternion", [[0, 0, 0, 0], [0, 0, 0, 2], [math.inf, 0, 0, 1], [0.1234567891, 0, 0, 1]])
def test_model_orientation_rejects_non_unit_or_noncanonical_quaternion(
    tmp_path: Path, quaternion: list[float]
) -> None:
    orientation = _orientation()
    orientation["rotations"] = {"front": quaternion, "reverse": [0, 1, 0, 0]}
    with pytest.raises(ValueError, match="orientation.rotations"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_overlapping_or_incomplete_hold_membership(tmp_path: Path) -> None:
    positions = [
        {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left", "hold-right"]},
        {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
    ]
    with pytest.raises(ValueError, match=r"positions\[1\]\.holdIDs"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), positions=positions)
        )


def test_model_positions_reject_duplicate_hold_ids_in_one_position(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"positions\[0\]\.holdIDs.*duplicates"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left", "hold-left"]},
            ])
        )


def test_model_positions_reject_nonempty_incomplete_partition(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="partition"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
            ])
        )


def test_model_positions_reject_mixed_legacy_and_explicit_membership(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"positions\[0\]\.holdIDs"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary"},
                {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-left"]},
            ])
        )


def test_model_orientation_and_suspension_are_mutually_exclusive(tmp_path: Path) -> None:
    # The shared fixture is intentionally not copied here; this checks the closed
    # model-media contract using a minimal orientation-bearing package.
    with pytest.raises(ValueError, match="orientation and suspension are mutually exclusive"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), media_overrides={"suspension": {}})
        )


def test_fixed_model_rejects_orientation_metadata(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="orientation.*fixed"):
        load_board_catalog_module().load_board_package(
            write_model_package(
                tmp_path,
                orientation={"pivot": "modelBoundsCenter", "rotations": {"primary": [0, 0, 0, 1]}},
            )
        )


@pytest.mark.parametrize(
    "positions",
    [
        [
            {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
            {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-left"]},
        ],
        [
            {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left"]},
            {"id": "reverse", "presentationID": "primary", "holdIDs": []},
        ],
        [
            {"id": "front", "presentationID": "primary", "holdIDs": ["hold-left", "unknown"]},
            {"id": "reverse", "presentationID": "primary", "holdIDs": ["hold-right"]},
        ],
    ],
)
def test_model_positions_require_exact_partition_without_orientation(
    tmp_path: Path, positions: list[dict[str, object]]
) -> None:
    with pytest.raises(ValueError, match=r"positions\[|partition"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, positions=positions)
        )


def test_raster_media_rejects_orientation_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown keys.*orientation"):
        load_board_catalog_module().load_board_package(
            write_model_package(tmp_path, media_overrides={"type": "raster", "orientation": _orientation()})
        )


def test_discovered_model_inventory_is_exactly_the_four_current_packages() -> None:
    model_packages = _discovered_model_packages()
    assert set(model_packages) == MODEL_PACKAGE_IDS


@pytest.mark.parametrize(
    "board_id",
    ["beastmaker-1000", "metolius.wood-grips-compact-ii"],
)
def test_fixed_model_packages_keep_one_canonical_position_without_orientation(
    board_id: str,
) -> None:
    package = _discovered_model_packages()[board_id]
    board = package.board
    presentation = next(
        presentation
        for presentation in board.presentations
        if isinstance(
            presentation.media, load_board_catalog_module().PresentationMediaModel
        )
    )
    assert presentation.id == "primary"
    assert presentation.media.orientation is None
    assert presentation.media.suspension is None
    assert len(board.positions) == 1
    position = board.positions[0]
    assert position.id == "primary"
    assert position.presentation_id == "primary"
    assert position.hold_ids == tuple(hold.id for hold in board.holds)


def test_nature_stone_hanger_declares_reviewed_front_and_reverse_orientation() -> None:
    board = _discovered_model_packages()["nature.stone-hanger"].board
    presentation = board.presentations[0]
    media = presentation.media
    assert isinstance(media, load_board_catalog_module().PresentationMediaModel)

    # The review has established the two physical usable faces, but not a
    # final contact-to-face grouping. Keep this test intentionally agnostic to
    # that future Astra judgment while requiring a complete authored matrix.
    assert {position.id for position in board.positions} == {"front", "reverse"}
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_exact_model_position_partition(board)
    assert media.orientation is not None
    assert media.orientation.pivot == "modelBoundsCenter"
    assert set(media.orientation.rotations) == {"front", "reverse"}


def test_baguette_evo_requires_authored_contact_groupings_and_orientation() -> None:
    board = _discovered_model_packages()["yy.baguette-evo"].board
    presentation = board.presentations[0]
    media = presentation.media
    assert isinstance(media, load_board_catalog_module().PresentationMediaModel)

    # Do not encode guessed IDs, grouping, or angles here. The reviewed
    # grouping is deliberately supplied by the later evidence/Astra pass; this
    # RED contract only requires every reviewed grouping to be explicit and to
    # partition the descriptor inventory exactly once.
    assert len(board.positions) > 1
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_exact_model_position_partition(board)
    assert media.orientation is not None
    assert media.orientation.pivot == "modelBoundsCenter"
    assert set(media.orientation.rotations) == {
        position.id for position in board.positions
    }


def test_orientation_audit_records_all_model_packages_and_review_fields() -> None:
    assert ORIENTATION_AUDIT.is_file(), (
        "the orientation audit must be added before model metadata is promoted"
    )
    audit = ORIENTATION_AUDIT.read_text(encoding="utf-8")
    for package_id in sorted(MODEL_PACKAGE_IDS):
        assert package_id in audit, f"missing audit row for {package_id}"
    for required_field in (
        "model bounds",
        "position",
        "hold IDs",
        "pivot",
        "quaternion",
        "evidence",
        "author",
    ):
        assert required_field.casefold() in audit.casefold(), (
            f"orientation audit is missing the {required_field} field"
        )
    assert "authored display estimate" in audit
