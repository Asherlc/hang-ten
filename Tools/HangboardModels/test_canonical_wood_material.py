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
import struct
import zipfile

import bpy


ROOT = Path(__file__).resolve().parents[2]
CANONICAL_NAME = "canonical-neutral-wood.png"
EXPECTED_MODEL_SLUGS = frozenset(
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


def png_dimensions(payload: bytes) -> tuple[int, int]:
    if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise AssertionError("embedded canonical texture must be a PNG with IHDR")
    width, height = struct.unpack(">II", payload[16:24])
    if width <= 0 or height <= 0:
        raise AssertionError("embedded canonical texture must have positive dimensions")
    return width, height


def assert_clean_import_has_usable_image_materials(model_path: Path) -> None:
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
            if not images:
                raise AssertionError(f"mesh lacks image material: {item.name}")
            for image in images:
                _ = image.pixels[0]
                if not image.has_data or min(image.size) <= 0:
                    raise AssertionError(f"mesh has unusable image material: {item.name}")


packages = model_packages()
assert {slug for slug, _ in packages} == EXPECTED_MODEL_SLUGS, packages
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
assert png_dimensions(canonical_bytes)[0] >= 1024
for _, model_path in packages:
    assert_clean_import_has_usable_image_materials(model_path)

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
