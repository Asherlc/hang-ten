from __future__ import annotations

from collections import Counter
import hashlib
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

ORIENTATION_PRESENTATION_EXPECTATIONS = {
    "trango-rock-prodigy-pivot-orientation-1": (
        (650, 264),
        "9c4e31db309ffe8a554695038e463402fdc1bd6b29a4a0a380288d678a56ae61",
    ),
    "trango-rock-prodigy-pivot-orientation-2-90-outwards": (
        (308, 327),
        "39c04d89e09fba49bcbee0803c40fdf7e843cfffeafc5ae175cf17b38f992ff9",
    ),
    "trango-rock-prodigy-pivot-orientation-3-90-inwards": (
        (650, 254),
        "305a86c175d74b34877378511d3a062e9b3d253cdad44644f2e6be6bc401a6ee",
    ),
    "trango-rock-prodigy-pivot-orientation-3-switch-left-to-right": (
        (650, 251),
        "1f4d4f019df7acf52b89ce18c0af4bd60c8ac1de0df58bccb31f0855d15e8a38",
    ),
    "trango-rock-prodigy-pivot-orientation-4-90-outwards": (
        (308, 326),
        "55cefe136fe40bf3ad06b792bbd765743e0d3da93a0732a32a11beee80fbb428",
    ),
}

# Literal operator-reviewed normalized bounds on the official Quick Start
# orientation summary panels. A tuple contains one frame per visible contact
# surface; Orientation 1's combined jug/pinch and Orientation 4's compression
# pinch each have a second thumb-contact surface.
ORIENTATION_GEOMETRY_FRAMES = {
    "trango-rock-prodigy-pivot-orientation-1": {
        "jug-horizontal-pinch-left": ((0.107692, 0.257576, 0.169231, 0.356061), (0.223077, 0.590909, 0.075385, 0.159091)),
        "jug-horizontal-pinch-right": ((0.723077, 0.257576, 0.169231, 0.356061), (0.701538, 0.590909, 0.075385, 0.159091)),
        "variable-depth-sloper-rail-left": ((0.173846, 0.556818, 0.298462, 0.147727),),
        "variable-depth-sloper-rail-right": ((0.527692, 0.556818, 0.298462, 0.147727),),
        "medium-supported-crimp-left": ((0.278462, 0.424242, 0.186154, 0.090909),),
        "medium-supported-crimp-right": ((0.535384, 0.424242, 0.186154, 0.090909),),
        "large-sloped-crimp-left": ((0.321538, 0.246212, 0.147692, 0.098485),),
        "large-sloped-crimp-right": ((0.53077, 0.246212, 0.147692, 0.098485),),
    },
    "trango-rock-prodigy-pivot-orientation-2-90-outwards": {
        "shallow-mono-left": ((0.337662, 0.204893, 0.087662, 0.449541),),
        "shallow-mono-right": ((0.574676, 0.204893, 0.087662, 0.449541),),
        "steep-gaston-left": ((0.233766, 0.412844, 0.224026, 0.299694),),
        "steep-gaston-right": ((0.542208, 0.412844, 0.224026, 0.299694),),
        "small-sloped-crimp-left": ((0.152597, 0.174312, 0.275974, 0.082569),),
        "small-sloped-crimp-right": ((0.571429, 0.174312, 0.275974, 0.082569),),
    },
    "trango-rock-prodigy-pivot-orientation-3-90-inwards": {
        "two-finger-pocket-left": ((0.170769, 0.543307, 0.058462, 0.110236),),
        "two-finger-pocket-right": ((0.770769, 0.543307, 0.058462, 0.110236),),
        "three-finger-pocket-left": ((0.236923, 0.551181, 0.046154, 0.098425),),
        "three-finger-pocket-right": ((0.716923, 0.551181, 0.046154, 0.098425),),
        "large-supported-crimp-left": ((0.223077, 0.559055, 0.123077, 0.11811),),
        "large-supported-crimp-right": ((0.653846, 0.559055, 0.123077, 0.11811),),
        "sloper-left": ((0.230769, 0.228346, 0.130769, 0.094488),),
        "sloper-right": ((0.638462, 0.228346, 0.130769, 0.094488),),
    },
    "trango-rock-prodigy-pivot-orientation-3-switch-left-to-right": {
        "variable-depth-incut-rail-left": ((0.207692, 0.294821, 0.272308, 0.14741),),
        "variable-depth-incut-rail-right": ((0.52, 0.294821, 0.272308, 0.14741),),
        "shallow-gaston-left": ((0.138462, 0.36255, 0.116923, 0.286853),),
        "shallow-gaston-right": ((0.744615, 0.36255, 0.116923, 0.286853),),
    },
    "trango-rock-prodigy-pivot-orientation-4-90-outwards": {
        "compression-pinch-left": ((0.165584, 0.196319, 0.185065, 0.266871), (0.376623, 0.41411, 0.074675, 0.144172)),
        "compression-pinch-right": ((0.649351, 0.196319, 0.185065, 0.266871), (0.548702, 0.41411, 0.074675, 0.144172)),
        "deep-mono-left": ((0.344156, 0.294479, 0.084416, 0.435583),),
        "deep-mono-right": ((0.571428, 0.294479, 0.084416, 0.435583),),
        "medium-mono-left": ((0.12987, 0.552147, 0.087662, 0.162577),),
        "medium-mono-right": ((0.782468, 0.552147, 0.087662, 0.162577),),
    },
}

# Each digest is computed from the literal authored path-command objects using
# canonical JSON (sorted keys and compact separators).  This pins the contour
# within its reviewed frame, so a replacement path with identical bounds fails.
ORIENTATION_PATH_COMMAND_SHA256 = {
    "trango-rock-prodigy-pivot-orientation-1": {
        "jug-horizontal-pinch-left": ("cdd15a9dc551e45b0bea26325fba9dcc5982685d1cd350102836552cb8e5f56d", "cee171ee032ee2d8c59c6b632365d156c46ca0aba1b35aeedcdc18a58759cf65"),
        "jug-horizontal-pinch-right": ("0804e1e9ab8f6c3e5e85517e0ccb8deeb9a7d23c521bf57c665e91a2763ce7f8", "7c04c53bbdc844d45e7599de53c361cafb1aba125dea9345cf50cdcf7d78be38"),
        "variable-depth-sloper-rail-left": ("d02f7c02f09cf698be213374e4d01857822e5ae13e1c72f7923f83882c713911",),
        "variable-depth-sloper-rail-right": ("5fafbcc227f0f41b219937f2933396fab4afa67ba26078830d94de38814dc161",),
        "medium-supported-crimp-left": ("89f8798e399f0669f2cbf3c1af47501325f055b84a2732d52512cfc179f90219",),
        "medium-supported-crimp-right": ("c9cb219036edb61691bee440c27dccc6ac14cb653dc73c0833c29c0046616d84",),
        "large-sloped-crimp-left": ("3143b585af8a0428e60ae0468bc468783fed7f46c53b95eafef0fc71997496c8",),
        "large-sloped-crimp-right": ("1b1a4db9f2b4dd0588bbce602a7b1c982c963e04d196e8017e1e89b788e7fa81",),
    },
    "trango-rock-prodigy-pivot-orientation-2-90-outwards": {
        "shallow-mono-left": ("0e60a96fbd9a1048f8b20b6da5bbe4909ec78c40a335a6c77c00860e78839c47",),
        "shallow-mono-right": ("a9ca488134e5d4b847aa80719e51f05e2e577687cf42104db1b31bb12fba923d",),
        "steep-gaston-left": ("5657760072dae8e23943a8e6d464393996b949918cd86985b95291f852492926",),
        "steep-gaston-right": ("5c18c2920a58bbec2905002aa244141d65e64155ead580f55ecc4de3e5905e72",),
        "small-sloped-crimp-left": ("e0e41816ca8b11b7738eca05954e20188c22eb3db375f2eadf3eb5354b5019b4",),
        "small-sloped-crimp-right": ("663f7c029d01f47e1b5c3092a934677e5b1bf68a8677bba7bdbfa7505549d98d",),
    },
    "trango-rock-prodigy-pivot-orientation-3-90-inwards": {
        "two-finger-pocket-left": ("3deb931662761ceec0541ed60b836531c2bd2ca4327c9dc7448b9dda4e5ab261",),
        "two-finger-pocket-right": ("90b32755205b0ba83478d62b1034163e31bd42ecb39f2b7c95a0c561c3af31d2",),
        "three-finger-pocket-left": ("a6b166bc9c9d6b7d8c7e422c149991b15a1e3aafe034f65df4805515b9cdc71b",),
        "three-finger-pocket-right": ("05d3b4ed3eef536e4eee1728ab188f640e90073a270d357a7d9d9e91b1cd3d8f",),
        "large-supported-crimp-left": ("4f15448e779052fff53078e9d4c3cea083aed6d1abd44f198f74a9ad65c865d6",),
        "large-supported-crimp-right": ("d31fdbe3fbcafa0acf5dbc4436441f347fc75b55bb92f8b3105dcc47a94a6229",),
        "sloper-left": ("825007e3c87d0e20ed81a4ccff0d50fce021494267ff124be0cdc60862e9fc18",),
        "sloper-right": ("0179f1125f8c63949c182d31e07ec177e2c00116c73ed4c03cf9b84d61f5b340",),
    },
    "trango-rock-prodigy-pivot-orientation-3-switch-left-to-right": {
        "variable-depth-incut-rail-left": ("5d044c5f6fb673ab479319b4bb3abec0b19798181ecb11e9b07241fa72150453",),
        "variable-depth-incut-rail-right": ("0b702680316b121d3efb33702799b96a411c0eedf128668e396c0d5b6894af32",),
        "shallow-gaston-left": ("0edd458c8f67109f20bdf83f1154da604fa440bf3ce1f19c1b632de0dcbd97c6",),
        "shallow-gaston-right": ("6666da2b7336879276f0e0727ae68a6b9da6d304f9ab8c751c46f2ee7093dde7",),
    },
    "trango-rock-prodigy-pivot-orientation-4-90-outwards": {
        "compression-pinch-left": ("238f58f3b0d3ccd0f99df1f101ab1f7eb79d6865483ca515704a223993555666", "0dbfa7b238c6fdb5e319be91a3a7015c4bf29c3b5431006c45daae32b6ee447a"),
        "compression-pinch-right": ("757eeb0f648431aeb6a1150c3a41643f6133cf78c444c021ff67c8c8f5483cd2", "b34b8ca4bfec6444f121df4ce8b9d2d1b5d276623ca1f2d939a501848bc5b745"),
        "deep-mono-left": ("3f6d11f246d63159655d2d69179d16848960ef6c4ff87d7d0c1bc56e6902b7e4",),
        "deep-mono-right": ("4b5f433ec665a36119049417d14a4fb279dbaca0ae0dfb479610db34fab0d86f",),
        "medium-mono-left": ("a6b166bc9c9d6b7d8c7e422c149991b15a1e3aafe034f65df4805515b9cdc71b",),
        "medium-mono-right": ("05d3b4ed3eef536e4eee1728ab188f640e90073a270d357a7d9d9e91b1cd3d8f",),
    },
}


def _command_points(command: dict[str, object]) -> tuple[tuple[float, float], ...]:
    return tuple(
        tuple(point)
        for key in ("to", "control", "control1", "control2")
        if (point := command.get(key)) is not None
    )


def _path_command_sha256(commands: list[dict[str, object]]) -> str:
    return hashlib.sha256(
        json.dumps(commands, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


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
        expected_pixel_size, expected_sha256 = ORIENTATION_PRESENTATION_EXPECTATIONS[slug]
        asset_path = package_root / "assets" / "primary.png"
        assert board_package._png_dimensions(asset_path) == expected_pixel_size
        assert hashlib.sha256(asset_path.read_bytes()).hexdigest() == expected_sha256
        assert hashlib.sha256(asset_path.read_bytes()).hexdigest() != hashlib.sha256(
            (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
        ).hexdigest()
        assert board["aspectRatio"] == pytest.approx(
            expected_pixel_size[0] / expected_pixel_size[1]
        )
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


def test_orientation_packages_use_source_specific_operator_reviewed_geometry() -> None:
    actual_slugs = {
        path.parent.name
        for path in (REPOSITORY_ROOT / "Hangboards").glob(
            "trango-rock-prodigy-pivot-orientation-*/board.json"
        )
    }
    assert actual_slugs == set(ORIENTATION_PACKAGES)

    for slug, expected_frames in ORIENTATION_GEOMETRY_FRAMES.items():
        board = board_package.load_board_package(
            REPOSITORY_ROOT / "Hangboards" / slug
        ).board
        holds = {hold["id"]: hold for hold in board["holds"]}

        assert set(holds) == set(expected_frames)
        for hold_id, literal_frames in expected_frames.items():
            actual_frames = tuple(
                (
                    piece["frame"]["x"],
                    piece["frame"]["y"],
                    piece["frame"]["width"],
                    piece["frame"]["height"],
                )
                for piece in holds[hold_id]["geometry"]
            )
            assert len(actual_frames) == len(literal_frames)
            for actual_frame, literal_frame in zip(
                actual_frames, literal_frames, strict=True
            ):
                assert actual_frame == pytest.approx(literal_frame, abs=5e-7)

        base_geometries = {
            json.dumps(hold["geometry"], sort_keys=True)
            for hold in board_package.load_board_package(PACKAGE_ROOT).board["holds"]
        }
        assert all(
            json.dumps(hold["geometry"], sort_keys=True) not in base_geometries
            for hold in holds.values()
        )


def test_orientation_paths_match_operator_reviewed_command_signatures() -> None:
    """Replacing a reviewed contour inside its existing frame is a geometry bug."""
    for slug in ORIENTATION_PACKAGES:
        board = board_package.load_board_package(
            REPOSITORY_ROOT / "Hangboards" / slug
        ).board
        actual_hold_signatures = {
            hold["id"]: tuple(
                _path_command_sha256(piece["shape"]["commands"])
                for piece in hold["geometry"]
            )
            for hold in board["holds"]
        }
        assert actual_hold_signatures == ORIENTATION_PATH_COMMAND_SHA256.get(slug, {})


def test_orientation_left_and_right_contacts_are_exact_mirrors() -> None:
    for slug, expected_frames in ORIENTATION_GEOMETRY_FRAMES.items():
        board = board_package.load_board_package(
            REPOSITORY_ROOT / "Hangboards" / slug
        ).board
        holds = {hold["id"]: hold for hold in board["holds"]}

        for left_id in (hold_id for hold_id in expected_frames if hold_id.endswith("-left")):
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
