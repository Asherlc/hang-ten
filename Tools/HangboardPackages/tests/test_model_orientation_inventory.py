from __future__ import annotations

import functools
import hashlib
import json
import math
from pathlib import Path

import pytest

from conftest import load_board_catalog_module, package_board_text
from test_model_first_packages import _write_reusable_model_package, write_model_package


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
HANGBOARDS_ROOT = REPOSITORY_ROOT / "Hangboards"
ORIENTATION_AUDIT = (
    REPOSITORY_ROOT
    / "docs"
    / "source-audits"
    / "2026-09-11-3d-board-orientation-audit.md"
)
BOARD_CATALOG = load_board_catalog_module()

MODEL_PACKAGE_IDS = {
    "beastmaker-1000",
    "beastmaker-2000",
    "captain-fingerfood.dual",
    "captain-fingerfood.pocket",
    "captain-fingerfood.unlevel",
    "crimptonite.helium-mobile",
    "dewoodstok-woodbord",
    "escape-beta-22",
    "escape.unlimited",
    "evolv-kilter-basic-long",
    "j-bryant.ftg-32",
    "lattice-triple-rung",
    "lattice.mxedge-lift-large",
    "lattice.mxedge-lift-small",
    "mammut.diamond-finger",
    "metolius.foundry",
    "metolius.light-rail-2",
    "metolius.rock-rings-3d",
    "owl-climb.poker",
    "yy.penta-evo",
    "metolius.prime-rib",
    "metolius.project",
    "metolius.climbers-edge",
    "metolius.contact",
    "metolius.simulator-3d",
    "metolius.wood-grips-compact-ii",
    "metolius.wood-grips-deluxe-ii",
    "moon.armstrong",
    "nature.stoak-board-iii",
    "nature.stone-hanger",
    "target10a.linebreaker-base",
    "tension.flash-board",
    "soill.iron-palm-2",
    "soill.split-palm",
    "soill.training-tiles",
    "the-hangboard.the-hangboard",
    "trango.rock-prodigy-pivot",
    "trango.rock-prodigy-training-center",
    "yy.baguette-evo",
    "clavellium-training-block",
    "zlagboard.evo",
    "zlagboard.pro",
    "frictitious.doormount-pro-7",
    "frictitious.megalith",
    "trango.rock-prodigy-forge",
    "trango.rock-prodigy-natural",
}

FIXED_FRONT_MODEL_PACKAGE_SLUGS = (
    "dewoodstok-woodbord",
    "escape-unlimited",
    "evolv-kilter-basic-long",
    "metolius-wood-grips-deluxe-ii",
    "moon-armstrong",
    "target10a-linebreaker-base",
)


@functools.cache
def _discovered_model_packages() -> dict[str, object]:
    inventory = BOARD_CATALOG.discover_board_packages(
        HANGBOARDS_ROOT, require_complete_inventory=True
    )
    model_packages: dict[str, object] = {}
    for package in inventory.packages:
        model_presentations = [
            presentation
            for presentation in package.board.presentations
            if isinstance(presentation.media, BOARD_CATALOG.PresentationMediaModel)
        ]
        if model_presentations:
            assert len(model_presentations) == 1, (
                f"{package.board.id} must have exactly one model presentation"
            )
            model_packages[package.board.id] = package
    return model_packages


def _assert_model_position_union_coverage(board: object) -> None:
    hold_ids = tuple(hold.id for hold in board.contacts)
    positions = board.positions
    assert positions, "a model with orientation metadata must declare positions"
    assert all(position.contact_ids_authored for position in positions)

    flattened = [hold_id for position in positions for hold_id in position.contact_ids]
    assert all(position.contact_ids for position in positions)
    # Union must cover all descriptor holds (no missing holds)
    assert set(flattened) == set(hold_ids)
    # No duplicates within a single position
    for position in positions:
        assert len(position.contact_ids) == len(set(position.contact_ids))
        # Canonical order
        assert tuple(position.contact_ids) == tuple(
            hold_id for hold_id in hold_ids if hold_id in position.contact_ids
        )
    # Overlap across positions is now allowed (e.g., upright/inverted same face)


def _orientation() -> dict[str, object]:
    return {
        "pivot": "modelBoundsCenter",
        "rotations": {
            "front": [0, 0, 0, 1],
            "reverse": [0, 1, 0, 0],
        },
    }


def _positions() -> list[dict[str, object]]:
    return [
        {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left"]},
        {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-right"]},
    ]


def test_model_orientation_preserves_canonical_order_and_union_coverage(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, orientation=_orientation(), positions=_positions())
    board = BOARD_CATALOG.load_board_package(package).board
    assert board.positions[0].contact_ids == ("hold-left",)
    assert tuple(board.presentations[0].media.orientation.rotations) == ("front", "reverse")
    assert board.contact_ids_for_position("reverse") == ("hold-right",)


def test_legacy_model_positions_materialize_complete_inventory(tmp_path: Path) -> None:
    package = write_model_package(tmp_path, positions=[
        {"id": "front", "presentationID": "primary"},
    ])
    board = BOARD_CATALOG.load_board_package(package).board
    assert board.positions[0].contact_ids == ("hold-left", "hold-right")


def test_reusable_model_instances_are_the_only_pose_mechanism(tmp_path: Path) -> None:
    media = BOARD_CATALOG.load_board_package(
        _write_reusable_model_package(tmp_path)
    ).board.presentations[0].media

    assert media.instances is not None
    assert media.orientation is None
    assert media.suspension is None


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("pivot", "wrong", r"orientation\.pivot"),
        ("rotations", {"front": [0, 0, 0, 1], "unknown": [0, 1, 0, 0]}, r"orientation\.rotations"),
        ("rotations", {"front": [0, 0, 0, 1]}, r"orientation\.rotations"),
    ],
)
def test_model_orientation_rejects_invalid_rotation_inventory(
    tmp_path: Path, field: str, value: object, reason: str
) -> None:
    orientation = _orientation()
    orientation[field] = value
    with pytest.raises(ValueError, match=reason):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_noncanonical_member_order(tmp_path: Path) -> None:
    orientation = {
        "rotations": {"front": [0, 0, 0, 1], "reverse": [0, 1, 0, 0]},
        "pivot": "modelBoundsCenter",
    }
    with pytest.raises(ValueError, match=r"orientation.*canonical member order"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_unsorted_rotation_ids(tmp_path: Path) -> None:
    orientation = {
        "pivot": "modelBoundsCenter",
        "rotations": {"reverse": [0, 1, 0, 0], "front": [0, 0, 0, 1]},
    }
    with pytest.raises(ValueError, match=r"orientation\.rotations.*sorted"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_rejects_unknown_keys_inside_orientation(tmp_path: Path) -> None:
    orientation = _orientation()
    orientation["unexpected"] = True
    with pytest.raises(ValueError, match="orientation has unknown keys"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


@pytest.mark.parametrize("quaternion", [[0, 0, 0, 0], [0, 0, 0, 2], [math.inf, 0, 0, 1], [0.1234567891, 0, 0, 1]])
def test_model_orientation_rejects_non_unit_or_noncanonical_quaternion(
    tmp_path: Path, quaternion: list[float]
) -> None:
    orientation = _orientation()
    orientation["rotations"] = {"front": quaternion, "reverse": [0, 1, 0, 0]}
    with pytest.raises(ValueError, match=r"orientation\.rotations"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=orientation, positions=_positions())
        )


def test_model_orientation_allows_overlapping_hold_membership(tmp_path: Path) -> None:
    # Overlap is now allowed: a hold may appear in multiple positions
    positions = [
        {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left", "hold-right"]},
        {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-right"]},
    ]
    board = BOARD_CATALOG.load_board_package(
        write_model_package(tmp_path, orientation=_orientation(), positions=positions)
    ).board
    assert board.positions[0].contact_ids == ("hold-left", "hold-right")
    assert board.positions[1].contact_ids == ("hold-right",)


def test_model_orientation_rejects_incomplete_union_coverage(tmp_path: Path) -> None:
    # Union must cover all descriptor holds (hold-left, hold-right)
    positions = [
        {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left"]},
        {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-left"]},  # missing hold-right
    ]
    with pytest.raises(ValueError, match="union coverage"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), positions=positions)
        )


def test_model_positions_reject_duplicate_hold_ids_in_one_position(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"positions\[0\]\.contactIDs.*duplicates"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left", "hold-left"]},
            ])
        )


def test_model_positions_reject_nonempty_incomplete_union(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="union coverage"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left"]},
            ])
        )


def test_model_positions_reject_mixed_legacy_and_explicit_membership(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"positions\[0\]\.contactIDs"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, positions=[
                {"id": "front", "presentationID": "primary"},
                {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-left"]},
            ])
        )


def test_model_orientation_and_suspension_are_parsed_independently(tmp_path: Path) -> None:
    # The suspension remains independently validated; orientation metadata does
    # not make an otherwise malformed suspension look valid.
    with pytest.raises(ValueError, match=r"suspension\.type"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, orientation=_orientation(), media_overrides={"suspension": {}})
        )


def test_fixed_model_rejects_orientation_metadata(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"orientation.*fixed"):
        BOARD_CATALOG.load_board_package(
            write_model_package(
                tmp_path,
                orientation={"pivot": "modelBoundsCenter", "rotations": {"primary": [0, 0, 0, 1]}},
            )
        )


@pytest.mark.parametrize(
    "positions",
    [
        [
            {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left"]},
            {"id": "reverse", "presentationID": "primary", "contactIDs": []},
        ],
        [
            {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left", "unknown"]},
            {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-right"]},
        ],
    ],
)
def test_model_positions_reject_empty_or_unknown_holds(
    tmp_path: Path, positions: list[dict[str, object]]
) -> None:
    with pytest.raises(ValueError, match=r"positions\["):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, positions=positions)
        )


def test_model_positions_allow_overlap_without_orientation(tmp_path: Path) -> None:
    # Overlap is allowed even without orientation metadata
    positions = [
        {"id": "front", "presentationID": "primary", "contactIDs": ["hold-left", "hold-right"]},
        {"id": "reverse", "presentationID": "primary", "contactIDs": ["hold-right"]},
    ]
    board = BOARD_CATALOG.load_board_package(
        write_model_package(tmp_path, positions=positions)
    ).board
    assert board.positions[0].contact_ids == ("hold-left", "hold-right")
    assert board.positions[1].contact_ids == ("hold-right",)


def test_raster_media_rejects_orientation_key(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"unknown keys.*orientation"):
        BOARD_CATALOG.load_board_package(
            write_model_package(tmp_path, media_overrides={"type": "raster", "orientation": _orientation()})
        )


def test_j_bryant_ftg32_one_sided_positions_are_an_exact_z_half_turn() -> None:
    board = _discovered_model_packages()["j-bryant.ftg-32"].board
    media = board.presentations[0].media
    assert isinstance(media, BOARD_CATALOG.PresentationMediaModel)
    assert [(p.id, p.contact_ids) for p in board.positions] == [
        ("edge-25-down", ("edge-25",)),
        ("edge-16-down", ("edge-16",)),
    ]
    assert media.orientation is not None
    assert media.orientation.pivot == "modelBoundsCenter"
    assert media.orientation.rotations == {
        "edge-25-down": (0, 0, 0, 1),
        "edge-16-down": (0, 0, 1, 0),
    }
    assert media.suspension is not None
    assert {key: pose.rotation for key, pose in media.suspension.canonical_poses.items()} == media.orientation.rotations
    _assert_model_position_union_coverage(board)


def test_discovered_model_inventory_matches_current_packages() -> None:
    model_packages = _discovered_model_packages()
    assert set(model_packages) == MODEL_PACKAGE_IDS


def test_fixed_front_model_presentation_ratios_match_descriptor_bounds() -> None:
    for slug in FIXED_FRONT_MODEL_PACKAGE_SLUGS:
        package_path = HANGBOARDS_ROOT / slug
        board = json.loads(package_board_text(package_path))
        presentations = [item for item in board["presentations"] if item["media"]["type"] == "model"]
        assert len(presentations) == 1, slug
        presentation = presentations[0]
        descriptor_path = package_path / presentation["media"]["descriptorPath"]
        descriptor = json.loads(descriptor_path.read_text())
        bounds = descriptor["modelBounds"]
        expected = (bounds["max"][0] - bounds["min"][0]) / (
            bounds["max"][1] - bounds["min"][1]
        )
        assert presentation["aspectRatio"] == pytest.approx(
            expected, rel=1e-9, abs=1e-9
        ), slug


def test_flash_board_uses_suspension_with_corrected_small_crimp_contacts() -> None:
    board = _discovered_model_packages()["tension.flash-board"].board
    media = board.presentations[0].media
    assert isinstance(media, BOARD_CATALOG.PresentationMediaModel)
    assert media.suspension is not None
    assert media.orientation is None
    positions = {position.id: position for position in board.positions}
    assert set(positions) == {
        "three-edge-upright",
        "three-edge-inverted",
        "two-edge-upright",
        "two-edge-inverted",
    }
    assert set(media.suspension.canonical_poses) == set(positions)
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_model_position_union_coverage(board)
    assert positions["three-edge-upright"].contact_ids == positions["three-edge-inverted"].contact_ids
    assert positions["two-edge-upright"].contact_ids == positions["two-edge-inverted"].contact_ids
    assert set(positions["two-edge-upright"].contact_ids) == {
        "two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"
    }
    assert set(positions["three-edge-upright"].contact_ids).isdisjoint(
        positions["two-edge-upright"].contact_ids
    )


def test_rock_rings_uses_two_identical_unreflected_units_with_independent_cords() -> None:
    board = _discovered_model_packages()["metolius.rock-rings-3d"].board
    presentation = next(
        presentation
        for presentation in board.presentations
        if isinstance(presentation.media, BOARD_CATALOG.PresentationMediaModel)
    )
    media = presentation.media
    assert media.instances is not None
    assert media.orientation is None
    assert media.suspension is None
    assert len(media.instances) == 2

    expected_slots = ("jug", "pocket-40", "pocket-32", "pocket-25")
    expected_maps = (
        {
            "jug": "jug-left",
            "pocket-40": "pocket-40-four-left",
            "pocket-32": "pocket-32-three-left",
            "pocket-25": "pocket-25-two-left",
        },
        {
            "jug": "jug-right",
            "pocket-40": "pocket-40-four-right",
            "pocket-32": "pocket-32-three-right",
            "pocket-25": "pocket-25-two-right",
        },
    )
    assert [instance.equipment_object_id for instance in media.instances] == [
        "left-ring",
        "right-ring",
    ]
    for instance, expected_map in zip(media.instances, expected_maps):
        assert set(instance.contact_ids_by_slot_id) == set(expected_slots)
        assert dict(instance.contact_ids_by_slot_id) == expected_map
        assert instance.base_transform.rotation == (0, 0, 0, 1)
        assert instance.base_transform.reflection is None
        assert instance.position_transforms is None
        assert instance.suspension is not None
        assert len(instance.suspension.attachments) == 2
        assert instance.suspension.anchor.visibility == "invisible"

    # Each unit owns its own paired lead cord and anchor state.
    left_suspension = media.instances[0].suspension
    right_suspension = media.instances[1].suspension
    assert left_suspension is not right_suspension
    assert left_suspension is not None and right_suspension is not None
    assert left_suspension.attachments is not right_suspension.attachments


def test_penta_evo_uses_two_identical_unreflected_units_with_exact_slot_maps() -> None:
    board = _discovered_model_packages()["yy.penta-evo"].board
    presentation = next(
        presentation
        for presentation in board.presentations
        if isinstance(presentation.media, BOARD_CATALOG.PresentationMediaModel)
    )
    media = presentation.media
    assert media.instances is not None
    assert media.orientation is None
    assert media.suspension is None
    assert len(media.instances) == 2

    slots = ("edge-25", "edge-20", "edge-15", "edge-10", "mono", "duo", "tray")
    expected_maps = (
        {slot: f"{slot}-left" for slot in slots},
        {slot: f"{slot}-right" for slot in slots},
    )
    assert [instance.equipment_object_id for instance in media.instances] == [
        "left-penta", "right-penta"
    ]
    left_instance, right_instance = media.instances
    for instance, expected_map in zip(media.instances, expected_maps, strict=True):
        assert dict(instance.contact_ids_by_slot_id) == expected_map
        assert instance.base_transform.rotation == (0, 0, 0, 1)
        assert instance.base_transform.reflection is None
        assert instance.position_transforms is None
        assert instance.suspension is not None
        assert len(instance.suspension.attachments) == 2
        assert instance.suspension.anchor.visibility == "invisible"
        assert set(instance.suspension.canonical_poses) == {"primary", "reverse"}
    assert left_instance.suspension is not None
    assert right_instance.suspension is not None
    for position_id, expected_rotation in {
        "primary": (0, 0, 0, 1),
        "reverse": (0, 1, 0, 0),
    }.items():
        left_pose = left_instance.suspension.canonical_poses[position_id]
        right_pose = right_instance.suspension.canonical_poses[position_id]
        assert left_pose.rotation == right_pose.rotation
        assert left_pose.rotation == expected_rotation
    assert media.instances[0].suspension is not media.instances[1].suspension
    assert {position.id for position in board.positions} == {"primary", "reverse"}
    assert all(position.presentation_id == presentation.id for position in board.positions)
    expected_position_contacts = {
        "primary": {
            contact.id for contact in board.contacts
            if contact.id not in {"edge-10-left", "edge-10-right"}
        },
        "reverse": {
            contact.id for contact in board.contacts
            if contact.id.rsplit("-", 1)[0] in {"edge-10", "mono", "duo", "tray"}
        },
    }
    assert {position.id: set(position.contact_ids) for position in board.positions} == expected_position_contacts
    assert {len(position.contact_ids) for position in board.positions} == {8, 12}
    for position in board.positions:
        expected_order = tuple(
            contact.id for contact in board.contacts
            if contact.id in expected_position_contacts[position.id]
        )
        assert position.contact_ids == expected_order


def test_pivot_uses_one_reflected_half_with_four_selectable_positions() -> None:
    """Catch a lost reflection, an incomplete pose map, or a selectable p4."""
    board = _discovered_model_packages()["trango.rock-prodigy-pivot"].board
    presentation = next(
        presentation
        for presentation in board.presentations
        if isinstance(presentation.media, BOARD_CATALOG.PresentationMediaModel)
    )
    media = presentation.media
    assert media.instances is not None and len(media.instances) == 2
    assert media.orientation is None
    assert media.suspension is None

    slots = (
        "upper-sloped-crimp",
        "outer-sloped-crimp",
        "variable-edge",
        "medium-crimp",
        "large-crimp",
        "two-finger-pocket",
        "three-finger-pocket",
        "outer-wedge-pinch",
        "lower-sloper",
    )
    left_instance, right_instance = media.instances
    assert [instance.equipment_object_id for instance in media.instances] == [
        "left-half", "right-half"
    ]
    assert left_instance.base_transform.reflection is None
    assert right_instance.base_transform.reflection == "x"
    for instance, side in ((left_instance, "left"), (right_instance, "right")):
        assert instance.suspension is None
        assert instance.base_transform.rotation == (0, 0, 0, 1)
        assert instance.base_transform.translation == (0, 0, 0)
        assert dict(instance.contact_ids_by_slot_id) == {
            slot: f"{slot}-{side}" for slot in slots
        }
        assert instance.position_transforms is not None
        assert set(instance.position_transforms) == {"p1", "p2", "p3", "p5"}
        for transform in instance.position_transforms.values():
            assert transform.reflection is None
            assert all(math.isfinite(value) for value in transform.translation)
            assert math.isclose(
                math.sqrt(sum(value * value for value in transform.rotation)),
                1.0,
                abs_tol=1e-6,
            )

    # Both halves keep the same key set; the right one mirrors every quarter turn.
    assert set(left_instance.position_transforms) == set(right_instance.position_transforms)
    for position_id in ("p1", "p2", "p3", "p5"):
        left = left_instance.position_transforms[position_id]
        right = right_instance.position_transforms[position_id]
        assert left.rotation[0] == right.rotation[0] == 0
        assert left.rotation[1] == right.rotation[1] == 0
        assert left.rotation[2] == pytest.approx(-right.rotation[2], abs=1e-12)
        assert left.rotation[3] == pytest.approx(right.rotation[3], abs=1e-12)
        assert left.translation == pytest.approx(
            tuple(-value for value in right.translation), abs=1e-12
        )
    # p5 exchanges the physical halves; p1 through p3 keep them in place.
    assert left_instance.position_transforms["p1"].translation[0] < 0
    assert left_instance.position_transforms["p2"].translation[0] < 0
    assert left_instance.position_transforms["p3"].translation[0] < 0
    assert left_instance.position_transforms["p5"].translation[0] > 0

    assert [position.id for position in board.positions] == ["p1", "p2", "p3", "p5"]
    assert all(position.presentation_id == presentation.id for position in board.positions)
    assert {contact.id for contact in board.contacts} == {
        f"{slot}-{side}" for slot in slots for side in ("left", "right")
    }


def test_poker_is_one_model_with_four_source_face_orientations() -> None:
    """Pin the four-face model contract before Astra replaces the raster package."""
    package_root = HANGBOARDS_ROOT / "owl-climb-poker"
    board_path = package_root / "board.json"
    board = json.loads(board_path.read_text(encoding="utf-8"))

    assert board["schemaVersion"] == 3
    assert board["id"] == "owl-climb.poker"
    assert board["equipmentObjects"] == [{"id": "primary"}]
    assert len(board["contacts"]) == 34
    contact_ids = [contact["id"] for contact in board["contacts"]]
    assert len(contact_ids) == len(set(contact_ids))
    assert {
        face: [contact_id for contact_id in contact_ids if contact_id.startswith(f"{face}-")]
        for face in ("face-a", "face-b", "face-c", "face-d")
    } == {
        "face-a": [
            "face-a-left-outer-slot",
            "face-a-left-single-pocket",
            "face-a-left-dual-pocket",
            "face-a-center-pull-up-slot",
            "face-a-right-dual-pocket",
            "face-a-right-single-pocket",
            "face-a-right-outer-slot",
        ],
        "face-b": [
            "face-b-left-outer-slot",
            "face-b-left-single-pocket",
            "face-b-left-dual-pocket",
            "face-b-left-deep-sloper",
            "face-b-center-pull-up-slot",
            "face-b-right-deep-sloper",
            "face-b-right-dual-pocket",
            "face-b-right-single-pocket",
            "face-b-right-outer-slot",
        ],
        "face-c": [
            "face-c-left-outer-slot",
            "face-c-left-single-pocket",
            "face-c-left-dual-pocket",
            "face-c-left-shallow-half-round",
            "face-c-center-pull-up-slot",
            "face-c-right-shallow-half-round",
            "face-c-right-dual-pocket",
            "face-c-right-single-pocket",
            "face-c-right-outer-slot",
        ],
        "face-d": [
            "face-d-left-outer-slot",
            "face-d-left-single-pocket",
            "face-d-left-dual-pocket",
            "face-d-left-deep-rounded-recess",
            "face-d-center-pull-up-slot",
            "face-d-right-deep-rounded-recess",
            "face-d-right-dual-pocket",
            "face-d-right-single-pocket",
            "face-d-right-outer-slot",
        ],
    }

    assert len(board["presentations"]) == 1
    presentation = board["presentations"][0]
    assert presentation["id"] == "primary"
    assert presentation["isDefault"] is True
    assert presentation["media"]["type"] == "model"
    assert set(presentation["media"]) == {
        "type", "assetPath", "descriptorPath", "display", "orientation"
    }
    assert presentation["media"]["assetPath"] == "assets/primary.usdz"
    assert presentation["media"]["descriptorPath"] == "assets/primary.model.json"
    assert "contactGeometry" not in json.dumps(board)
    assert not any(
        token in json.dumps(board).casefold()
        for token in ("suspension", "screw", "fastener", "bracket", "cleat", "hardware")
    )

    expected_positions = {
        face: [contact_id for contact_id in contact_ids if contact_id.startswith(f"{face}-")]
        for face in ("face-a", "face-b", "face-c", "face-d")
    }
    assert board["positions"] == [
        {"id": face, "presentationID": "primary", "contactIDs": expected_positions[face]}
        for face in ("face-a", "face-b", "face-c", "face-d")
    ]
    orientation = presentation["media"]["orientation"]
    assert orientation == {
        "pivot": "modelBoundsCenter",
        "rotations": {
            "face-a": [0, 0, 0, 1],
            "face-b": [0.707106781, 0, 0, 0.707106781],
            "face-c": [1, 0, 0, 0],
            "face-d": [-0.707106781, 0, 0, 0.707106781],
        },
    }

    model_files = {
        path.relative_to(package_root).as_posix()
        for path in package_root.rglob("*")
        if path.is_file()
    }
    assert model_files == {
        "board.json", "assets/primary.usdz", "assets/primary.model.json"
    }
    descriptor_path = package_root / presentation["media"]["descriptorPath"]
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    assert descriptor["schemaVersion"] == 1
    assert descriptor["modelSHA256"] == hashlib.sha256(
        (package_root / presentation["media"]["assetPath"]).read_bytes()
    ).hexdigest()
    assert set(descriptor["contacts"]) == set(contact_ids)
    assert not any(
        token in json.dumps(descriptor).casefold()
        for token in ("screw", "fastener", "bracket", "cleat", "hardware")
    )

    project = (REPOSITORY_ROOT / "HangTen.xcodeproj" / "project.pbxproj").read_text(
        encoding="utf-8"
    )
    assert "HangTenModelODR/owl-climb-poker/Hangboards" in project
    assert 'ASSET_TAGS = ("hang-ten-model-owl-climb-poker", );' in project


@pytest.mark.parametrize(
    ("board_id", "position_id"),
    [
        ("beastmaker-1000", "primary"),
        ("beastmaker-2000", "primary"),
        ("lattice-triple-rung", "primary"),
        ("metolius.prime-rib", "primary"),
        ("metolius.project", "primary"),
        ("metolius.wood-grips-compact-ii", "primary"),
        ("dewoodstok-woodbord", "primary"),
        ("escape.unlimited", "primary"),
        ("evolv-kilter-basic-long", "primary"),
        ("metolius.wood-grips-deluxe-ii", "front"),
        ("moon.armstrong", "primary"),
        ("target10a.linebreaker-base", "primary"),
    ],
)
def test_fixed_model_packages_keep_one_canonical_position_without_orientation(
    board_id: str, position_id: str,
) -> None:
    package = _discovered_model_packages()[board_id]
    board = package.board
    presentation = next(
        presentation
        for presentation in board.presentations
        if isinstance(presentation.media, BOARD_CATALOG.PresentationMediaModel)
    )
    assert presentation.id == position_id
    assert presentation.media.orientation is None
    assert presentation.media.suspension is None
    assert len(board.positions) == 1
    position = board.positions[0]
    assert position.id == position_id
    assert position.presentation_id == position_id
    assert position.contact_ids == tuple(hold.id for hold in board.contacts)


def test_nature_stone_hanger_declares_reviewed_front_and_reverse_orientation() -> None:
    board = _discovered_model_packages()["nature.stone-hanger"].board
    presentation = board.presentations[0]
    media = presentation.media
    assert isinstance(media, BOARD_CATALOG.PresentationMediaModel)

    # The review has established the two physical usable faces, but not a
    # final contact-to-face grouping. Keep this test intentionally agnostic to
    # that future Astra judgment while requiring a complete authored matrix.
    assert {position.id for position in board.positions} == {"front", "reverse"}
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_model_position_union_coverage(board)
    assert isinstance(media.suspension, BOARD_CATALOG.BoardModelPairedLeadCord)
    assert media.suspension.canonical_poses["front"].rotation == (0, 0, 0, 1)
    assert media.suspension.canonical_poses["reverse"].rotation == (0, 1, 0, 0)


def test_baguette_evo_requires_authored_contact_groupings_and_orientation() -> None:
    board = _discovered_model_packages()["yy.baguette-evo"].board
    presentation = board.presentations[0]
    media = presentation.media
    assert isinstance(media, BOARD_CATALOG.PresentationMediaModel)

    # Do not encode guessed IDs, grouping, or angles here. The reviewed
    # grouping is deliberately supplied by the later evidence/Astra pass; this
    # RED contract only requires every reviewed grouping to be explicit and to
    # cover the descriptor inventory (union coverage).
    assert len(board.positions) > 1
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_model_position_union_coverage(board)
    assert media.orientation is not None
    assert media.orientation.pivot == "modelBoundsCenter"
    assert set(media.orientation.rotations) == {
        position.id for position in board.positions
    }


def test_flash_board_allows_upright_inverted_overlap() -> None:
    board = _discovered_model_packages()["tension.flash-board"].board
    presentation = board.presentations[0]
    media = presentation.media
    assert isinstance(media, BOARD_CATALOG.PresentationMediaModel)

    # Flash board has 4 positions with upright/inverted pairs sharing holds
    expected_positions = {
        "three-edge-upright",
        "three-edge-inverted",
        "two-edge-upright",
        "two-edge-inverted",
    }
    assert {position.id for position in board.positions} == expected_positions
    assert all(position.presentation_id == "primary" for position in board.positions)
    _assert_model_position_union_coverage(board)

    # Verify overlap: three-edge holds appear in both upright and inverted
    three_edge_upright = next(p for p in board.positions if p.id == "three-edge-upright")
    three_edge_inverted = next(p for p in board.positions if p.id == "three-edge-inverted")
    assert three_edge_upright.contact_ids == three_edge_inverted.contact_ids
    assert set(three_edge_upright.contact_ids) == {"three-edge-left", "three-edge-center", "three-edge-right"}

    # Two-edge holds appear in both upright and inverted
    two_edge_upright = next(p for p in board.positions if p.id == "two-edge-upright")
    two_edge_inverted = next(p for p in board.positions if p.id == "two-edge-inverted")
    assert two_edge_upright.contact_ids == two_edge_inverted.contact_ids
    assert set(two_edge_upright.contact_ids) == {
        "two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"
    }

    # Suspension metadata covers each corrected position.
    assert media.orientation is None
    assert media.suspension is not None
    assert set(media.suspension.canonical_poses) == expected_positions


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
