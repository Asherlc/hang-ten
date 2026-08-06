from __future__ import annotations

from dataclasses import replace
import base64
import hashlib
from importlib import resources
import json
import xml.etree.ElementTree as ET

import cv2
import numpy as np
import pytest

from hangboard_vectorizer.alignment import AlignmentInfo
from hangboard_vectorizer.export import build_manifest, render_preview, render_svg
from hangboard_vectorizer.geometry import Opening, RectifiedBoard
from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.overrides import apply_overrides
from hangboard_vectorizer.regions import GripRegion
from hangboard_vectorizer.templates import (
    get_product_template,
    layout_from_template,
    load_template_document,
)


SVG = "{http://www.w3.org/2000/svg}"

BEASTMAKER_1000_IDS = (
    "jug-left",
    "jug-right",
    "sloper-35-left",
    "sloper-35-right",
    "sloper-center",
    "pocket-top-outer-left",
    "pocket-top-outer-right",
    "pocket-top-left",
    "pocket-top-right",
    "pocket-middle-outer-left",
    "pocket-middle-mid-left",
    "pocket-middle-inner-left",
    "pocket-middle-center",
    "pocket-middle-inner-right",
    "pocket-middle-mid-right",
    "pocket-middle-outer-right",
    "pocket-bottom-outer-left",
    "pocket-bottom-mid-left",
    "pocket-bottom-inner-left",
    "pocket-bottom-inner-right",
    "pocket-bottom-mid-right",
    "pocket-bottom-outer-right",
)


def test_render_svg_embeds_the_exact_beastmaker_asset_under_semantic_overlays():
    product = replace(
        get_product_template("beastmaker-1000"),
        render_profile=None,
    )
    board = RectifiedBoard(
        rgb=np.zeros((259, 1000, 3), dtype=np.uint8),
        mask=np.ones((259, 1000), dtype=bool),
        width=1000,
        height=259,
    )
    regions = layout_from_template(product, board).regions

    root = ET.fromstring(render_svg(board, (), regions, product=product))

    (image,) = root.findall(f"./{SVG}image[@class='product-render']")
    assert image.attrib["x"] == "0"
    assert image.attrib["y"] == "0"
    assert image.attrib["width"] == "1000"
    assert image.attrib["height"] == "259"
    assert image.attrib["preserveAspectRatio"] == "none"
    assert image.attrib["href"].startswith("data:image/png;base64,")
    embedded = base64.b64decode(image.attrib["href"].partition(",")[2])
    packaged = (
        resources.files("hangboard_vectorizer.products")
        .joinpath("beastmaker-1000-render.png")
        .read_bytes()
    )
    assert embedded == packaged
    assert hashlib.sha256(packaged).hexdigest() == (
        "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627"
    )

    overlays = root.findall(f"./{SVG}path[@class='grip-region']")
    assert tuple(path.attrib["id"] for path in overlays) == BEASTMAKER_1000_IDS
    assert sum(path.attrib["id"] == "sloper-center" for path in overlays) == 1
    assert not {"sloper-20-left", "sloper-20-right"}.intersection(
        path.attrib["id"] for path in overlays
    )
    assert root.findall(f".//{SVG}path[@class='board-silhouette']") == []
    assert root.findall(f".//{SVG}path[@class='board-front-face']") == []
    assert not any(
        "grip-decoration" in element.attrib.get("class", "").split()
        for element in root.findall(".//*")
    )
    assert root.findall(f".//{SVG}path[@class='opening']") == []

    css = root.find(f"./{SVG}style")
    assert css is not None
    assert ".product-render { pointer-events: none; }" in css.text
    assert (
        ".grip-region { fill: transparent; stroke: none; pointer-events: all; }"
        in css.text
    )
    assert ".grip-region:hover { fill: #ff5a1f; fill-opacity: .24; }" in css.text
    assert ".grip-region.active { fill: #ff5a1f; fill-opacity: .48; }" in css.text

    children = list(root)
    image_index = children.index(image)
    assert all(image_index < children.index(overlay) for overlay in overlays)


def test_asset_backed_rename_preserves_the_exact_reviewed_display_path():
    product = replace(
        get_product_template("beastmaker-1000"),
        product_id="renamable-asset-board",
    )
    board = RectifiedBoard(
        rgb=np.zeros((259, 1000, 3), dtype=np.uint8),
        mask=np.ones((259, 1000), dtype=bool),
        width=1000,
        height=259,
    )
    original_regions = layout_from_template(product, board).regions
    renamed_regions = apply_overrides(
        original_regions,
        {"version": 1, "rename": {"pocket-top-left": "warmup-pocket"}},
        board.width,
        board.height,
    )

    original_root = ET.fromstring(
        render_svg(board, (), original_regions, product=product)
    )
    renamed_root = ET.fromstring(
        render_svg(board, (), renamed_regions, product=product)
    )

    original_path = original_root.find(
        f".//{SVG}path[@id='pocket-top-left']"
    )
    renamed_path = renamed_root.find(f".//{SVG}path[@id='warmup-pocket']")
    assert original_path is not None
    assert renamed_path is not None
    assert renamed_path.attrib["d"] == original_path.attrib["d"]
    assert "C" in renamed_path.attrib["d"] or "Q" in renamed_path.attrib["d"]


def test_asset_backed_output_rejects_a_region_without_native_display_geometry():
    product = replace(
        get_product_template("beastmaker-1000"),
        product_id="asset-board",
    )
    board = RectifiedBoard(
        rgb=np.zeros((259, 1000, 3), dtype=np.uint8),
        mask=np.ones((259, 1000), dtype=bool),
        width=1000,
        height=259,
    )
    regions = list(layout_from_template(product, board).regions)
    regions[0] = replace(regions[0], display_path=None)

    with pytest.raises(ConversionError, match="native display geometry"):
        render_svg(board, (), tuple(regions), product=product)
    with pytest.raises(ConversionError, match="native display geometry"):
        build_manifest("photo.png", board, (), tuple(regions), product=product)


def test_render_svg_preserves_curated_branch_for_profile_without_render_asset():
    product = replace(
        get_product_template("beastmaker-1000"),
        render_asset=None,
    )
    board = RectifiedBoard(
        rgb=np.zeros((259, 1000, 3), dtype=np.uint8),
        mask=np.ones((259, 1000), dtype=bool),
        width=1000,
        height=259,
    )
    regions = layout_from_template(product, board).regions

    root = ET.fromstring(render_svg(board, (), regions, product=product))

    assert root.findall(f".//{SVG}image[@class='product-render']") == []
    assert len(root.findall(f".//{SVG}path[@class='board-silhouette']")) == 1
    assert len(root.findall(f".//{SVG}path[@class='grip-region']")) == 22


def test_render_svg_uses_product_display_paths_and_keeps_semantic_ids():
    document = {
        "schemaVersion": 1,
        "productId": "smooth-board",
        "displayName": "Smooth Board",
        "canonicalViewBox": [0, 0, 100, 50],
        "outline": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
        "displayOutlinePath": (
            "M 0 5 Q 0 0 5 0 L 95 0 Q 100 0 100 5 "
            "L 100 45 Q 100 50 95 50 L 5 50 Q 0 50 0 45 Z"
        ),
        "regions": [{
            "id": "pocket-left",
            "type": "pocket",
            "label": "Pocket left",
            "side": "left",
            "polygons": [[[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]],
            "displayPath": (
                "M 10 15 C 10 12 13 10 16 10 L 34 10 "
                "C 38 10 40 13 40 17 L 40 25 C 40 28 37 30 34 30 "
                "L 16 30 C 13 30 10 27 10 24 Z"
            ),
        }],
    }
    product = load_template_document(document)
    board = _board()
    region = layout_from_template(product, board).regions[0]

    root = ET.fromstring(render_svg(board, (), (region,), product=product))

    silhouette = root.find(f".//{SVG}path[@class='board-silhouette']")
    assert silhouette is not None
    assert "Q" in silhouette.attrib["d"]
    overlay = root.find(f".//{SVG}path[@id='pocket-left']")
    assert overlay is not None
    assert "C" in overlay.attrib["d"]
    assert overlay.attrib["data-type"] == "pocket"
    assert overlay.attrib["data-source"] == "template"
    css = root.find(f".//{SVG}style")
    assert css is not None
    assert ".board-silhouette { fill: url(#board-wood); filter: drop-shadow(" in css.text
    assert ".grip-pocket-cavity { fill: url(#pocket-cavity);" in css.text
    assert ".grip-region { fill: transparent; stroke: none;" in css.text
    assert ".grip-region:hover { fill: #ff5a1f; fill-opacity: .32; }" in css.text
    assert ".grip-region.active { fill: #ff5a1f; fill-opacity: .62; }" in css.text


def test_render_svg_keeps_polygon_fallback_without_product_display_geometry():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening)

    root = ET.fromstring(render_svg(board, (opening,), (region,)))

    silhouette = root.find(f".//{SVG}path[@class='board-silhouette']")
    overlay = root.find(f".//{SVG}path[@id='grip-a']")
    assert silhouette is not None and "L" in silhouette.attrib["d"]
    assert overlay is not None and "L" in overlay.attrib["d"]


def test_render_svg_preserves_legacy_styling_without_product():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("pocket-a", opening)

    root = ET.fromstring(render_svg(board, (opening,), (region,)))

    overlay = root.find(f".//{SVG}path[@id='pocket-a']")
    assert overlay is not None
    assert overlay.attrib["data-type"] == "pocket"
    css = root.find(f".//{SVG}style")
    assert css is not None
    assert css.text == (
        ".grip-region { fill: transparent; pointer-events: all; }\n"
        ".grip-region:hover { fill: #ff5a1f; fill-opacity: .25; }\n"
        ".grip-region.active { fill: #ff5a1f; fill-opacity: .55; }"
    )


def test_render_svg_preserves_legacy_styling_for_product_without_display_paths():
    product = load_template_document(
        {
            "schemaVersion": 1,
            "productId": "polygon-board",
            "displayName": "Polygon Board",
            "canonicalViewBox": [0, 0, 100, 50],
            "outline": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
            "regions": [
                {
                    "id": "pocket-left",
                    "type": "pocket",
                    "label": "Pocket left",
                    "side": "left",
                    "polygons": [
                        [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]
                    ],
                }
            ],
        }
    )
    board = _board()
    region = layout_from_template(product, board).regions[0]

    root = ET.fromstring(render_svg(board, (), (region,), product=product))

    overlay = root.find(f".//{SVG}path[@id='pocket-left']")
    assert overlay is not None
    assert overlay.attrib["data-type"] == "pocket"
    assert "L" in overlay.attrib["d"]
    css = root.find(f".//{SVG}style")
    assert css is not None
    assert css.text == (
        ".grip-region { fill: transparent; pointer-events: all; }\n"
        ".grip-region:hover { fill: #ff5a1f; fill-opacity: .25; }\n"
        ".grip-region.active { fill: #ff5a1f; fill-opacity: .55; }"
    )


def test_render_svg_ignores_disabled_curated_regions_when_selecting_styles():
    product = load_template_document(
        {
            "schemaVersion": 1,
            "productId": "disabled-smooth-board",
            "displayName": "Disabled Smooth Board",
            "canonicalViewBox": [0, 0, 100, 50],
            "outline": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
            "regions": [
                {
                    "id": "pocket-left",
                    "type": "pocket",
                    "label": "Pocket left",
                    "side": "left",
                    "polygons": [
                        [[0.1, 0.2], [0.4, 0.2], [0.4, 0.6], [0.1, 0.6]]
                    ],
                    "displayPath": (
                        "M 10 15 C 10 12 13 10 16 10 L 34 10 "
                        "C 38 10 40 13 40 17 L 40 25 C 40 28 37 30 34 30 "
                        "L 16 30 C 13 30 10 27 10 24 Z"
                    ),
                }
            ],
        }
    )
    board = _board()
    region = replace(layout_from_template(product, board).regions[0], disabled=True)

    root = ET.fromstring(render_svg(board, (), (region,), product=product))

    assert root.findall(f".//{SVG}path[@class='grip-region']") == []
    css = root.find(f".//{SVG}style")
    assert css is not None
    assert css.text == (
        ".grip-region { fill: transparent; pointer-events: all; }\n"
        ".grip-region:hover { fill: #ff5a1f; fill-opacity: .25; }\n"
        ".grip-region.active { fill: #ff5a1f; fill-opacity: .55; }"
    )


def test_render_svg_preserves_aspect_ratio_and_emits_separate_visible_shapes():
    board = _board()
    openings = (
        _opening("opening-a", (20, 15), (40, 30)),
        _opening("opening-b", (60, 15), (80, 30)),
    )
    regions = (
        _region("grip-a", openings[0], side="left"),
        _region("grip-b", openings[1], disabled=True),
    )

    root = ET.fromstring(render_svg(board, openings, regions))

    assert root.attrib["viewBox"] == "0 0 1000 500"
    assert len(root.findall(f".//{SVG}path[@class='board-silhouette']")) == 1
    assert len(root.findall(f".//{SVG}path[@class='opening']")) == 2
    assert len(root.findall(f".//{SVG}path[@class='grip-region']")) == 1


def test_render_svg_exposes_region_metadata_and_highlight_css():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening, side="right")

    root = ET.fromstring(
        render_svg(board, (opening,), (region,), highlight_color="#12abef")
    )

    (overlay,) = root.findall(f".//{SVG}path[@class='grip-region']")
    assert overlay.attrib == {
        "id": "grip-a",
        "class": "grip-region",
        "data-opening": "opening-a",
        "data-type": "pocket",
        "data-source": "automatic",
        "data-side": "right",
        "d": overlay.attrib["d"],
    }
    css = root.find(f".//{SVG}style")
    assert css is not None
    assert ".grip-region { fill: transparent; pointer-events: all; }" in css.text
    assert ".grip-region:hover { fill: #12abef; fill-opacity: .25; }" in css.text
    assert ".grip-region.active { fill: #12abef; fill-opacity: .55; }" in css.text


def test_render_svg_omits_side_metadata_when_region_has_no_side():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening)

    root = ET.fromstring(render_svg(board, (opening,), (region,)))

    (overlay,) = root.findall(f".//{SVG}path[@class='grip-region']")
    assert "data-side" not in overlay.attrib


def test_build_manifest_includes_canvas_warnings_and_normalized_geometry():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening, side="left")

    manifest = build_manifest("photo.png", board, (opening,), (region,))

    assert manifest["schemaVersion"] == 1
    assert manifest["source"] == "photo.png"
    assert manifest["canvas"] == {"width": 100, "height": 50}
    assert manifest["warnings"] == ["fixture warning"]
    assert manifest["openings"][0]["id"] == "opening-a"
    assert manifest["regions"][0]["openingId"] == "opening-a"
    assert manifest["regions"][0]["side"] == "left"
    for item in (*manifest["openings"], *manifest["regions"]):
        assert all(0.0 <= value <= 1.0 for value in item["center"])
        assert all(0.0 <= value <= 1.0 for value in item["bbox"])
        assert all(
            0.0 <= coordinate <= 1.0
            for point in item["contour"]
            for coordinate in point
        )


def test_build_manifest_converts_numpy_scalars_to_json_numbers():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    opening = Opening(
        id=opening.id,
        contour=opening.contour.astype(np.float32),
        center=(np.float32(opening.center[0]), np.float64(opening.center[1])),
        bbox=tuple(np.int32(value) for value in opening.bbox),
        area=np.float32(opening.area),
        aspect_ratio=np.float64(opening.aspect_ratio),
    )

    manifest = build_manifest("photo.png", board, (opening,), (_region("grip-a", opening),))

    json.dumps(manifest)
    assert type(manifest["openings"][0]["center"][0]) is float
    assert type(manifest["openings"][0]["bbox"][0]) is float


def test_build_manifest_rejects_automatic_region_without_an_existing_opening():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening)
    invalid = GripRegion(
        id=region.id,
        opening_id="missing",
        type=region.type,
        side=region.side,
        contour=region.contour,
        center=region.center,
        bbox=region.bbox,
    )

    with np.testing.assert_raises_regex(ValueError, "existing opening"):
        build_manifest("photo.png", board, (opening,), (invalid,))


def test_build_manifest_allows_override_region_without_an_opening():
    board = _board()
    opening = _opening("opening-a", (20, 15), (40, 30))
    region = _region("grip-a", opening)
    override = GripRegion(
        id="manual-grip",
        opening_id="",
        type="unknown",
        side=None,
        contour=region.contour,
        center=region.center,
        bbox=region.bbox,
        source="override",
    )

    manifest = build_manifest("photo.png", board, (opening,), (override,))

    assert manifest["regions"][0]["source"] == "override"
    assert manifest["regions"][0]["openingId"] == ""


def test_semantic_region_export_preserves_template_metadata_without_an_opening():
    board = _board()
    contour = _rectangle((10, 5), (40, 20))
    center, bbox = _geometry(contour)
    region = GripRegion(
        id="sloper-left",
        opening_id="",
        type="sloper",
        side="left",
        contour=contour,
        center=center,
        bbox=bbox,
        source="template",
        label="Left 35 degree sloper",
        metadata=(("angleDeg", 35), ("featured", True)),
    )

    manifest = build_manifest("photo.png", board, (), (region,))
    root = ET.fromstring(render_svg(board, (), (region,)))

    assert manifest["regions"][0]["openingId"] is None
    assert manifest["regions"][0]["label"] == "Left 35 degree sloper"
    assert manifest["regions"][0]["metadata"] == {
        "angleDeg": 35,
        "featured": True,
    }
    (overlay,) = root.findall(f".//{SVG}path[@class='grip-region']")
    assert overlay.attrib["data-source"] == "template"
    assert overlay.attrib["data-type"] == "sloper"
    assert overlay.attrib["data-side"] == "left"
    assert overlay.attrib["data-label"] == "Left 35 degree sloper"


def test_build_manifest_adds_exact_product_and_alignment_records_when_supplied():
    template = load_template_document(
        {
            "schemaVersion": 1,
            "productId": "test-board",
            "displayName": "Test Board",
            "canonicalViewBox": [0, 0, 100, 50],
            "outline": [[[0, 0], [1, 0], [1, 1], [0, 1]]],
            "regions": [],
        }
    )
    alignment = AlignmentInfo(
        method="minimum-area-frame",
        aspect_ratio_error=0.021,
        confidence="high",
    )

    manifest = build_manifest(
        "photo.png", _board(), (), (), product=template, alignment=alignment
    )

    assert manifest["product"] == {
        "id": "test-board",
        "displayName": "Test Board",
        "templateSchemaVersion": 1,
    }
    assert manifest["alignment"] == {
        "method": "minimum-area-frame",
        "aspectRatioError": 0.021,
        "confidence": "high",
    }


def test_disconnected_merge_components_survive_svg_and_manifest_export():
    board = _board()
    opening = _opening("opening-a", (10, 10), (90, 30))
    left = _region_from_rectangle("left", opening.id, (10, 10), (30, 30))
    right = _region_from_rectangle("right", opening.id, (70, 10), (90, 30))
    (merged,) = apply_overrides(
        (left, right),
        {"version": 1, "merge": [{"ids": ["left", "right"], "id": "combined"}]},
        board.width,
        board.height,
    )

    root = ET.fromstring(render_svg(board, (opening,), (merged,)))
    (overlay,) = root.findall(f".//{SVG}path[@class='grip-region']")
    manifest = build_manifest("photo.png", board, (opening,), (merged,))

    assert overlay.attrib["d"].count("M ") == 2
    assert len(manifest["regions"][0]["contours"]) == 2


def test_cross_opening_merge_is_an_override_accepted_by_manifest():
    board = _board()
    left_opening = _opening("opening-a", (10, 10), (30, 30))
    right_opening = _opening("opening-b", (30, 10), (50, 30))
    (merged,) = apply_overrides(
        (
            _region("left", left_opening),
            _region("right", right_opening),
        ),
        {"version": 1, "merge": [{"ids": ["left", "right"], "id": "combined"}]},
        board.width,
        board.height,
    )

    assert merged.source == "override"
    assert merged.opening_id == ""
    manifest = build_manifest(
        "photo.png", board, (left_opening, right_opening), (merged,)
    )
    assert manifest["regions"][0]["source"] == "override"


def test_render_preview_matches_board_and_marks_every_region_boundary():
    board = _board()
    board = RectifiedBoard(
        rgb=np.full_like(board.rgb, 40),
        mask=board.mask,
        width=board.width,
        height=board.height,
        warnings=board.warnings,
    )
    opening = _opening("opening-a", (10, 10), (90, 35))
    regions = (
        _region_from_rectangle("left-grip", opening.id, (10, 10), (45, 35)),
        _region_from_rectangle("right-grip", opening.id, (55, 10), (90, 35)),
    )

    preview = render_preview(board, (opening,), regions)

    assert preview.shape == (board.height, board.width, 3)
    assert preview.dtype == np.uint8
    for region in regions:
        boundary = np.rint(region.contour).astype(int)
        assert any(
            not np.array_equal(preview[y, x], board.rgb[y, x])
            for x, y in boundary
        )


def _board() -> RectifiedBoard:
    mask = np.zeros((50, 100), dtype=bool)
    mask[5:46, 5:96] = True
    return RectifiedBoard(
        rgb=np.zeros((50, 100, 3), dtype=np.uint8),
        mask=mask,
        width=100,
        height=50,
        warnings=("fixture warning",),
    )


def _opening(
    opening_id: str,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> Opening:
    contour = _rectangle(top_left, bottom_right)
    center, bbox = _geometry(contour)
    return Opening(
        id=opening_id,
        contour=contour,
        center=center,
        bbox=bbox,
        area=float(cv2.contourArea(contour.astype(np.float32))),
        aspect_ratio=bbox[2] / bbox[3],
    )


def _region(
    region_id: str,
    opening: Opening,
    *,
    side: str | None = None,
    disabled: bool = False,
) -> GripRegion:
    return GripRegion(
        id=region_id,
        opening_id=opening.id,
        type="pocket",
        side=side,
        contour=opening.contour,
        center=opening.center,
        bbox=opening.bbox,
        disabled=disabled,
    )


def _region_from_rectangle(
    region_id: str,
    opening_id: str,
    top_left: tuple[int, int],
    bottom_right: tuple[int, int],
) -> GripRegion:
    contour = _rectangle(top_left, bottom_right)
    center, bbox = _geometry(contour)
    return GripRegion(
        id=region_id,
        opening_id=opening_id,
        type="pocket",
        side=None,
        contour=contour,
        center=center,
        bbox=bbox,
    )


def _rectangle(
    top_left: tuple[int, int], bottom_right: tuple[int, int]
) -> np.ndarray:
    return np.array(
        [
            top_left,
            (bottom_right[0], top_left[1]),
            bottom_right,
            (top_left[0], bottom_right[1]),
        ],
        dtype=float,
    )


def _geometry(
    contour: np.ndarray,
) -> tuple[tuple[float, float], tuple[int, int, int, int]]:
    integer_contour = np.rint(contour).astype(np.int32)
    x, y, width, height = cv2.boundingRect(integer_contour)
    moments = cv2.moments(integer_contour)
    return (
        (moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]),
        (x, y, width, height),
    )
