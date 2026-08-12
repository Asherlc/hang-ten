from __future__ import annotations

import base64
from collections import Counter
from dataclasses import replace
from io import BytesIO

import cv2
import numpy as np
from PIL import Image
import pytest

import hangboard_vectorizer.product_render as product_render_module
from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.product_render import (
    encode_png_data_url,
    load_render_asset,
    render_product,
)
from hangboard_vectorizer.templates import get_product_template


def test_render_product_has_canonical_shapes_dtypes_and_semantic_masks():
    template = get_product_template("beastmaker-1000")

    result = render_product(template)

    assert result.rgba.shape == (259, 1000, 4)
    assert result.rgba.dtype == np.uint8
    assert result.height.shape == (259, 1000)
    assert result.height.dtype == np.float32
    assert np.isfinite(result.height).all()
    assert -30.0 < float(result.height.min())
    assert float(result.height.max()) < 30.0
    assert result.rgba[0, 0, 3] == 0
    assert result.rgba[-1, -1, 3] == 0
    assert np.count_nonzero(result.rgba[..., 3]) > 0
    assert len(result.masks) == 22
    assert all(mask.shape == (259, 1000) for mask in result.masks.values())
    assert all(mask.dtype == np.bool_ for mask in result.masks.values())


def test_render_product_has_one_continuous_canonical_center_sloper():
    template = get_product_template("beastmaker-1000")
    result = render_product(template)

    assert Counter(region.type for region in template.regions) == {
        "pocket": 17,
        "sloper": 3,
        "jug": 2,
    }
    assert "sloper-center" in result.masks
    assert "sloper-20-left" not in result.masks
    assert "sloper-20-right" not in result.masks
    center = result.masks["sloper-center"]
    component_count, _ = cv2.connectedComponents(center.astype(np.uint8), 8)
    assert component_count == 2
    occupied_rows = np.flatnonzero(center.any(axis=1))
    assert occupied_rows.size > 0
    for row in occupied_rows:
        covered = np.flatnonzero(center[row])
        assert np.all(center[row, covered[0] : covered[-1] + 1])
    assert np.all(center[:, 500].take(occupied_rows))


@pytest.mark.parametrize("legacy_id", ["sloper-20-left", "sloper-20-right"])
def test_render_product_rejects_legacy_split_center_slopers(legacy_id):
    template = get_product_template("beastmaker-1000")
    regions = tuple(
        replace(region, id=legacy_id) if region.id == "sloper-center" else region
        for region in template.regions
    )

    with pytest.raises(ConversionError, match="legacy split-center"):
        render_product(replace(template, regions=regions))


def test_render_product_rejects_noncanonical_beastmaker_sloper_topology():
    template = get_product_template("beastmaker-1000")
    regions = tuple(
        region for region in template.regions if region.id != "sloper-center"
    )

    with pytest.raises(ConversionError, match="three canonical sloper masks"):
        render_product(replace(template, regions=regions))


@pytest.mark.parametrize("region_type", ["pocket", "rail", "edge"])
def test_render_product_rejects_nonrelief_masks_crossing_the_silhouette(
    region_type,
):
    template = get_product_template("beastmaker-1000")
    crossing_path = next(
        region.display_path
        for region in template.regions
        if region.id == "sloper-35-left"
    )
    regions = tuple(
        replace(region, type=region_type, display_path=crossing_path)
        if region.id == "pocket-middle-center"
        else region
        for region in template.regions
    )

    with pytest.raises(ConversionError, match="extends outside"):
        render_product(replace(template, regions=regions))


def test_render_product_is_pixel_deterministic_and_seed_controls_grain():
    template = get_product_template("beastmaker-1000")

    first = render_product(template)
    second = render_product(template)
    assert np.array_equal(first.rgba, second.rgba)
    assert np.array_equal(first.height, second.height)
    assert all(
        np.array_equal(first.masks[key], second.masks[key]) for key in first.masks
    )

    assert template.render_profile is not None
    changed_profile = replace(template.render_profile, seed=template.render_profile.seed + 1)
    changed = render_product(replace(template, render_profile=changed_profile))
    assert not np.array_equal(first.rgba[..., :3], changed.rgba[..., :3])
    assert np.array_equal(first.height, changed.height)


def test_region_cores_match_visible_color_and_height_relief():
    template = get_product_template("beastmaker-1000")
    result = render_product(template)
    visible = result.rgba[..., 3] > 0
    occupied = np.logical_or.reduce(tuple(result.masks.values()))
    luminance = result.rgba[..., :3].astype(np.float32).mean(axis=2)

    assert all(np.all(visible[mask]) for mask in result.masks.values())

    for region in template.regions:
        core, ring = _core_and_face_ring(result.masks[region.id], visible, occupied)
        assert np.any(core), region.id
        assert np.any(ring), region.id
        if region.type == "pocket":
            assert result.height[core].mean() < result.height[ring].mean(), region.id
            assert luminance[core].mean() < luminance[ring].mean(), region.id
        else:
            assert region.type in ("jug", "sloper")
            assert result.height[core].mean() > result.height[ring].mean(), region.id


def test_pocket_cavity_core_is_darker_than_its_surrounding_pale_rim():
    result = render_product(get_product_template("beastmaker-1000"))
    pocket = result.masks["pocket-middle-center"]
    visible = result.rgba[..., 3] > 0
    occupied = np.logical_or.reduce(tuple(result.masks.values()))
    core, face_ring = _core_and_face_ring(pocket, visible, occupied)
    inner_rim = pocket & ~cv2.erode(
        pocket.astype(np.uint8), np.ones((9, 9), dtype=np.uint8)
    ).astype(bool)
    luminance = result.rgba[..., :3].astype(np.float32).mean(axis=2)

    assert np.any(core)
    assert np.any(inner_rim)
    assert np.any(face_ring)
    assert luminance[core].mean() < luminance[inner_rim].mean()
    assert luminance[core].mean() < luminance[face_ring].mean()


def test_png_data_url_is_deterministic_and_decodes_as_rgba():
    rgba = render_product(get_product_template("beastmaker-1000")).rgba

    first = encode_png_data_url(rgba)
    second = encode_png_data_url(rgba)

    assert first == second
    assert first.startswith("data:image/png;base64,")
    payload = base64.b64decode(first.partition(",")[2])
    with Image.open(BytesIO(payload)) as image:
        assert image.mode == "RGBA"
        assert image.size == (1000, 259)
        assert np.array_equal(np.asarray(image), rgba)


@pytest.mark.parametrize(
    "unsafe_name",
    ["../outside.png", "nested/render.png", "render.jpg", "render image.png"],
)
def test_load_render_asset_rejects_unsafe_replaced_names_before_resource_access(
    unsafe_name,
    monkeypatch,
):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset=unsafe_name,
    )

    def unexpected_resource_access(_package):
        raise AssertionError("unsafe name reached importlib.resources")

    monkeypatch.setattr(
        product_render_module.resources,
        "files",
        unexpected_resource_access,
    )

    with pytest.raises(ConversionError, match="safe PNG filename"):
        load_render_asset(template)


def test_load_render_asset_rejects_missing_resource(tmp_path, monkeypatch):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset="missing-render.png",
    )
    monkeypatch.setattr(product_render_module.resources, "files", lambda _: tmp_path)

    with pytest.raises(ConversionError, match="could not load renderAsset"):
        load_render_asset(template)


def test_load_render_asset_rejects_malformed_image_bytes(tmp_path, monkeypatch):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset="malformed-render.png",
    )
    (tmp_path / "malformed-render.png").write_bytes(b"not an image")
    monkeypatch.setattr(product_render_module.resources, "files", lambda _: tmp_path)

    with pytest.raises(ConversionError, match="could not load renderAsset"):
        load_render_asset(template)


def test_load_render_asset_rejects_non_png_image_bytes(tmp_path, monkeypatch):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset="jpeg-render.png",
    )
    Image.new("RGB", (1000, 259)).save(
        tmp_path / "jpeg-render.png",
        format="JPEG",
    )
    monkeypatch.setattr(product_render_module.resources, "files", lambda _: tmp_path)

    with pytest.raises(ConversionError, match="must decode as PNG"):
        load_render_asset(template)


def test_load_render_asset_rejects_rgb_png(tmp_path, monkeypatch):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset="rgb-render.png",
    )
    Image.new("RGB", (1000, 259)).save(tmp_path / "rgb-render.png")
    monkeypatch.setattr(product_render_module.resources, "files", lambda _: tmp_path)

    with pytest.raises(ConversionError, match="must decode as RGBA"):
        load_render_asset(template)


def test_load_render_asset_rejects_noncanonical_dimensions(tmp_path, monkeypatch):
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset="wrong-size-render.png",
    )
    Image.new("RGBA", (999, 259)).save(tmp_path / "wrong-size-render.png")
    monkeypatch.setattr(product_render_module.resources, "files", lambda _: tmp_path)

    with pytest.raises(ConversionError, match="must match canonicalViewBox"):
        load_render_asset(template)


def test_load_render_asset_accepts_asset_without_profile():
    template = replace(
        get_product_template("beastmaker-1000"),
        render_profile=None,
    )

    png_bytes = load_render_asset(template)

    with Image.open(BytesIO(png_bytes)) as image:
        assert image.mode == "RGBA"
        assert image.size == (1000, 259)


def test_render_product_accepts_profile_without_asset():
    template = replace(
        get_product_template("beastmaker-1000"),
        render_asset=None,
    )

    result = render_product(template)

    assert result.rgba.shape == (259, 1000, 4)
    assert len(result.masks) == 22


def _core_and_face_ring(
    mask: np.ndarray, visible: np.ndarray, occupied: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    kernel = np.ones((9, 9), dtype=np.uint8)
    core = cv2.erode(mask.astype(np.uint8), kernel).astype(bool)
    ring = (
        cv2.dilate(mask.astype(np.uint8), kernel).astype(bool)
        & ~occupied
        & visible
    )
    return core, ring
