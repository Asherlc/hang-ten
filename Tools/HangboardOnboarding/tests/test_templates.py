from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import replace
from dataclasses import FrozenInstanceError
import math
from pathlib import Path
import tomllib

import cv2
import numpy as np
import pytest

from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.display_paths import flatten_display_path
from hangboard_vectorizer.geometry import RectifiedBoard
from hangboard_vectorizer import templates
from hangboard_vectorizer.templates import (
    get_product_template,
    layout_from_template,
    list_product_templates,
    load_template_document,
)


VALID = {
    "schemaVersion": 1,
    "productId": "test-board",
    "displayName": "Test Board",
    "canonicalViewBox": [0, 0, 1000, 250],
    "outline": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]],
    "regions": [
        {
            "id": "jug-left",
            "type": "jug",
            "label": "Left jug",
            "side": "left",
            "polygons": [
                [[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.3]]
            ],
            "metadata": {"fingerCount": 4, "depthMm": 20.0},
        }
    ],
}

VALID_RENDER_PROFILE = {
    "style": "pale-wood-heightfield-v1",
    "seed": 23,
    "supersample": 4,
    "bevelRadius": 7.5,
    "pocketDepth": 20.0,
    "surfaceRelief": 6.0,
    "frontDrop": 8.0,
    "grainStrength": 0.075,
    "lightDirection": [-0.35, -0.42, 0.84],
}


def test_load_template_document_normalizes_immutable_template_models():
    """Changing model shape, polygon normalization, or metadata ordering is a bug."""
    template = load_template_document(VALID)

    assert template.product_id == "test-board"
    assert (template.canonical_width, template.canonical_height) == (1000, 250)
    assert template.display_outline_path is None
    assert template.render_profile is None
    assert template.render_asset is None
    assert not hasattr(template, "__dict__")
    assert not hasattr(template.regions[0], "__dict__")
    assert template.regions[0].display_path is None
    assert template.regions[0].metadata == (("depthMm", 20.0), ("fingerCount", 4))
    assert template.outline[0].dtype == np.float64
    assert template.outline[0].shape == (4, 2)
    assert not template.outline[0].flags.writeable
    assert not template.regions[0].polygons[0].flags.writeable
    with pytest.raises(FrozenInstanceError):
        template.display_name = "Changed"  # type: ignore[misc]
    with pytest.raises(ValueError):
        template.regions[0].polygons[0][0, 0] = 0.2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("style", "other"),
        ("seed", -1),
        ("supersample", 1),
        ("supersample", 5),
        ("bevelRadius", 0.0),
        ("pocketDepth", -1.0),
        ("surfaceRelief", 0.0),
        ("frontDrop", -0.1),
        ("grainStrength", -0.01),
        ("grainStrength", 0.26),
        ("lightDirection", [0.0, 0.0, 0.0]),
        ("lightDirection", [0.0, 1.0]),
        ("lightDirection", [0.0, float("inf"), 1.0]),
    ],
)
def test_load_template_document_rejects_invalid_render_profile_values(field, value):
    """The heightfield renderer must receive a bounded, normalized profile."""
    document = deepcopy(VALID)
    document["renderProfile"] = deepcopy(VALID_RENDER_PROFILE)
    document["renderProfile"][field] = value

    with pytest.raises(ConversionError, match="renderProfile"):
        load_template_document(document)


@pytest.mark.parametrize(
    "render_asset",
    ["../board.png", "nested/board.png", "board.jpg", ".png", "board image.png"],
)
def test_load_template_document_rejects_unsafe_render_asset_names(render_asset):
    document = deepcopy(VALID)
    document["renderAsset"] = render_asset

    with pytest.raises(ConversionError, match="renderAsset"):
        load_template_document(document)


def test_load_template_document_accepts_a_safe_png_render_asset_name():
    document = deepcopy(VALID)
    document["renderAsset"] = "test-board-render.png"

    assert load_template_document(document).render_asset == "test-board-render.png"


def test_load_template_document_accepts_render_profile_without_an_asset():
    document = deepcopy(VALID)
    document["renderProfile"] = deepcopy(VALID_RENDER_PROFILE)

    template = load_template_document(document)

    assert template.render_profile is not None
    assert template.render_asset is None


def test_flatten_display_path_returns_a_closed_scaled_curve_contour():
    """Curved display paths must flatten without rounding away sampled geometry."""
    document = deepcopy(VALID)
    document["displayOutlinePath"] = (
        "M 0 0 Q 10 20 20 0 C 25 0 30 10 20 20 L 0 20 Z"
    )
    path = load_template_document(document).display_outline_path
    assert path is not None

    contour = flatten_display_path(path, scale=0.5, curve_steps=4)

    assert contour.dtype == np.float64
    assert contour.shape == (11, 2)
    assert np.array_equal(contour[0], contour[-1])
    assert np.isfinite(contour).all()
    assert any(np.allclose(point, (5.0, 5.0)) for point in contour)


@pytest.mark.parametrize(
    ("scale", "curve_steps"),
    [(0.0, 2), (float("nan"), 2), (1.0, 1), (1.0, True)],
)
def test_flatten_display_path_rejects_invalid_rendering_parameters(scale, curve_steps):
    """Raster renderers cannot safely interpret invalid sampling inputs."""
    document = deepcopy(VALID)
    document["displayOutlinePath"] = "M 0 0 Q 10 20 20 0 L 0 20 Z"
    path = load_template_document(document).display_outline_path
    assert path is not None

    with pytest.raises(ValueError):
        flatten_display_path(path, scale=scale, curve_steps=curve_steps)


def test_load_template_document_accepts_immutable_smooth_display_paths():
    """Dropping display-path parsing would lose the smooth rendering geometry."""
    document = deepcopy(VALID)
    document["displayOutlinePath"] = (
        "M 0 20 Q 0 0 20 0 L 980 0 Q 1000 0 1000 20 "
        "L 1000 230 Q 1000 250 980 250 L 20 250 Q 0 250 0 230 Z"
    )
    document["regions"][0]["displayPath"] = (
        "M 100 25 C 100 15 110 10 120 10 L 280 10 "
        "C 290 10 300 20 300 30 L 300 70 C 300 80 290 90 280 90 "
        "L 120 90 C 110 90 100 80 100 70 Z"
    )

    template = load_template_document(document)

    assert template.display_outline_path is not None
    assert template.display_outline_path.commands == (
        "M", "Q", "L", "Q", "L", "Q", "L", "Q", "Z"
    )
    assert template.regions[0].display_path is not None
    assert "C" in template.regions[0].display_path.commands
    assert not hasattr(template.display_outline_path, "__dict__")
    assert template.display_outline_path.scaled(0.5).startswith("M 0 10 Q 0 0 10 0")


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("M 0 0 A 10 10 0 0 0 20 20 Z", "unsupported"),
        ("M 0 0 L 1001 0 Q 1000 10 990 20 Z", "canonical view box"),
        ("M 0 0 L 10 0 L 10 10 Z", "curved segment"),
        ("M 0 0 Q 10 0 10 10", "close with Z"),
        ("L 0 0 Q 10 0 10 10 Z", "start with M"),
        ("M 0 0 Q 10 0 10 10 Z onclick=alert(1)", "unsupported"),
    ],
)
def test_load_template_document_rejects_unsafe_display_paths(path, message):
    """Unsafe or non-renderable SVG-like paths must never reach renderers."""
    document = deepcopy(VALID)
    document["displayOutlinePath"] = path

    with pytest.raises(ConversionError, match=message):
        load_template_document(document)


@pytest.mark.parametrize(
    ("change", "field"),
    [
        (lambda doc: doc.__setitem__("schemaVersion", 2), "schemaVersion"),
        (lambda doc: doc["regions"][0].__setitem__("type", "crimp"), "type"),
        (lambda doc: doc.__setitem__("productId", "../test-board"), "productId"),
        (lambda doc: doc["regions"][0].__setitem__("id", "jug left"), "id"),
        (lambda doc: doc["regions"].append(deepcopy(doc["regions"][0])), "regions"),
        (lambda doc: doc["canonicalViewBox"].__setitem__(2, 0), "canonicalViewBox"),
        (lambda doc: doc.__setitem__("outline", []), "outline"),
        (lambda doc: doc["regions"][0].__setitem__("polygons", []), "polygons"),
        (
            lambda doc: doc["regions"][0].__setitem__(
                "polygons", [[[0.1, 0.1], [0.1, 0.1], [0.1, 0.1]]]
            ),
            "polygons",
        ),
        (
            lambda doc: doc["regions"][0].__setitem__(
                "polygons",
                [[[0.1, 0.1], [0.3, 0.1], [0.3, 0.3], [0.1, 0.1]]],
            ),
            "polygons",
        ),
        (
            lambda doc: doc["regions"][0].__setitem__(
                "polygons", [[[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]]
            ),
            "polygons",
        ),
        (
            lambda doc: doc.__setitem__(
                "outline", [[[0.1, 0.1], [0.2, 0.2], [0.3, 0.3]]]
            ),
            "outline",
        ),
        (
            lambda doc: doc["regions"][0]["polygons"][0][0].__setitem__(0, float("nan")),
            "polygons",
        ),
        (
            lambda doc: doc["regions"][0]["polygons"][0][0].__setitem__(0, float("inf")),
            "polygons",
        ),
        (
            lambda doc: doc["regions"][0]["polygons"][0][0].__setitem__(0, 1.01),
            "polygons",
        ),
    ],
)
def test_load_template_document_rejects_invalid_schema_values(change, field):
    """Removing any template validation branch should reject malformed input."""
    document = deepcopy(VALID)
    change(document)

    with pytest.raises(ConversionError, match=field):
        load_template_document(document)


def test_registry_discovers_templates_in_product_id_order(monkeypatch):
    """A registry that exposes package iteration order makes product selection unstable."""
    documents = [_document_with_product("zeta-board"), _document_with_product("alpha-board")]
    monkeypatch.setattr(templates, "_TEMPLATE_REGISTRY", None, raising=False)
    monkeypatch.setattr(templates, "_iter_template_documents", lambda: documents, raising=False)

    assert list_product_templates() == (("alpha-board", "Alpha Board"), ("zeta-board", "Zeta Board"))
    assert get_product_template("zeta-board").display_name == "Zeta Board"


def test_registry_rejects_duplicate_product_ids(monkeypatch):
    """Allowing two resources for one product makes lookup ambiguous."""
    documents = [_document_with_product("test-board"), _document_with_product("test-board")]
    monkeypatch.setattr(templates, "_TEMPLATE_REGISTRY", None, raising=False)
    monkeypatch.setattr(templates, "_iter_template_documents", lambda: documents, raising=False)

    with pytest.raises(ConversionError, match="productId"):
        list_product_templates()


def test_registry_unknown_product_names_sorted_supported_ids(monkeypatch):
    """An unknown-product error without supported IDs cannot guide the caller."""
    documents = [_document_with_product("zeta-board"), _document_with_product("alpha-board")]
    monkeypatch.setattr(templates, "_TEMPLATE_REGISTRY", None, raising=False)
    monkeypatch.setattr(templates, "_iter_template_documents", lambda: documents, raising=False)

    with pytest.raises(
        ConversionError, match=r"alpha-board, zeta-board"
    ):
        get_product_template("missing-board")


def _document_with_product(product_id: str) -> dict[str, object]:
    document = deepcopy(VALID)
    document["productId"] = product_id
    document["displayName"] = product_id.replace("-", " ").title()
    return document


def test_layout_from_template_scales_composite_region_into_canonical_pixels():
    """Template regions retain every component while exposing their combined geometry."""
    document = deepcopy(VALID)
    document["regions"][0]["polygons"] = [
        [[0.1, 0.1], [0.2, 0.1], [0.2, 0.3], [0.1, 0.3]],
        [[0.6, 0.1], [0.8, 0.1], [0.8, 0.3], [0.6, 0.3]],
    ]
    template = load_template_document(document)
    board = RectifiedBoard(
        rgb=np.zeros((250, 1000, 3), dtype=np.uint8),
        mask=np.ones((250, 1000), dtype=bool),
        width=1000,
        height=250,
    )

    layout = layout_from_template(template, board)

    assert layout.openings == ()
    assert len(layout.regions) == 1
    region = layout.regions[0]
    assert region.id == "jug-left"
    assert region.opening_id == ""
    assert region.source == "template"
    assert region.type == "jug"
    assert region.side == "left"
    assert region.label == "Left jug"
    assert region.metadata == (("depthMm", 20.0), ("fingerCount", 4))
    assert len(region.contours) == 2
    assert np.array_equal(
        region.contours[0],
        np.array([[100.0, 25.0], [200.0, 25.0], [200.0, 75.0], [100.0, 75.0]]),
    )
    assert np.array_equal(region.contour, region.contours[1])
    assert region.bbox == (100, 25, 701, 51)
    assert region.center == pytest.approx((516.0596026, 50.0))


def test_layout_from_template_rejects_non_finite_transformed_points():
    """Hand-constructed template models cannot leak invalid geometry into SVG output."""
    template = load_template_document(VALID)
    invalid_region = replace(
        template.regions[0],
        polygons=(np.array([[0.1, 0.1], [float("nan"), 0.1], [0.2, 0.2]]),),
    )
    invalid_template = replace(template, regions=(invalid_region,))
    board = RectifiedBoard(
        rgb=np.zeros((250, 1000, 3), dtype=np.uint8),
        mask=np.ones((250, 1000), dtype=bool),
        width=1000,
        height=250,
    )

    with pytest.raises(ConversionError, match="non-finite"):
        layout_from_template(invalid_template, board)


def test_layout_from_template_rejects_noncanonical_board_dimensions():
    """Template coordinates must never be emitted in a noncanonical coordinate system."""
    template = load_template_document(VALID)
    board = RectifiedBoard(
        rgb=np.zeros((250, 999, 3), dtype=np.uint8),
        mask=np.ones((250, 999), dtype=bool),
        width=999,
        height=250,
    )

    with pytest.raises(ConversionError, match="canonical dimensions"):
        layout_from_template(template, board)


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


def test_built_in_product_json_is_declared_as_package_data():
    """A wheel without product JSON makes the built-in registry silently empty."""
    project = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(
            encoding="utf-8"
        )
    )

    assert project["tool"]["setuptools"]["package-data"][
        "hangboard_vectorizer.products"
    ] == ["*.json", "*.png"]


def test_beastmaker_1000_template_has_exact_semantic_grip_map():
    """Changing product order, semantics, or symmetry breaks stable highlighting IDs."""
    template = get_product_template("beastmaker-1000")

    assert template.display_name == "Beastmaker 1000"
    assert (template.canonical_width, template.canonical_height) == (1000, 259)
    assert template.render_asset == "beastmaker-1000-render.png"
    assert tuple(region.id for region in template.regions) == BEASTMAKER_1000_IDS
    assert Counter(region.type for region in template.regions) == {
        "pocket": 17,
        "jug": 2,
        "sloper": 3,
    }

    by_id = {region.id: region for region in template.regions}
    assert by_id["pocket-middle-center"].side is None
    for region_id, angle in (
        ("sloper-35-left", 35),
        ("sloper-35-right", 35),
        ("sloper-center", 20),
    ):
        assert dict(by_id[region_id].metadata) == {"angleDeg": angle}

    board = RectifiedBoard(
        rgb=np.zeros((259, 1000, 3), dtype=np.uint8),
        mask=np.ones((259, 1000), dtype=bool),
        width=1000,
        height=259,
    )
    layout_by_id = {
        region.id: region for region in layout_from_template(template, board).regions
    }
    mirrored_pairs = (
        ("jug-left", "jug-right"),
        ("sloper-35-left", "sloper-35-right"),
        ("pocket-top-outer-left", "pocket-top-outer-right"),
        ("pocket-top-left", "pocket-top-right"),
        ("pocket-middle-outer-left", "pocket-middle-outer-right"),
        ("pocket-middle-mid-left", "pocket-middle-mid-right"),
        ("pocket-middle-inner-left", "pocket-middle-inner-right"),
        ("pocket-bottom-outer-left", "pocket-bottom-outer-right"),
        ("pocket-bottom-mid-left", "pocket-bottom-mid-right"),
        ("pocket-bottom-inner-left", "pocket-bottom-inner-right"),
    )
    for left_id, right_id in mirrored_pairs:
        assert by_id[left_id].side == "left"
        assert by_id[right_id].side == "right"
        normalized_center_sum = (
            layout_by_id[left_id].center[0] + layout_by_id[right_id].center[0]
        ) / template.canonical_width
        assert normalized_center_sum == pytest.approx(1.0, abs=0.035)

    assert by_id["sloper-center"].side is None

    for side in ("left", "right"):
        jug = layout_by_id[f"jug-{side}"]
        outer_pocket = layout_by_id[f"pocket-top-outer-{side}"]
        sloper = layout_by_id[f"sloper-35-{side}"]
        assert jug.type == "jug"
        assert outer_pocket.type == "pocket"
        assert jug.center[1] < outer_pocket.bbox[1]
        assert cv2.intersectConvexConvex(
            jug.contour.astype(np.float32), outer_pocket.contour.astype(np.float32)
        )[0] == pytest.approx(0.0)
        assert cv2.intersectConvexConvex(
            jug.contour.astype(np.float32), sloper.contour.astype(np.float32)
        )[0] == pytest.approx(0.0)


def test_beastmaker_1000_has_smooth_display_geometry_for_every_shape():
    template = get_product_template("beastmaker-1000")

    assert template.display_outline_path is not None
    assert any(command in ("Q", "C") for command in template.display_outline_path.commands)
    assert all(region.display_path is not None for region in template.regions)
    assert all(
        any(command in ("Q", "C") for command in region.display_path.commands)
        for region in template.regions
        if region.display_path is not None
    )


def test_beastmaker_1000_has_the_deterministic_heightfield_render_profile():
    """The built-in commercial renderer profile is part of the product contract."""
    template = get_product_template("beastmaker-1000")
    profile = template.render_profile

    assert profile is not None
    assert profile.style == "pale-wood-heightfield-v1"
    assert profile.seed == 23
    assert profile.supersample == 4
    assert profile.bevel_radius == pytest.approx(7.5)
    assert profile.pocket_depth == pytest.approx(20.0)
    assert profile.surface_relief == pytest.approx(6.0)
    assert profile.front_drop == pytest.approx(8.0)
    assert profile.grain_strength == pytest.approx(0.075)
    assert profile.light_direction == pytest.approx(
        (-0.3492151479, -0.4190581775, 0.8381163549)
    )
    assert math.hypot(*profile.light_direction) == pytest.approx(1.0)
    assert [
        region.id
        for region in template.regions
        if "center" in region.id and region.type == "sloper"
    ] == ["sloper-center"]


def test_beastmaker_outer_slopers_cut_deeper_than_jugs():
    template = get_product_template("beastmaker-1000")
    by_id = {region.id: region for region in template.regions}

    for side in ("left", "right"):
        jug = by_id[f"jug-{side}"]
        sloper = by_id[f"sloper-35-{side}"]
        assert sloper.polygons[0][:, 1].min() == pytest.approx(0.0)
        assert sloper.display_path is not None
        assert jug.display_path is not None
        sloper_y = [point[1] for point in sloper.display_path.coordinates]
        jug_y = [point[1] for point in jug.display_path.coordinates]
        assert min(sloper_y) == pytest.approx(0.0)
        assert max(sloper_y) > max(jug_y)

    center = by_id["sloper-center"]
    assert center.display_path is not None
    center_y = [point[1] for point in center.display_path.coordinates]
    assert min(center_y) == pytest.approx(0.0)
    assert max(center_y) < max(
        point[1]
        for point in by_id["sloper-35-left"].display_path.coordinates
    )


def _straight_curve_join_angles(path_data: str) -> list[tuple[str, float]]:
    tokens = path_data.split()
    segments: list[
        tuple[
            str,
            tuple[float, float],
            tuple[float, float],
        ]
    ] = []
    start: tuple[float, float] | None = None
    current: tuple[float, float] | None = None
    index = 0

    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "M":
            current = (float(tokens[index]), float(tokens[index + 1]))
            start = current
            index += 2
            continue
        assert current is not None and start is not None

        if command == "L":
            end = (float(tokens[index]), float(tokens[index + 1]))
            index += 2
            tangent = (end[0] - current[0], end[1] - current[1])
            segments.append((command, tangent, tangent))
        elif command == "Q":
            control = (float(tokens[index]), float(tokens[index + 1]))
            end = (float(tokens[index + 2]), float(tokens[index + 3]))
            index += 4
            segments.append(
                (
                    command,
                    (control[0] - current[0], control[1] - current[1]),
                    (end[0] - control[0], end[1] - control[1]),
                )
            )
        elif command == "C":
            control_1 = (float(tokens[index]), float(tokens[index + 1]))
            control_2 = (float(tokens[index + 2]), float(tokens[index + 3]))
            end = (float(tokens[index + 4]), float(tokens[index + 5]))
            index += 6
            segments.append(
                (
                    command,
                    (control_1[0] - current[0], control_1[1] - current[1]),
                    (end[0] - control_2[0], end[1] - control_2[1]),
                )
            )
        else:
            assert command == "Z"
            end = start
            tangent = (end[0] - current[0], end[1] - current[1])
            if tangent != (0.0, 0.0):
                segments.append(("L", tangent, tangent))
        current = end

    angles = []
    for segment_index, (incoming, outgoing) in enumerate(
        zip(segments, segments[1:] + segments[:1], strict=True)
    ):
        if (incoming[0] == "L") == (outgoing[0] == "L"):
            continue
        incoming_tangent = incoming[2]
        outgoing_tangent = outgoing[1]
        incoming_length = math.hypot(*incoming_tangent)
        outgoing_length = math.hypot(*outgoing_tangent)
        assert incoming_length > 0 and outgoing_length > 0
        cosine = (
            incoming_tangent[0] * outgoing_tangent[0]
            + incoming_tangent[1] * outgoing_tangent[1]
        ) / (incoming_length * outgoing_length)
        angle = math.degrees(math.acos(max(-1.0, min(1.0, cosine))))
        next_segment_index = (segment_index + 1) % len(segments)
        angles.append((f"segment {segment_index} -> {next_segment_index}", angle))
    return angles


def test_beastmaker_smooth_paths_keep_straight_curve_joins_tangent_continuous():
    """A visible corner at a display-path join breaks the product illustration."""
    template = get_product_template("beastmaker-1000")
    assert template.display_outline_path is not None
    paths = [("outline", template.display_outline_path)]
    paths.extend((region.id, region.display_path) for region in template.regions)
    assert len(paths) == 23

    violations = []
    for name, path in paths:
        assert path is not None
        angles = _straight_curve_join_angles(path.data)
        assert angles, f"{name} has no straight/curve joins to audit"
        # Integer control points produce an audited maximum of 3.9 degrees.
        violations.extend(
            (name, join, angle)
            for join, angle in angles
            if angle > 4.0
        )

    assert not violations, violations


def test_beastmaker_1000_pockets_have_exact_official_category_metadata():
    """Every official pocket category must map to the correct stable physical IDs."""
    template = get_product_template("beastmaker-1000")
    pocket_metadata = {
        region.id: dict(region.metadata)
        for region in template.regions
        if region.type == "pocket"
    }
    expected = {
        "pocket-top-outer-left": {},
        "pocket-top-outer-right": {},
        "pocket-top-left": {"depthClass": "small", "depthMm": 10, "fingerCount": 4},
        "pocket-top-right": {"depthClass": "small", "depthMm": 10, "fingerCount": 4},
        "pocket-middle-outer-left": {"depthClass": "deep", "fingerCount": 4},
        "pocket-middle-outer-right": {"depthClass": "deep", "fingerCount": 4},
        "pocket-middle-mid-left": {"depthClass": "deep", "fingerCount": 2},
        "pocket-middle-mid-right": {"depthClass": "deep", "fingerCount": 2},
        "pocket-middle-inner-left": {"depthClass": "deep", "fingerCount": 3},
        "pocket-middle-inner-right": {"depthClass": "deep", "fingerCount": 3},
        "pocket-middle-center": {"depthClass": "very-deep", "fingerCount": 4},
        "pocket-bottom-outer-left": {"depthClass": "medium", "fingerCount": 4},
        "pocket-bottom-outer-right": {"depthClass": "medium", "fingerCount": 4},
        "pocket-bottom-mid-left": {"depthClass": "medium", "fingerCount": 2},
        "pocket-bottom-mid-right": {"depthClass": "medium", "fingerCount": 2},
        "pocket-bottom-inner-left": {"depthClass": "medium", "fingerCount": 3},
        "pocket-bottom-inner-right": {"depthClass": "medium", "fingerCount": 3},
    }

    assert pocket_metadata == expected
    categorized = [item for item in pocket_metadata.values() if item]
    assert Counter(item["depthClass"] for item in categorized) == {
        "small": 2,
        "deep": 6,
        "very-deep": 1,
        "medium": 6,
    }
    assert Counter(item["fingerCount"] for item in categorized) == {
        2: 4,
        3: 4,
        4: 7,
    }
    assert {
        region_id for region_id, item in pocket_metadata.items() if "depthMm" in item
    } == {"pocket-top-left", "pocket-top-right"}
