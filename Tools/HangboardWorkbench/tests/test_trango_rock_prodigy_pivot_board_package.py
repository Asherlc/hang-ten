from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest
from PIL import Image

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "Hangboards" / "trango-rock-prodigy-pivot"
sys.path.insert(0, str(WORKBENCH_ROOT))

import board_geometry
import board_package

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
EXPECTED_PRESENTATIONS = (
    ("orientation-1", "Orientation 1", "assets/primary.png", True),
    ("orientation-2", "Orientation 2", "assets/orientation-2.png", False),
    ("orientation-3", "Orientation 3", "assets/orientation-3.png", False),
    ("orientation-4", "Orientation 4", "assets/orientation-4.png", False),
)
EXPECTED_SECONDARY_HALF_TRANSFORMS = {
    "orientation-2": (
        ("left", "left", Image.Transpose.ROTATE_90),
        ("right", "right", Image.Transpose.ROTATE_270),
    ),
    "orientation-3": (
        ("left", "left", Image.Transpose.ROTATE_180),
        ("right", "right", Image.Transpose.ROTATE_180),
    ),
    # The guide's Orientation 3 switch moves the complete right half to the
    # left and the complete left half to the right before the outward pivots.
    "orientation-4": (
        ("right", "left", Image.Transpose.ROTATE_90),
        ("left", "right", Image.Transpose.ROTATE_270),
    ),
}
MIRRORED_PAIRS = tuple(
    (EXPECTED_HOLDS[index][0], EXPECTED_HOLDS[index + 1][0])
    for index in range(0, len(EXPECTED_HOLDS), 2)
)
FORBIDDEN_RAW_KEYS = frozenset(
    {"cueStyle", "semantics", "evidence", "artwork", "catalog", "claims", "ui"}
)


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


def _hold_id(base_id: str, presentation_id: str) -> str:
    return (
        base_id
        if presentation_id == "orientation-1"
        else f"{base_id}-{presentation_id}"
    )


def _half_box(side: str) -> tuple[int, int, int, int]:
    left = 0 if side == "left" else EXPECTED_PIXEL_SIZE[0] // 2
    return left, 0, left + EXPECTED_PIXEL_SIZE[0] // 2, EXPECTED_PIXEL_SIZE[1]


def _opposite_side_hold_id(hold_id: str) -> str:
    if hold_id.endswith("-left"):
        return f"{hold_id.removesuffix('-left')}-right"
    return f"{hold_id.removesuffix('-right')}-left"


def _absolute_point(
    piece: dict[str, object], point: tuple[float, float]
) -> tuple[float, float]:
    frame = piece["frame"]
    assert isinstance(frame, dict)
    return (
        frame["x"] + point[0] * frame["width"],
        frame["y"] + point[1] * frame["height"],
    )


def _manufacturer_transformed_point(
    presentation_id: str,
    target_side: str,
    point: tuple[float, float],
) -> tuple[float, float]:
    x, y = point
    if presentation_id == "orientation-2":
        return (y / 2, 1 - 2 * x) if target_side == "left" else (1 - y / 2, 2 * x - 1)
    if presentation_id == "orientation-3":
        return (0.5 - x, 1 - y) if target_side == "left" else (1.5 - x, 1 - y)
    if presentation_id == "orientation-4":
        return (y / 2, 2 - 2 * x) if target_side == "left" else (1 - y / 2, 2 * x)
    raise AssertionError(f"unexpected secondary presentation: {presentation_id}")


def _transformed_frame(
    presentation_id: str,
    target_side: str,
    frame: dict[str, float],
) -> dict[str, float]:
    corners = tuple(
        _manufacturer_transformed_point(presentation_id, target_side, point)
        for point in (
            (frame["x"], frame["y"]),
            (frame["x"] + frame["width"], frame["y"]),
            (frame["x"], frame["y"] + frame["height"]),
            (frame["x"] + frame["width"], frame["y"] + frame["height"]),
        )
    )
    xs = tuple(point[0] for point in corners)
    ys = tuple(point[1] for point in corners)
    return {
        "x": min(xs),
        "y": min(ys),
        "width": max(xs) - min(xs),
        "height": max(ys) - min(ys),
    }


@pytest.fixture(scope="module")
def package() -> board_package.BoardPackage:
    return board_package.load_board_package(PACKAGE_ROOT)


def _pixel_sizes() -> dict[str, tuple[int, int]]:
    return {
        asset_path: board_package._png_dimensions(PACKAGE_ROOT / asset_path)
        for _, _, asset_path, _ in EXPECTED_PRESENTATIONS
    }


def test_package_contents_and_metadata(package: board_package.BoardPackage) -> None:
    board = package.board

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"assets", "board.json"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        Path(asset_path).name for _, _, asset_path, _ in EXPECTED_PRESENTATIONS
    }
    pixel_sizes = _pixel_sizes()
    assert board["id"] == "trango.rock-prodigy-pivot"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Pivot"
    assert board["dimensions"] == "15.5 × 5 × 2.5 in"
    assert board["presentations"] == [
        {
            "id": presentation_id,
            "name": presentation_name,
            "assetPath": asset_path,
            "aspectRatio": pixel_sizes[asset_path][0] / pixel_sizes[asset_path][1],
            "default": is_default,
        }
        for presentation_id, presentation_name, asset_path, is_default in EXPECTED_PRESENTATIONS
    ]
    assert set(pixel_sizes.values()) == {EXPECTED_PIXEL_SIZE}
    assert Counter(hold["presentationID"] for hold in board["holds"]) == Counter(
        {
            presentation_id: len(EXPECTED_HOLDS)
            for presentation_id, *_ in EXPECTED_PRESENTATIONS
        }
    )
    assert board["aspectRatio"] == EXPECTED_PIXEL_SIZE[0] / EXPECTED_PIXEL_SIZE[1]


def test_hold_inventory_kinds_and_source_audited_metadata(
    package: board_package.BoardPackage,
) -> None:
    board = package.board

    assert board_package._HOLD_KINDS == ALLOWED_KINDS
    assert all(hold["kind"] in ALLOWED_KINDS for hold in board["holds"])
    assert Counter(hold["kind"] for hold in board["holds"]) == Counter(
        {
            kind: count * len(EXPECTED_PRESENTATIONS)
            for kind, count in EXPECTED_KIND_COUNTS.items()
        }
    )

    for presentation_id, *_ in EXPECTED_PRESENTATIONS:
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
            if hold["presentationID"] == presentation_id
        )
        assert actual_holds == tuple(
            (_hold_id(base_id, presentation_id), kind, metadata)
            for base_id, kind, metadata in EXPECTED_HOLDS
        )
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == (
        EXPECTED_PIECE_COUNT * len(EXPECTED_PRESENTATIONS)
    )
    assert {
        hold["id"]: len(hold["geometry"])
        for hold in board["holds"]
        if len(hold["geometry"]) != 1
    } == {
        _hold_id(base_id, presentation_id): 2
        for presentation_id, *_ in EXPECTED_PRESENTATIONS
        for base_id in (
            "outer-wedge-pinch-left",
            "outer-wedge-pinch-right",
            "lower-sloper-left",
            "lower-sloper-right",
        )
    }


def test_piece_geometry_fills_declared_frames(
    package: board_package.BoardPackage,
) -> None:
    pixel_sizes = _pixel_sizes()
    for hold in package.board["holds"]:
        width, height = pixel_sizes[
            next(
                asset_path
                for presentation_id, _, asset_path, _ in EXPECTED_PRESENTATIONS
                if presentation_id == hold["presentationID"]
            )
        ]
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


def test_left_three_finger_pocket_exposes_a_smooth_bezier_junction(
    package: board_package.BoardPackage,
) -> None:
    document = board_package.editor_document(package)
    region = next(
        region
        for region in document["regions"]
        if region["key"] == "three-finger-pocket-left-piece-0"
    )

    assert region["smoothAnchorIndexes"] == [6]


def test_secondary_presentation_pixels_are_exact_manufacturer_transforms() -> None:
    with Image.open(PACKAGE_ROOT / "assets" / "primary.png") as source_image:
        source_image.load()
        assert source_image.mode == "RGBA"
        assert source_image.size == EXPECTED_PIXEL_SIZE

        for (
            presentation_id,
            half_transforms,
        ) in EXPECTED_SECONDARY_HALF_TRANSFORMS.items():
            expected = Image.new(source_image.mode, source_image.size)
            for source_side, target_side, transform in half_transforms:
                transformed_half = source_image.crop(_half_box(source_side)).transpose(
                    transform
                )
                expected.paste(transformed_half, _half_box(target_side)[:2])

            asset_path = next(
                asset_path
                for candidate_id, _, asset_path, _ in EXPECTED_PRESENTATIONS
                if candidate_id == presentation_id
            )
            with Image.open(PACKAGE_ROOT / asset_path) as actual:
                actual.load()
                assert actual.mode == expected.mode
                assert actual.size == expected.size
                assert actual.tobytes() == expected.tobytes()


def test_secondary_geometry_is_exact_manufacturer_transform_of_orientation_one(
    package: board_package.BoardPackage,
) -> None:
    holds = {hold["id"]: hold for hold in package.board["holds"]}

    for presentation_id in EXPECTED_SECONDARY_HALF_TRANSFORMS:
        for base_id, *_ in EXPECTED_HOLDS:
            target_side = "left" if base_id.endswith("-left") else "right"
            source_id = (
                _opposite_side_hold_id(base_id)
                if presentation_id == "orientation-4"
                else base_id
            )
            source_geometry = holds[source_id]["geometry"]
            target_geometry = holds[_hold_id(base_id, presentation_id)]["geometry"]
            assert len(target_geometry) == len(source_geometry)

            for source_piece, target_piece in zip(
                source_geometry, target_geometry, strict=True
            ):
                assert target_piece.keys() == source_piece.keys()
                assert target_piece.get("treatment") == source_piece.get("treatment")

                expected_frame = _transformed_frame(
                    presentation_id, target_side, source_piece["frame"]
                )
                assert target_piece["frame"] == pytest.approx(expected_frame, abs=1e-12)

                source_shape = source_piece["shape"]
                target_shape = target_piece["shape"]
                assert target_shape.keys() == source_shape.keys()
                assert target_shape["type"] == source_shape["type"]
                source_commands = source_shape["commands"]
                target_commands = target_shape["commands"]
                assert len(target_commands) == len(source_commands)

                for source_command, target_command in zip(
                    source_commands, target_commands, strict=True
                ):
                    assert target_command.keys() == source_command.keys()
                    assert target_command["command"] == source_command["command"]
                    source_points = _command_points(source_command)
                    target_points = _command_points(target_command)
                    assert len(target_points) == len(source_points)
                    for source_point, target_point in zip(
                        source_points, target_points, strict=True
                    ):
                        expected_point = _manufacturer_transformed_point(
                            presentation_id,
                            target_side,
                            _absolute_point(source_piece, source_point),
                        )
                        assert _absolute_point(
                            target_piece, target_point
                        ) == pytest.approx(expected_point, abs=1e-12)


def test_left_and_right_geometry_are_mirrored(
    package: board_package.BoardPackage,
) -> None:
    holds = {hold["id"]: hold for hold in package.board["holds"]}
    for presentation_id, *_ in EXPECTED_PRESENTATIONS:
        for base_left_id, base_right_id in MIRRORED_PAIRS:
            left_geometry = holds[_hold_id(base_left_id, presentation_id)]["geometry"]
            right_geometry = holds[_hold_id(base_right_id, presentation_id)]["geometry"]
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
