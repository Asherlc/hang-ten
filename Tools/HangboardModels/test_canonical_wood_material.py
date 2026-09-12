#!/usr/bin/env python3
"""Actual-USDZ regression for the canonical wood material contract.

Run with Blender because material bindings are only meaningful after a clean
USDZ reimport:
  rtk proxy blender --background --factory-startup --python-exit-code 1 \
    --python Tools/HangboardModels/test_canonical_wood_material.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

_SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(_SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIRECTORY))

import bpy

from canonical_wood_color import (
    assert_light_neutral_wood_srgb,
    assert_standard_srgb_png_profile,
    png_dimensions,
    srgb_color_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_NAME = "canonical-neutral-wood.png"
CANONICAL_WOOD_MODEL_SLUGS = frozenset(
    {"beastmaker-1000", "metolius-wood-grips-compact-ii"}
)


def model_packages() -> tuple[tuple[str, Path], ...]:
    """Discover every shipped model package from its actual board media."""
    packages: list[tuple[str, Path]] = []
    for board_path in sorted((ROOT / "Hangboards").glob("*/board.json")):
        document = json.loads(board_path.read_text(encoding="utf-8"))
        for presentation in document.get("presentations", []):
            media = presentation.get("media", {})
            if media.get("type") == "model":
                packages.append((board_path.parent.name, board_path.parent / media["assetPath"]))
    return tuple(packages)


def embedded_pngs(model_path: Path) -> tuple[tuple[str, bytes], ...]:
    with zipfile.ZipFile(model_path) as archive:
        return tuple(
            (member, archive.read(member))
            for member in archive.namelist()
            if member.lower().endswith(".png")
        )


def assert_clean_import_has_usable_image_materials(model_path: Path, *, require_image: bool = True) -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    result = bpy.ops.wm.usd_import(filepath=str(model_path), merge_parent_xform=True)
    if "FINISHED" not in result:
        raise AssertionError(f"USDZ import failed: {model_path}")
    meshes = [item for item in bpy.context.scene.objects if item.type == "MESH"]
    if not meshes:
        raise AssertionError(f"USDZ import has no meshes: {model_path}")
    for item in meshes:
        used_indexes = {polygon.material_index for polygon in item.data.polygons}
        if not used_indexes:
            raise AssertionError(f"mesh has no material-bearing faces: {item.name}")
        for index in used_indexes:
            material = item.data.materials[index] if index < len(item.data.materials) else None
            if material is None or material.node_tree is None:
                raise AssertionError(f"mesh is materialless: {item.name}")
            images = [
                node.image
                for node in material.node_tree.nodes
                if node.type == "TEX_IMAGE" and node.image is not None
            ]
            if require_image and not images:
                raise AssertionError(f"mesh lacks image material: {item.name}")
            for image in images:
                _ = image.pixels[0]
                if not image.has_data or min(image.size) <= 0:
                    raise AssertionError(f"mesh has unusable image material: {item.name}")


all_packages = model_packages()
# The canonical-wood contract applies to these authored wood models. Imported
# mixed-material boards and Flash retain their separately reviewed materials.
packages = tuple(item for item in all_packages if item[0] in CANONICAL_WOOD_MODEL_SLUGS)
assert {slug for slug, _ in packages} == CANONICAL_WOOD_MODEL_SLUGS, all_packages
images_by_slug = {slug: embedded_pngs(model_path) for slug, model_path in packages}
assert all(images_by_slug.values()), "every shipped model USDZ must embed an image"
payloads = [payload for images in images_by_slug.values() for _, payload in images]
assert len({hashlib.sha256(payload).digest() for payload in payloads}) == 1, (
    "shipped wood USDZs embed different texture bytes",
    {slug: [(name, hashlib.sha256(payload).hexdigest()) for name, payload in images]
     for slug, images in images_by_slug.items()},
)
names = {Path(name).name for images in images_by_slug.values() for name, _ in images}
assert names == {CANONICAL_NAME}, names
canonical_path = ROOT / "Tools/HangboardModels/assets" / CANONICAL_NAME
canonical_bytes = canonical_path.read_bytes()
assert payloads[0] == canonical_bytes, "USDZ must embed the committed canonical source bytes"
assert_standard_srgb_png_profile(canonical_bytes)
for payload in payloads:
    assert_standard_srgb_png_profile(payload)
assert png_dimensions(canonical_bytes)[0] >= 1024
assert_light_neutral_wood_srgb(srgb_color_evidence(canonical_bytes))
for slug, model_path in all_packages:
    assert_clean_import_has_usable_image_materials(model_path, require_image=slug in CANONICAL_WOOD_MODEL_SLUGS)

print(
    "CANONICAL_WOOD_MATERIAL_TEST passed",
    json.dumps(
        {
            "packages": [slug for slug, _ in packages],
            "textureSHA256": hashlib.sha256(canonical_bytes).hexdigest(),
            "dimensions": png_dimensions(canonical_bytes),
        },
        sort_keys=True,
    ),
)
