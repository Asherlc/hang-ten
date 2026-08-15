from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageChops, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKBENCH_ROOT = REPO_ROOT / "Tools" / "HangboardWorkbench"
sys.path.insert(0, str(WORKBENCH_ROOT))

from board_package import load_board_package  # noqa: E402


PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "trango-rock-prodigy-training-center"
EXPECTED_PRIMARY_SHA256 = (
    "8d5c4e853a4186a0ca21cca32b57cd6844d9644a4a9b5dacdedfc9287fc22a35"
)
EXPECTED_HOLDS = (
    ("sloper-left", "sloper", 1),
    ("sloper-right", "sloper", 1),
    ("jug-left", "jug", 1),
    ("jug-right", "jug", 1),
    ("edge-large-vder-left", "edge", 1),
    ("edge-large-vder-right", "edge", 1),
    ("edge-shallow-vder-left", "edge", 1),
    ("edge-shallow-vder-right", "edge", 1),
    ("edge-thin-crimp-left", "edge", 1),
    ("edge-thin-crimp-right", "edge", 1),
    ("pocket-three-finger-slot-left", "pocket", 1),
    ("pocket-three-finger-slot-right", "pocket", 1),
    ("pocket-index-middle-deep-left", "pocket", 1),
    ("pocket-index-middle-deep-right", "pocket", 1),
    ("pocket-middle-ring-deep-left", "pocket", 1),
    ("pocket-middle-ring-deep-right", "pocket", 1),
    ("pocket-index-middle-medium-shallow-left", "pocket", 1),
    ("pocket-index-middle-medium-shallow-right", "pocket", 1),
    ("pocket-middle-ring-shallow-left", "pocket", 1),
    ("pocket-middle-ring-shallow-right", "pocket", 1),
    ("pinch-medium-left", "pinch", 2),
    ("pinch-medium-right", "pinch", 2),
    ("pinch-wide-left", "pinch", 2),
    ("pinch-wide-right", "pinch", 2),
)
MIRRORED_PAIRS = tuple(
    (left_id, right_id)
    for left_id, right_id in zip(
        (hold_id for hold_id, _, _ in EXPECTED_HOLDS if hold_id.endswith("-left")),
        (hold_id for hold_id, _, _ in EXPECTED_HOLDS if hold_id.endswith("-right")),
        strict=True,
    )
)
CANVAS_SIZE = (1254, 1254)

# Hand-checked against the accepted 1254 × 1254 overlay. Literal frames catch
# moving a complete symmetric pair onto the wrong surface; literal path digests
# catch collapsing distinct calibrated contacts to one generic normalized path.
EXPECTED_PIECE_GEOMETRY = {
    ("sloper-left", 0): (
        (0.129186602870813, 0.339712918660287, 0.188995215311005, 0.055023923444976),
        "96a2e53506ffba0bcb2e1ec5851d9cc8c51f534cbe6ed1f625336216dc832190",
    ),
    ("sloper-right", 0): (
        (0.681818181818182, 0.339712918660287, 0.188995215311005, 0.055023923444976),
        "d553cb0e5342ec3bb9624c9b820ac9635053e9889d016ca833f6623239d3b07b",
    ),
    ("jug-left", 0): (
        (0.317384370015949, 0.331738437001595, 0.128389154704944, 0.054226475279107),
        "873b2d039a5d1dc3b485e02e1c949a947c2de2231c3f205663673d0192797c69",
    ),
    ("jug-right", 0): (
        (0.554226475279107, 0.331738437001595, 0.128389154704944, 0.054226475279107),
        "96399cf9defa67c2ac37969d11eb746741ebae8a728995168f9b2f35e885b5ad",
    ),
    ("edge-large-vder-left", 0): (
        (0.192982456140351, 0.394736842105263, 0.232854864433812, 0.04066985645933),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("edge-large-vder-right", 0): (
        (0.574162679425837, 0.394736842105263, 0.232854864433812, 0.04066985645933),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("edge-shallow-vder-left", 0): (
        (0.194577352472089, 0.43859649122807, 0.231259968102073, 0.039872408293461),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("edge-shallow-vder-right", 0): (
        (0.574162679425837, 0.43859649122807, 0.231259968102073, 0.039872408293461),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("edge-thin-crimp-left", 0): (
        (0.222488038277512, 0.490430622009569, 0.099681020733652, 0.027113237639553),
        "3fd87a875b1c3020f4449e37beb2e1a73ba10007f6a9656135c37c793fbcc445",
    ),
    ("edge-thin-crimp-right", 0): (
        (0.677830940988836, 0.490430622009569, 0.099681020733652, 0.027113237639553),
        "1b73b20d91ddb0f3b7750b26cbed2d0d6f34a9d52f0e698b00cb16eaa7c49fb2",
    ),
    ("pocket-three-finger-slot-left", 0): (
        (0.335725677830941, 0.481658692185008, 0.090111642743222, 0.027910685805423),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("pocket-three-finger-slot-right", 0): (
        (0.574162679425837, 0.481658692185008, 0.090111642743222, 0.027910685805423),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("pocket-index-middle-deep-left", 0): (
        (0.203349282296651, 0.543062200956938, 0.078149920255183, 0.027113237639553),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("pocket-index-middle-deep-right", 0): (
        (0.718500797448166, 0.543062200956938, 0.078149920255183, 0.027113237639553),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("pocket-middle-ring-deep-left", 0): (
        (0.311004784688995, 0.54066985645933, 0.054226475279107, 0.029505582137161),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("pocket-middle-ring-deep-right", 0): (
        (0.634768740031898, 0.54066985645933, 0.054226475279107, 0.029505582137161),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("pocket-index-middle-medium-shallow-left", 0): (
        (0.240031897926635, 0.598883572567783, 0.050239234449761, 0.027113237639553),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("pocket-index-middle-medium-shallow-right", 0): (
        (0.709728867623604, 0.598883572567783, 0.050239234449761, 0.027113237639553),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("pocket-middle-ring-shallow-left", 0): (
        (0.311004784688995, 0.596491228070175, 0.054226475279107, 0.028708133971292),
        "933b6602f87f0dca4a134493157aa0ceb4d5f01f47ad056be614406d06daa43d",
    ),
    ("pocket-middle-ring-shallow-right", 0): (
        (0.634768740031898, 0.596491228070175, 0.054226475279107, 0.028708133971292),
        "9bc7b316c24c525ce1e78159c1d44da5dc100a4df028150eda901308c9ec0b45",
    ),
    ("pinch-medium-left", 0): (
        (0.119617224880383, 0.353269537480064, 0.038277511961722, 0.129984051036683),
        "13afca465a233f416295e55549d003c3b2bb77935e1d3b3110e57fff3cecd8cf",
    ),
    ("pinch-medium-left", 1): (
        (0.119617224880383, 0.45933014354067, 0.058213716108453, 0.059808612440191),
        "7182baa398012651e38e914eeb830666abfc437a2fe6166c95727e1bb10f8591",
    ),
    ("pinch-medium-right", 0): (
        (0.842105263157895, 0.353269537480064, 0.038277511961722, 0.129984051036683),
        "c60b6746d3bb7caeb70a971cd09c16dc3ece21ce85058799201fcc9f96a92dd3",
    ),
    ("pinch-medium-right", 1): (
        (0.822169059011164, 0.45933014354067, 0.058213716108453, 0.059808612440191),
        "965669140ad2670685248b8d9ff5dc1935f48831d552284eab4021183269d62f",
    ),
    ("pinch-wide-left", 0): (
        (0.017543859649123, 0.353269537480064, 0.10207336523126, 0.137161084529506),
        "8734b6519be6c582730b6c6c7a4fe94404149a130a3079b93f2234b8830903bd",
    ),
    ("pinch-wide-left", 1): (
        (0.054226475279107, 0.490430622009569, 0.065390749601276, 0.028708133971292),
        "2ef561d90892109db5eb1a3903ca7e84c6dc1f42961d7cf19f1b48fe2a7e4c92",
    ),
    ("pinch-wide-right", 0): (
        (0.880382775119617, 0.353269537480064, 0.10207336523126, 0.137161084529506),
        "2affcb46dcdd4ed200729bc49b7bd38fad77de34fa0d7ea75577e863c5590c31",
    ),
    ("pinch-wide-right", 1): (
        (0.880382775119617, 0.490430622009569, 0.065390749601276, 0.028708133971292),
        "4985d557b1fcaab797635ebedba42eb1615e118c9be7400260125fa360237c77",
    ),
}

# These are the six one-pixel shared seams visible in the accepted overlay.
# A new pair or growth past its literal ceiling indicates broad area collision.
EXPECTED_OVERLAP_CEILINGS = {
    ("sloper-left", "jug-left"): 24,
    ("sloper-left", "pinch-medium-left"): 34,
    ("sloper-right", "jug-right"): 24,
    ("sloper-right", "pinch-medium-right"): 34,
    ("pinch-medium-left", "pinch-wide-left"): 158,
    ("pinch-medium-right", "pinch-wide-right"): 158,
}


def _shape_digest(raw_shape: object) -> str:
    canonical = json.dumps(
        raw_shape,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cubic_points(
    start: tuple[float, float],
    control1: tuple[float, float],
    control2: tuple[float, float],
    end: tuple[float, float],
    *,
    steps: int = 32,
) -> tuple[tuple[float, float], ...]:
    points = []
    for index in range(1, steps + 1):
        t = index / steps
        inverse = 1 - t
        points.append(
            (
                inverse**3 * start[0]
                + 3 * inverse**2 * t * control1[0]
                + 3 * inverse * t**2 * control2[0]
                + t**3 * end[0],
                inverse**3 * start[1]
                + 3 * inverse**2 * t * control1[1]
                + 3 * inverse * t**2 * control2[1]
                + t**3 * end[1],
            )
        )
    return tuple(points)


def _piece_polygon(piece: object) -> tuple[tuple[float, float], ...]:
    local_points: list[tuple[float, float]] = []
    current = None
    start = None
    for command in piece["shape"]["commands"]:
        if command["command"] == "move":
            current = command.get("to")
            start = current
            local_points.append(current)
        elif command["command"] == "curve":
            assert current is not None
            assert command.get("control1") is not None
            assert command.get("control2") is not None
            assert command.get("to") is not None
            local_points.extend(
                _cubic_points(
                    current,
                    command["control1"],
                    command["control2"],
                    command["to"],
                )
            )
            current = command["to"]
        elif command["command"] == "close":
            assert start is not None
            if current != start:
                local_points.append(start)
            current = start
        else:
            raise AssertionError(f"unsupported path command: {command['command']}")

    width, height = CANVAS_SIZE
    return tuple(
        (
            (piece["frame"]["x"] + local_x * piece["frame"]["width"]) * width,
            (piece["frame"]["y"] + local_y * piece["frame"]["height"]) * height,
        )
        for local_x, local_y in local_points
    )


def _hold_mask(hold: object) -> Image.Image:
    mask = Image.new("L", CANVAS_SIZE, 0)
    draw = ImageDraw.Draw(mask)
    for piece in hold["geometry"]:
        draw.polygon(_piece_polygon(piece), fill=255)
    return mask


def _intersection_pixels(left: Image.Image, right: Image.Image) -> int:
    return ImageChops.multiply(left, right).histogram()[255]


def _points(command: object) -> tuple[tuple[float, float], ...]:
    return tuple(
        point
        for point in (
            command.get("to"),
            command.get("control"),
            command.get("control1"),
            command.get("control2"),
        )
        if point is not None
    )


def _nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_nested_keys(child) for child in value.values()))
    if isinstance(value, list):
        return set().union(*(_nested_keys(child) for child in value))
    return set()


def test_trango_rock_prodigy_training_center_audited_structure_and_geometry() -> None:
    board = load_board_package(PACKAGE_ROOT).board
    holds = {hold["id"]: hold for hold in board["holds"]}
    raw = board
    raw_holds = {hold["id"]: hold for hold in raw["holds"]}

    assert {path.name for path in PACKAGE_ROOT.iterdir()} == {"board.json", "assets"}
    assert {path.name for path in (PACKAGE_ROOT / "assets").iterdir()} == {
        "primary.png"
    }
    assert hashlib.sha256(
        (PACKAGE_ROOT / "assets" / "primary.png").read_bytes()
    ).hexdigest() == EXPECTED_PRIMARY_SHA256

    assert board["id"] == "trango.rock-prodigy-training-center"
    assert board["manufacturer"] == "Trango"
    assert board["name"] == "Rock Prodigy Training Center"
    assert board["dimensions"] == "9.1 × 12.1 in"
    assert math.isclose(board["aspectRatio"], 1.0, abs_tol=1e-12)
    assert board["presentation"]["assetPath"] == "assets/primary.png"
    assert tuple(
        (hold["id"], hold["kind"], len(hold["geometry"])) for hold in board["holds"]
    ) == EXPECTED_HOLDS
    assert len(board["holds"]) == 24
    assert sum(len(hold["geometry"]) for hold in board["holds"]) == 28
    assert Counter(hold["kind"] for hold in board["holds"]) == {
        "pocket": 10,
        "edge": 6,
        "pinch": 4,
        "jug": 2,
        "sloper": 2,
    }

    for hold in board["holds"]:
        assert hold.get("sizeMillimeters") is None
        assert hold.get("depthRangeMillimeters") is None
        for piece in hold["geometry"]:
            assert piece.get("treatment") is None
            assert piece["shape"]["type"] == "path"
            assert piece["shape"]["commands"][0]["command"] == "move"
            assert piece["shape"]["commands"][-1]["command"] == "close"
            assert sum(
                command["command"] == "curve" for command in piece["shape"]["commands"]
            ) >= 4
            assert {
                command["command"] for command in piece["shape"]["commands"]
            } <= {"move", "curve", "close"}
            assert 0 <= piece["frame"]["x"] < piece["frame"]["x"] + piece["frame"]["width"] <= 1
            assert 0 <= piece["frame"]["y"] < piece["frame"]["y"] + piece["frame"]["height"] <= 1
            assert piece["frame"]["width"] * piece["frame"]["height"] > 0
            for command in piece["shape"]["commands"]:
                assert all(
                    0 <= coordinate <= 1
                    for point in _points(command)
                    for coordinate in point
                )

    # These literal expectations fail if a symmetric pair is moved together or
    # if a calibrated outline is replaced with a reusable generic path.
    actual_piece_geometry = {
        (hold["id"], piece_index): (
            (
                piece["frame"]["x"],
                piece["frame"]["y"],
                piece["frame"]["width"],
                piece["frame"]["height"],
            ),
            _shape_digest(raw_holds[hold["id"]]["geometry"][piece_index]["shape"]),
        )
        for hold in board["holds"]
        for piece_index, piece in enumerate(hold["geometry"])
    }
    assert actual_piece_geometry == EXPECTED_PIECE_GEOMETRY

    # Rasterize all 24 holds independently. Only the six audited one-pixel seam
    # contacts may overlap, and none may grow past its measured pixel ceiling.
    masks = {hold["id"]: _hold_mask(hold) for hold in board["holds"]}
    hold_ids = tuple(masks)
    actual_overlaps = {
        (left_id, right_id): pixels
        for left_index, left_id in enumerate(hold_ids)
        for right_id in hold_ids[left_index + 1 :]
        if (pixels := _intersection_pixels(masks[left_id], masks[right_id])) > 0
    }
    assert set(actual_overlaps) == set(EXPECTED_OVERLAP_CEILINGS)
    assert all(
        pixels <= EXPECTED_OVERLAP_CEILINGS[pair]
        for pair, pixels in actual_overlaps.items()
    )

    for left_id, right_id in MIRRORED_PAIRS:
        left_pieces = holds[left_id]["geometry"]
        right_pieces = holds[right_id]["geometry"]
        assert len(left_pieces) == len(right_pieces)
        for left, right in zip(left_pieces, right_pieces, strict=True):
            assert math.isclose(
                right["frame"]["x"],
                1 - left["frame"]["x"] - left["frame"]["width"],
                abs_tol=1e-12,
            )
            assert right["frame"]["y"] == left["frame"]["y"]
            assert right["frame"]["width"] == left["frame"]["width"]
            assert right["frame"]["height"] == left["frame"]["height"]
            for left_command, right_command in zip(
                left["shape"]["commands"], right["shape"]["commands"], strict=True
            ):
                assert left_command["command"] == right_command["command"]
                for (left_x, left_y), (right_x, right_y) in zip(
                    _points(left_command), _points(right_command), strict=True
                ):
                    assert math.isclose(right_x, 1 - left_x, abs_tol=1e-12)
                    assert math.isclose(right_y, left_y, abs_tol=1e-12)

    assert holds["sloper-left"].get("gripType") == "sloper"
    assert holds["sloper-right"].get("gripType") == "sloper"
    assert holds["jug-left"].get("features") == ["jug"]
    assert holds["jug-right"].get("features") == ["jug"]
    assert holds["edge-large-vder-left"].get("gripType") == "openHand"
    assert holds["edge-large-vder-right"].get("gripType") == "openHand"
    assert holds["edge-large-vder-left"].get("features") == ["largeOpenHandRail"]
    assert holds["edge-large-vder-right"].get("features") == ["largeOpenHandRail"]
    assert holds["edge-thin-crimp-left"].get("features") == ["thinCrimp"]
    assert holds["edge-thin-crimp-right"].get("features") == ["thinCrimp"]
    assert holds["pocket-three-finger-slot-left"].get("fingerCapacity") == 3
    assert holds["pocket-three-finger-slot-right"].get("fingerCapacity") == 3
    assert holds["pocket-three-finger-slot-left"].get("gripType") == "threeFingerPocket"
    assert holds["pocket-three-finger-slot-right"].get("gripType") == "threeFingerPocket"
    assert holds["pocket-three-finger-slot-left"].get("features") == [
        "shallowThreeFingerSlot",
    ]
    assert holds["pocket-three-finger-slot-right"].get("features") == [
        "shallowThreeFingerSlot",
    ]
    assert all(
        holds[hold_id].get("fingerCapacity") == 2
        for hold_id in (
            "pocket-index-middle-deep-left",
            "pocket-index-middle-deep-right",
            "pocket-middle-ring-deep-left",
            "pocket-middle-ring-deep-right",
            "pocket-index-middle-medium-shallow-left",
            "pocket-index-middle-medium-shallow-right",
            "pocket-middle-ring-shallow-left",
            "pocket-middle-ring-shallow-right",
        )
    )
    assert all(
        holds[hold_id].get("gripType") == "twoFingerPocket"
        for hold_id in (
            "pocket-index-middle-deep-left",
            "pocket-index-middle-deep-right",
            "pocket-middle-ring-deep-left",
            "pocket-middle-ring-deep-right",
            "pocket-index-middle-medium-shallow-left",
            "pocket-index-middle-medium-shallow-right",
            "pocket-middle-ring-shallow-left",
            "pocket-middle-ring-shallow-right",
        )
    )
    assert all(
        holds[hold_id].get("features") == ["deepTwoFingerPocket"]
        for hold_id in (
            "pocket-index-middle-deep-left",
            "pocket-index-middle-deep-right",
            "pocket-middle-ring-deep-left",
            "pocket-middle-ring-deep-right",
        )
    )
    assert all(
        holds[hold_id].get("features") == ["twoFingerPocket"]
        for hold_id in (
            "pocket-index-middle-medium-shallow-left",
            "pocket-index-middle-medium-shallow-right",
            "pocket-middle-ring-shallow-left",
            "pocket-middle-ring-shallow-right",
        )
    )
    assert holds["pinch-medium-left"].get("features") == ["mediumPinch"]
    assert holds["pinch-medium-right"].get("features") == ["mediumPinch"]
    assert holds["pinch-wide-left"].get("features") == ["widePinch"]
    assert holds["pinch-wide-right"].get("features") == ["widePinch"]

    forbidden = {
        "artwork",
        "catalog",
        "claims",
        "cueStyle",
        "evidence",
        "semantics",
        "ui",
    }
    assert forbidden.isdisjoint(_nested_keys(raw))
