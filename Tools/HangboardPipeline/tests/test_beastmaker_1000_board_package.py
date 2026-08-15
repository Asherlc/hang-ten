from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from hangboard_vectorizer.beastmaker_v14_paths import ACCEPTED_V14_PATHS
from hangboard_vectorizer.board_catalog import load_board_package
from hangboard_vectorizer.board_library import _CanonicalPackageRunner
from hangboard_vectorizer.display_paths import flatten_display_path, parse_display_path


REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = REPO_ROOT / "Hangboards" / "beastmaker-1000"
TEMPLATE_PATH = (
    REPO_ROOT
    / "Tools/HangboardPipeline/src/hangboard_vectorizer/products/beastmaker-1000.json"
)
EXPECTED_HOLDS = (
    ("jug-left", "jug"),
    ("jug-right", "jug"),
    ("sloper-35-left", "sloper"),
    ("sloper-35-right", "sloper"),
    ("sloper-center", "sloper"),
    ("pocket-top-outer-left", "pocket"),
    ("pocket-top-outer-right", "pocket"),
    ("pocket-top-left", "pocket"),
    ("pocket-top-right", "pocket"),
    ("pocket-middle-outer-left", "pocket"),
    ("pocket-middle-mid-left", "pocket"),
    ("pocket-middle-inner-left", "pocket"),
    ("pocket-middle-center", "pocket"),
    ("pocket-middle-inner-right", "pocket"),
    ("pocket-middle-mid-right", "pocket"),
    ("pocket-middle-outer-right", "pocket"),
    ("pocket-bottom-outer-left", "pocket"),
    ("pocket-bottom-mid-left", "pocket"),
    ("pocket-bottom-inner-left", "pocket"),
    ("pocket-bottom-inner-right", "pocket"),
    ("pocket-bottom-mid-right", "pocket"),
    ("pocket-bottom-outer-right", "pocket"),
)
REFINED_SLOPERS = {"sloper-35-left", "sloper-35-right"}


def test_beastmaker_1000_preserves_inventory_and_unmodified_accepted_paths() -> None:
    package = load_board_package(PACKAGE_ROOT)
    template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    template_regions = {region["id"]: region for region in template["regions"]}

    assert [(hold.id, hold.kind) for hold in package.board.holds] == list(EXPECTED_HOLDS)
    assert all(hold.geometry for hold in package.board.holds)
    assert {
        region_id: region["displayPath"]
        for region_id, region in template_regions.items()
    } == ACCEPTED_V14_PATHS

    for hold in package.board.holds:
        assert len(hold.geometry) == 1
        piece = hold.geometry[0]
        source = parse_display_path(
            template_regions[hold.id]["displayPath"],
            f"regions.{hold.id}.displayPath",
            1000,
            259,
            allow_linear_segments=True,
        )
        rendered = parse_display_path(
            _CanonicalPackageRunner._piece_path(piece, 1000, 259),
            f"holds.{hold.id}.geometry",
            1000,
            259,
            allow_linear_segments=True,
        )
        assert source is not None and rendered is not None
        if hold.id not in REFINED_SLOPERS:
            assert rendered.commands == source.commands
            assert [
                value for point in rendered.coordinates for value in point
            ] == pytest.approx(
                [value for point in source.coordinates for value in point], abs=1e-9
            )

        xs = [point[0] for point in rendered.coordinates]
        ys = [point[1] for point in rendered.coordinates]
        assert (
            piece.frame.x * 1000,
            piece.frame.y * 259,
            (piece.frame.x + piece.frame.width) * 1000,
            (piece.frame.y + piece.frame.height) * 259,
        ) == pytest.approx((min(xs), min(ys), max(xs), max(ys)), abs=1e-9)


def test_beastmaker_1000_slopers_do_not_spill_into_transparent_notches() -> None:
    package = load_board_package(PACKAGE_ROOT)
    with Image.open(PACKAGE_ROOT / "assets/primary.png") as image:
        alpha = np.asarray(image.convert("RGBA"), dtype=np.uint8)[..., 3]
    width, height = 1000, 259
    scale = 4
    alpha4x = cv2.resize(
        alpha,
        (width * scale, height * scale),
        interpolation=cv2.INTER_NEAREST,
    )
    distance_outside_board = cv2.distanceTransform(
        (alpha4x == 0).astype(np.uint8), cv2.DIST_L2, 5
    )

    for hold_id in ("sloper-35-left", "sloper-35-right"):
        hold = next(hold for hold in package.board.holds if hold.id == hold_id)
        rendered = parse_display_path(
            _CanonicalPackageRunner._piece_path(hold.geometry[0], width, height),
            f"holds.{hold_id}.geometry",
            width,
            height,
            allow_linear_segments=True,
        )
        assert rendered is not None
        contour = flatten_display_path(rendered, scale=scale, curve_steps=128)
        mask = np.zeros_like(alpha4x)
        cv2.fillPoly(mask, [np.rint(contour).astype(np.int32)], 255)

        assert distance_outside_board[mask > 0].max() / scale <= 3.0
