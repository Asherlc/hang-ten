from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.board_catalog import load_board_package


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "yy-verticalboard-first"
EXPECTED_HOLDS = (
    ("pocket-45", "45 mm four-finger pocket", "pocket", 45, 4, 2),
    ("pocket-33", "33 mm four-finger pocket", "pocket", 33, 4, 2),
    ("pocket-25", "25 mm four-finger pocket", "pocket", 25, 4, 2),
    ("pocket-22", "22 mm four-finger pocket", "pocket", 22, 4, 2),
    ("pocket-20", "20 mm four-finger pocket", "pocket", 20, 4, 2),
    ("center-handle", "40 / 24 mm center handle", "edge", None, None, 2),
    ("sloper-35", "35° sloper", "sloper", None, None, 2),
    ("sloper-20", "20° sloper", "sloper", None, None, 1),
    ("jug-left", "Left jug", "jug", None, None, 1),
    ("jug-right", "Right jug", "jug", None, None, 1),
)
# Literal review contract from the accepted numbered overlay and source audit. The
# piece index is meaningful: paired holds are left then right, while the center
# handle is specifically upper 40 mm then lower 24 mm.
EXPECTED_PIECES = {
    ("pocket-45", 0): {
        "frame": (0.089, 0.454, 0.147, 0.084),
        "treatment": {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"},
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("pocket-45", 1): {
        "frame": (0.764, 0.454, 0.147, 0.084),
        "treatment": {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"},
        "pathDigest": "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094",
    },
    ("pocket-33", 0): {
        "frame": (0.249, 0.455, 0.143, 0.081),
        "treatment": {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"},
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("pocket-33", 1): {
        "frame": (0.608, 0.455, 0.143, 0.081),
        "treatment": {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"},
        "pathDigest": "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094",
    },
    ("pocket-25", 0): {
        "frame": (0.09, 0.345, 0.145, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("pocket-25", 1): {
        "frame": (0.765, 0.345, 0.145, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094",
    },
    ("pocket-22", 0): {
        "frame": (0.285, 0.596, 0.14, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("pocket-22", 1): {
        "frame": (0.575, 0.596, 0.14, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094",
    },
    ("pocket-20", 0): {
        "frame": (0.138, 0.596, 0.14, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("pocket-20", 1): {
        "frame": (0.722, 0.596, 0.14, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "bd8addd2817a7608a041627eb4751d4469f6319505708c6cb66f7de7b4510094",
    },
    ("center-handle", 0): {
        "contact": "upper-40-mm",
        "frame": (0.43, 0.455, 0.14, 0.082),
        "treatment": {"type": "recess", "rimInsetFraction": 0.1, "depth": "deep"},
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("center-handle", 1): {
        "contact": "lower-24-mm",
        "frame": (0.432, 0.597, 0.136, 0.08),
        "treatment": {
            "type": "recess",
            "rimInsetFraction": 0.1,
            "depth": "shallow",
        },
        "pathDigest": "e25b71e3c57a8b0d8db6b33be0df032141a35e800446cd0c90b4b23356621952",
    },
    ("sloper-35", 0): {
        "frame": (0.251, 0.311, 0.143, 0.104),
        "treatment": {"type": "surface"},
        "pathDigest": "dc87355812bc565f3ae440fc257116e3fd93f19ded489b6f3b22acafab947347",
    },
    ("sloper-35", 1): {
        "frame": (0.606, 0.311, 0.143, 0.104),
        "treatment": {"type": "surface"},
        "pathDigest": "0be6e6cc96179c075fad20d7bcf9a48d5f5ba5d1340a726db552377033f65c52",
    },
    ("sloper-20", 0): {
        "frame": (0.394, 0.312, 0.212, 0.052),
        "treatment": {"type": "surface"},
        "pathDigest": "105868228cb1f512018bc4eea7207b339f0836c87cc0bbdc9ffe78c7a7f13cf5",
    },
    ("jug-left", 0): {
        "frame": (0.073, 0.291, 0.177, 0.051),
        "treatment": {"type": "surface"},
        "pathDigest": "686b58bb5a730c13ecc77c70357f9285c35058fdbb0ce5f29fdf190e66f96a53",
    },
    ("jug-right", 0): {
        "frame": (0.75, 0.291, 0.177, 0.051),
        "treatment": {"type": "surface"},
        "pathDigest": "ae205f67af4382c9ecd2f261fb931a6308f65893170eccc7e45f75837aecb22d",
    },
}
MIRRORED_MULTI_PIECE_HOLDS = (
    "pocket-45",
    "pocket-33",
    "pocket-25",
    "pocket-22",
    "pocket-20",
    "sloper-35",
)


def _frame_tuple(piece: object) -> tuple[float, float, float, float]:
    return (piece.frame.x, piece.frame.y, piece.frame.width, piece.frame.height)


def _path_digest(piece: object) -> str:
    commands = [
        {
            "command": command.command,
            "to": command.to,
            "control": command.control,
            "control1": command.control1,
            "control2": command.control2,
        }
        for command in piece.shape.commands
    ]
    canonical_commands = json.dumps(
        commands, sort_keys=True, separators=(",", ":")
    ).encode()
    return sha256(canonical_commands).hexdigest()


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (command.to, command.control, command.control1, command.control2)
        if point is not None
    )


def _assert_exact_global_mirror(left: object, right: object) -> None:
    assert right.frame.x == pytest.approx(
        1 - left.frame.x - left.frame.width, abs=1e-12
    )
    assert right.frame.y == pytest.approx(left.frame.y, abs=1e-12)
    assert right.frame.width == pytest.approx(left.frame.width, abs=1e-12)
    assert right.frame.height == pytest.approx(left.frame.height, abs=1e-12)
    assert right.treatment == left.treatment
    assert [command.command for command in right.shape.commands] == [
        command.command for command in left.shape.commands
    ]
    for left_command, right_command in zip(
        left.shape.commands, right.shape.commands, strict=True
    ):
        for (left_x, left_y), (right_x, right_y) in zip(
            _points(left_command), _points(right_command), strict=True
        ):
            assert right_x == pytest.approx(1 - left_x, abs=1e-12)
            assert right_y == pytest.approx(left_y, abs=1e-12)


def _overlap_area(left: object, right: object) -> float:
    width = max(
        0.0,
        min(left.x + left.width, right.x + right.width) - max(left.x, right.x),
    )
    height = max(
        0.0,
        min(left.y + left.height, right.y + right.height) - max(left.y, right.y),
    )
    return width * height


def test_yy_verticalboard_first_preserves_audited_logical_holds_and_contacts() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold.id: hold for hold in board.holds}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert board.id == "yy.verticalboard-first"
    assert board.manufacturer == "YY Vertical"
    assert board.name == "VerticalBoard First"
    assert board.facts["subtitle"] == (
        "Ten-grip poplar hangboard with five four-finger pocket depths, two sloper "
        "angles, two jugs, and a central handle."
    )
    assert board.facts["productURL"] == (
        "https://www.yyvertical.com/en/products/verticalboard-first"
    )
    assert board.facts["dimensions"] == "540 × 130 × 50 mm"
    assert board.facts["aspectRatio"] == pytest.approx(54 / 13, abs=1e-12)
    assert board.presentation_asset_path == "assets/primary.png"
    source_asset = PACKAGE_ROOT / board.presentation_asset_path
    assert sha256(source_asset.read_bytes()).hexdigest() == (
        "e765f9ffad834127c96499008d5f99fa768bd11764e64cb96becc6d93d8a8011"
    )
    with Image.open(source_asset) as image:
        assert image.size == (1774, 887)
    assert tuple(
        (
            hold.id,
            hold.name,
            hold.kind,
            hold.size_millimeters,
            hold.finger_capacity,
            len(hold.geometry),
        )
        for hold in board.holds
    ) == EXPECTED_HOLDS
    assert Counter(hold.kind for hold in board.holds) == {
        "pocket": 5,
        "edge": 1,
        "sloper": 2,
        "jug": 2,
    }
    assert Counter(
        hold.kind for hold in board.holds for _piece in hold.geometry
    ) == {"pocket": 10, "edge": 2, "sloper": 3, "jug": 2}
    assert sum(len(hold.geometry) for hold in board.holds) == 17

    pieces = [piece for hold in board.holds for piece in hold.geometry]
    actual_pieces = {
        (hold.id, piece_index): piece
        for hold in board.holds
        for piece_index, piece in enumerate(hold.geometry)
    }
    assert actual_pieces.keys() == EXPECTED_PIECES.keys()
    for piece_key, expected in EXPECTED_PIECES.items():
        piece = actual_pieces[piece_key]
        assert _frame_tuple(piece) == expected["frame"]
        assert piece.treatment == expected["treatment"]
        assert _path_digest(piece) == expected["pathDigest"]

    for piece in pieces:
        assert piece.shape.type == "path"
        assert piece.shape.commands[0].command == "move"
        assert piece.shape.commands[-1].command == "close"
        assert sum(
            command.command == "curve" for command in piece.shape.commands
        ) >= 4
        assert 0 <= piece.frame.x < piece.frame.x + piece.frame.width <= 1
        assert 0 <= piece.frame.y < piece.frame.y + piece.frame.height <= 1
        assert piece.frame.width * piece.frame.height > 0
        for command in piece.shape.commands:
            for x, y in _points(command):
                assert 0 <= x <= 1
                assert 0 <= y <= 1

    for hold_id in MIRRORED_MULTI_PIECE_HOLDS:
        _assert_exact_global_mirror(
            holds[hold_id].geometry[0], holds[hold_id].geometry[1]
        )
    _assert_exact_global_mirror(
        holds["jug-left"].geometry[0], holds["jug-right"].geometry[0]
    )

    center_pieces = holds["center-handle"].geometry
    upper_40_mm, lower_24_mm = center_pieces
    assert EXPECTED_PIECES[("center-handle", 0)]["contact"] == "upper-40-mm"
    assert EXPECTED_PIECES[("center-handle", 1)]["contact"] == "lower-24-mm"
    assert upper_40_mm.frame.y < lower_24_mm.frame.y
    assert center_pieces[0].frame != center_pieces[1].frame
    assert center_pieces[0].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "deep",
    }
    assert center_pieces[1].treatment == {
        "type": "recess",
        "rimInsetFraction": 0.1,
        "depth": "shallow",
    }
    for piece in (*center_pieces, holds["sloper-20"].geometry[0]):
        assert piece.frame.x == pytest.approx(
            1 - piece.frame.x - piece.frame.width, abs=1e-12
        )

    for hold_id in ("sloper-35", "sloper-20", "jug-left", "jug-right"):
        assert all(
            piece.treatment == {"type": "surface"}
            for piece in holds[hold_id].geometry
        )
    for left_index, left in enumerate(pieces):
        for right in pieces[left_index + 1 :]:
            assert _overlap_area(left.frame, right.frame) == pytest.approx(0, abs=1e-12)

    assert all(hold.depth_range_millimeters is None for hold in board.holds)
    assert all(hold.grip_type is None for hold in board.holds)
    assert {hold.id: hold.finger_capacity for hold in board.holds} == {
        "pocket-45": 4,
        "pocket-33": 4,
        "pocket-25": 4,
        "pocket-22": 4,
        "pocket-20": 4,
        "center-handle": None,
        "sloper-35": None,
        "sloper-20": None,
        "jug-left": None,
        "jug-right": None,
    }
    assert all(hold.features is None for hold in board.holds)

    raw_document = json.loads((PACKAGE_ROOT / "board.json").read_text())
    forbidden_keys = {
        "cueStyle",
        "claims",
        "semantics",
        "evidence",
        "artwork",
        "ui",
        "depthRangeMillimeters",
        "gripType",
        "features",
    }

    def keys(value: object) -> set[str]:
        if isinstance(value, dict):
            return set(value).union(*(keys(item) for item in value.values()))
        if isinstance(value, list):
            return set().union(*(keys(item) for item in value))
        return set()

    assert forbidden_keys.isdisjoint(keys(raw_document))
    forbidden_files = {
        "semantics.json",
        "evidence.json",
        "artwork.json",
        "catalog.json",
    }
    assert forbidden_files.isdisjoint(
        path.name for path in PACKAGE_ROOT.rglob("*") if path.is_file()
    )
