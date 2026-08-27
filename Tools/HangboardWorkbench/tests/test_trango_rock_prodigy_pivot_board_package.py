from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_geometry  # noqa: E402
import board_package  # noqa: E402


EXPECTED_HOLDS = (
    (
        "upper-sloped-crimp-left",
        "edge",
        {"sizeMillimeters": 12.5, "fingerCapacity": 4},
    ),
    (
        "upper-sloped-crimp-right",
        "edge",
        {"sizeMillimeters": 12.5, "fingerCapacity": 4},
    ),
    (
        "outer-sloped-crimp-left",
        "edge",
        {"sizeMillimeters": 11.5, "fingerCapacity": 4},
    ),
    (
        "outer-sloped-crimp-right",
        "edge",
        {"sizeMillimeters": 11.5, "fingerCapacity": 4},
    ),
    (
        "variable-edge-left",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 16, "upperBound": 31},
            "fingerCapacity": 4,
        },
    ),
    (
        "variable-edge-right",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 16, "upperBound": 31},
            "fingerCapacity": 4,
        },
    ),
    (
        "medium-crimp-left",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 9, "upperBound": 10},
            "fingerCapacity": 4,
        },
    ),
    (
        "medium-crimp-right",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 9, "upperBound": 10},
            "fingerCapacity": 4,
        },
    ),
    (
        "large-crimp-left",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 11, "upperBound": 12},
            "fingerCapacity": 4,
        },
    ),
    (
        "large-crimp-right",
        "edge",
        {
            "depthRangeMillimeters": {"lowerBound": 11, "upperBound": 12},
            "fingerCapacity": 4,
        },
    ),
    (
        "two-finger-pocket-left",
        "pocket",
        {
            "depthRangeMillimeters": {"lowerBound": 28, "upperBound": 32},
            "fingerCapacity": 2,
            "gripType": "twoFingerPocket",
        },
    ),
    (
        "two-finger-pocket-right",
        "pocket",
        {
            "depthRangeMillimeters": {"lowerBound": 28, "upperBound": 32},
            "fingerCapacity": 2,
            "gripType": "twoFingerPocket",
        },
    ),
    (
        "three-finger-pocket-left",
        "pocket",
        {
            "depthRangeMillimeters": {"lowerBound": 17, "upperBound": 28},
            "fingerCapacity": 3,
            "gripType": "threeFingerPocket",
        },
    ),
    (
        "three-finger-pocket-right",
        "pocket",
        {
            "depthRangeMillimeters": {"lowerBound": 17, "upperBound": 28},
            "fingerCapacity": 3,
            "gripType": "threeFingerPocket",
        },
    ),
    ("outer-wedge-pinch-left", "pinch", {"fingerCapacity": 4}),
    ("outer-wedge-pinch-right", "pinch", {"fingerCapacity": 4}),
    (
        "lower-sloper-left",
        "sloper",
        {"fingerCapacity": 4, "gripType": "sloper"},
    ),
    (
        "lower-sloper-right",
        "sloper",
        {"fingerCapacity": 4, "gripType": "sloper"},
    ),
)
OPTIONAL_HOLD_METADATA_FIELDS = (
    "sizeMillimeters",
    "depthRangeMillimeters",
    "fingerCapacity",
    "handCapacity",
    "gripType",
    "features",
)
ALLOWED_KINDS = frozenset({"jug", "edge", "pocket", "pinch", "sloper"})
EXPECTED_KIND_COUNTS = Counter({"edge": 10, "pocket": 4, "pinch": 2, "sloper": 2})
EXPECTED_PIECE_COUNT = 22
EXPECTED_PIXEL_SIZE = (1774, 887)
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)
FORBIDDEN_RAW_KEYS = frozenset(
    {"cueStyle", "semantics", "evidence", "artwork", "catalog", "claims", "ui"}
)
ORIENTATION_PACKAGES = {
    "trango-rock-prodigy-pivot-orientation-1": (
        "trango.rock-prodigy-pivot.orientation-1",
        "Rock Prodigy Pivot — Orientation 1",
        (
            ("jug-horizontal-pinch-left", "Left Jug / Horizontal Pinch", "jug"),
            ("jug-horizontal-pinch-right", "Right Jug / Horizontal Pinch", "jug"),
            ("variable-depth-sloper-rail-left", "Left Variable Depth Sloper Rail", "sloper"),
            ("variable-depth-sloper-rail-right", "Right Variable Depth Sloper Rail", "sloper"),
            ("medium-supported-crimp-left", "Left Medium Supported Crimp", "edge"),
            ("medium-supported-crimp-right", "Right Medium Supported Crimp", "edge"),
            ("large-sloped-crimp-left", "Left Large Sloped Crimp", "edge"),
            ("large-sloped-crimp-right", "Right Large Sloped Crimp", "edge"),
        ),
    ),
    "trango-rock-prodigy-pivot-orientation-2-90-outwards": (
        "trango.rock-prodigy-pivot.orientation-2-90-outwards",
        "Rock Prodigy Pivot — Orientation 2 (90° Outwards)",
        (
            ("shallow-mono-left", "Left Shallow Mono", "pocket"),
            ("shallow-mono-right", "Right Shallow Mono", "pocket"),
            ("steep-gaston-left", "Left Steep Gaston", "edge"),
            ("steep-gaston-right", "Right Steep Gaston", "edge"),
            ("small-sloped-crimp-left", "Left Small Sloped Crimp", "edge"),
            ("small-sloped-crimp-right", "Right Small Sloped Crimp", "edge"),
        ),
    ),
    "trango-rock-prodigy-pivot-orientation-3-90-inwards": (
        "trango.rock-prodigy-pivot.orientation-3-90-inwards",
        "Rock Prodigy Pivot — Orientation 3 (90° Inwards)",
        (
            ("two-finger-pocket-left", "Left 2 Finger Pocket", "pocket"),
            ("two-finger-pocket-right", "Right 2 Finger Pocket", "pocket"),
            ("three-finger-pocket-left", "Left 3 Finger Pocket", "pocket"),
            ("three-finger-pocket-right", "Right 3 Finger Pocket", "pocket"),
            ("large-supported-crimp-left", "Left Large Supported Crimp", "edge"),
            ("large-supported-crimp-right", "Right Large Supported Crimp", "edge"),
            ("sloper-left", "Left Sloper", "sloper"),
            ("sloper-right", "Right Sloper", "sloper"),
        ),
    ),
    "trango-rock-prodigy-pivot-orientation-3-switch-left-to-right": (
        "trango.rock-prodigy-pivot.orientation-3-switch-left-to-right",
        "Rock Prodigy Pivot — Orientation 3 Switch (L-to-R)",
        (
            ("variable-depth-incut-rail-left", "Left Variable Depth Incut Rail", "edge"),
            ("variable-depth-incut-rail-right", "Right Variable Depth Incut Rail", "edge"),
            ("shallow-gaston-left", "Left Shallow Gaston", "edge"),
            ("shallow-gaston-right", "Right Shallow Gaston", "edge"),
        ),
    ),
    "trango-rock-prodigy-pivot-orientation-4-90-outwards": (
        "trango.rock-prodigy-pivot.orientation-4-90-outwards",
        "Rock Prodigy Pivot — Orientation 4 (90° Outwards)",
        (
            ("compression-pinch-left", "Left Compression Pinch", "pinch"),
            ("compression-pinch-right", "Right Compression Pinch", "pinch"),
            ("deep-mono-left", "Left Deep Mono", "pocket"),
            ("deep-mono-right", "Right Deep Mono", "pocket"),
            ("medium-mono-left", "Left Medium Mono", "pocket"),
            ("medium-mono-right", "Right Medium Mono", "pocket"),
        ),
    ),
}

# Each orientation record reuses exactly one complete, already-reviewed
# physical contact from the base package. The two official Orientation 1 usage
# names share one wedge contact per side, so each side has one combined record.
ORIENTATION_CANONICAL_CONTACTS = {
    "trango-rock-prodigy-pivot-orientation-1": {
        "jug-horizontal-pinch-left": "outer-wedge-pinch-left",
        "jug-horizontal-pinch-right": "outer-wedge-pinch-right",
        "variable-depth-sloper-rail-left": "variable-edge-left",
        "variable-depth-sloper-rail-right": "variable-edge-right",
        "medium-supported-crimp-left": "medium-crimp-left",
        "medium-supported-crimp-right": "medium-crimp-right",
        "large-sloped-crimp-left": "upper-sloped-crimp-left",
        "large-sloped-crimp-right": "upper-sloped-crimp-right",
    },
    "trango-rock-prodigy-pivot-orientation-2-90-outwards": {
        "shallow-mono-left": "variable-edge-left",
        "shallow-mono-right": "variable-edge-right",
        "steep-gaston-left": "outer-wedge-pinch-left",
        "steep-gaston-right": "outer-wedge-pinch-right",
        "small-sloped-crimp-left": "outer-sloped-crimp-left",
        "small-sloped-crimp-right": "outer-sloped-crimp-right",
    },
    "trango-rock-prodigy-pivot-orientation-3-90-inwards": {
        "two-finger-pocket-left": "two-finger-pocket-left",
        "two-finger-pocket-right": "two-finger-pocket-right",
        "three-finger-pocket-left": "three-finger-pocket-left",
        "three-finger-pocket-right": "three-finger-pocket-right",
        "large-supported-crimp-left": "medium-crimp-left",
        "large-supported-crimp-right": "medium-crimp-right",
        "sloper-left": "lower-sloper-left",
        "sloper-right": "lower-sloper-right",
    },
    "trango-rock-prodigy-pivot-orientation-3-switch-left-to-right": {
        "variable-depth-incut-rail-left": "variable-edge-left",
        "variable-depth-incut-rail-right": "variable-edge-right",
        "shallow-gaston-left": "outer-wedge-pinch-left",
        "shallow-gaston-right": "outer-wedge-pinch-right",
    },
    "trango-rock-prodigy-pivot-orientation-4-90-outwards": {
        "compression-pinch-left": "outer-wedge-pinch-left",
        "compression-pinch-right": "outer-wedge-pinch-right",
        "deep-mono-left": "variable-edge-left",
        "deep-mono-right": "variable-edge-right",
        "medium-mono-left": "three-finger-pocket-left",
        "medium-mono-right": "three-finger-pocket-right",
    },
}


def _command_points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_all_keys(child) for child in value))
    return set()


@pytest.fixture(scope="module")
def package() -> board_package.BoardPackage:
    return board_package.load_board_package(PACKAGE_ROOT)


@pytest.fixture(scope="module")
def pixel_size() -> tuple[int, int]:
    return board_package._png_dimensions(PACKAGE_ROOT / "assets" / "primary.png")


def test_package_contents_and_metadata(package: board_package.BoardPackage, pixel_size: tuple[int, int]) -> None:
    board = package.board
    width, height = pixel_size

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {"primary.png"}
    assert board["id"] == "trango.rock-prodigy-pivot"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Pivot"
    assert board["dimensions"] == "15.5 × 5 × 2.5 in"
    assert board["presentations"] == [
        {
            "id": "primary",
            "name": "Primary",
            "assetPath": "assets/primary.png",
            "aspectRatio": width / height,
            "default": True,
        }
    ]
    assert all(hold["presentationID"] == "primary" for hold in board["holds"])
    assert (width, height) == EXPECTED_PIXEL_SIZE
    assert board["aspectRatio"] == width / height


def test_hold_inventory_kinds_and_source_audited_metadata(
    package: board_package.BoardPackage,
) -> None:
    board = package.board

    assert board_package._HOLD_KINDS == ALLOWED_KINDS
    assert all(hold["kind"] in ALLOWED_KINDS for hold in board["holds"])
    assert Counter(hold["kind"] for hold in board["holds"]) == EXPECTED_KIND_COUNTS

    actual_holds = tuple(
        (
            hold["id"],
            hold["kind"],
            {
                field: hold[field]
                for field in OPTIONAL_HOLD_METADATA_FIELDS
                if field in hold
            },
        )
        for hold in board["holds"]
    )
    assert actual_holds == EXPECTED_HOLDS
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == EXPECTED_PIECE_COUNT
    assert {
        hold["id"]: len(hold["geometry"])
        for hold in board["holds"]
        if len(hold["geometry"]) != 1
    } == {
        "outer-wedge-pinch-left": 2,
        "outer-wedge-pinch-right": 2,
        "lower-sloper-left": 2,
        "lower-sloper-right": 2,
    }


def test_piece_geometry_fills_declared_frames(
    package: board_package.BoardPackage, pixel_size: tuple[int, int]
) -> None:
    width, height = pixel_size
    for hold in package.board["holds"]:
        for piece_index, piece in enumerate(hold["geometry"]):
            label = f"{hold['id']}.geometry[{piece_index}]"
            shape = piece["shape"]
            assert shape["type"] == "path"
            commands = shape["commands"]
            assert commands[0]["command"] == "move"
            assert commands[-1] == {"command": "close"}
            assert len(commands[1:-1]) >= 4
            assert {command["command"] for command in commands[1:-1]} == {"curve"}
            min_x, max_x, min_y, max_y = board_geometry.flattened_shape_bounds(commands)
            assert min_x == pytest.approx(0, abs=5e-7)
            assert min_y == pytest.approx(0, abs=5e-7)
            assert max_x == pytest.approx(1, abs=5e-7)
            assert max_y == pytest.approx(1, abs=5e-7)
            path = board_geometry.display_path_for_shape(
                piece["frame"], piece["shape"], width, height, label=label
            )
            assert path.commands[0][0] == "M"
            assert path.commands[-1][0] == "Z"
            assert path.data.endswith(" Z")


def test_left_and_right_geometry_are_mirrored(package: board_package.BoardPackage) -> None:
    holds = {hold["id"]: hold for hold in package.board["holds"]}
    for left_id, right_id in MIRRORED_PAIRS:
        left_geometry = holds[left_id]["geometry"]
        right_geometry = holds[right_id]["geometry"]
        assert len(right_geometry) == len(left_geometry)
        for left, right in zip(left_geometry, right_geometry, strict=True):
            left_frame = left["frame"]
            right_frame = right["frame"]
            assert right_frame["x"] == pytest.approx(
                1 - left_frame["x"] - left_frame["width"], abs=1e-12
            )
            assert right_frame["y"] == left_frame["y"]
            assert right_frame["width"] == left_frame["width"]
            assert right_frame["height"] == left_frame["height"]
            assert right.get("treatment") == left.get("treatment")
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _command_points(left_command),
                    _command_points(right_command),
                    strict=True,
                ):
                    assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                    assert right_y == pytest.approx(left_y, abs=1e-12)


def test_board_document_omits_forbidden_keys() -> None:
    raw = json.loads((PACKAGE_ROOT / "board.json").read_text(encoding="utf-8"))
    assert FORBIDDEN_RAW_KEYS.isdisjoint(_all_keys(raw))


def test_documented_orientation_packages_have_exact_manual_hold_inventories() -> None:
    """A missing documented orientation package or manual grip position is a catalog bug."""
    for slug, (board_id, name, expected_holds) in ORIENTATION_PACKAGES.items():
        package_root = REPOSITORY_ROOT / "Hangboards" / slug
        package = board_package.load_board_package(package_root)
        board = package.board

        assert {path.name for path in package_root.iterdir()} == {"assets", "board.json"}
        assert {path.name for path in (package_root / "assets").iterdir()} == {"primary.png"}
        assert board["id"] == board_id
        assert board["manufacturer"] == "Trango"
        assert board["name"] == name
        assert "dimensions" not in board
        assert board["aspectRatio"] == 2.0
        assert board_package._png_dimensions(package_root / "assets" / "primary.png") == (1774, 887)
        assert board["presentations"] == [
            {
                "id": "primary",
                "name": "Primary",
                "assetPath": "assets/primary.png",
                "aspectRatio": board["aspectRatio"],
                "default": True,
            }
        ]
        assert tuple((hold["id"], hold["name"], hold["kind"]) for hold in board["holds"]) == expected_holds
        assert all(hold["geometry"] for hold in board["holds"])
        assert all(hold["presentationID"] == "primary" for hold in board["holds"])
        assert all(
            set(hold).isdisjoint(OPTIONAL_HOLD_METADATA_FIELDS)
            for hold in board["holds"]
        )
        assert FORBIDDEN_RAW_KEYS.isdisjoint(_all_keys(board))


def test_orientation_packages_keep_documented_physical_contacts_separate_and_exact() -> None:
    base_board = board_package.load_board_package(PACKAGE_ROOT).board
    canonical_geometry = {
        hold["id"]: hold["geometry"]
        for hold in base_board["holds"]
    }

    actual_slugs = {
        path.parent.name
        for path in (REPOSITORY_ROOT / "Hangboards").glob(
            "trango-rock-prodigy-pivot-orientation-*/board.json"
        )
    }
    assert actual_slugs == set(ORIENTATION_PACKAGES)

    for slug, expected_contacts in ORIENTATION_CANONICAL_CONTACTS.items():
        board = board_package.load_board_package(
            REPOSITORY_ROOT / "Hangboards" / slug
        ).board
        holds = {hold["id"]: hold for hold in board["holds"]}

        assert set(holds) == set(expected_contacts)
        mapped_contacts = tuple(expected_contacts.values())
        assert len(mapped_contacts) == len(set(mapped_contacts))
        for hold_id, contact_id in expected_contacts.items():
            assert holds[hold_id]["geometry"] == canonical_geometry[contact_id]


def test_orientation_left_and_right_contacts_are_exact_mirrors() -> None:
    for slug, expected_contacts in ORIENTATION_CANONICAL_CONTACTS.items():
        board = board_package.load_board_package(
            REPOSITORY_ROOT / "Hangboards" / slug
        ).board
        holds = {hold["id"]: hold for hold in board["holds"]}

        for left_id in (hold_id for hold_id in expected_contacts if hold_id.endswith("-left")):
            right_id = f"{left_id.removesuffix('-left')}-right"
            left_geometry = holds[left_id]["geometry"]
            right_geometry = holds[right_id]["geometry"]
            assert len(right_geometry) == len(left_geometry)
            for left, right in zip(left_geometry, right_geometry, strict=True):
                left_frame = left["frame"]
                right_frame = right["frame"]
                assert right_frame["x"] == pytest.approx(
                    1 - left_frame["x"] - left_frame["width"], abs=1e-12
                )
                assert right_frame["y"] == left_frame["y"]
                assert right_frame["width"] == left_frame["width"]
                assert right_frame["height"] == left_frame["height"]
                assert right.get("treatment") == left.get("treatment")
                for left_command, right_command in zip(
                    left["shape"]["commands"],
                    right["shape"]["commands"],
                    strict=True,
                ):
                    assert left_command["command"] == right_command["command"]
                    for (left_x, left_y), (right_x, right_y) in zip(
                        _command_points(left_command),
                        _command_points(right_command),
                        strict=True,
                    ):
                        assert right_x == pytest.approx(1 - left_x, abs=1e-12)
                        assert right_y == pytest.approx(left_y, abs=1e-12)
