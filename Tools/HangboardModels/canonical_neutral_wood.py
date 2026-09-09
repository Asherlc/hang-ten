#!/usr/bin/env python3
"""Deterministic v3 source and Blender binding helpers for shipped wood models.

The committed PNG is intentionally generic: a light neutral wood field with
fine, low-contrast directional grain. It does not claim a wood species or copy
manufacturer imagery. Its encoded pixels are explicitly declared as standard
sRGB with the matching transfer and chromaticity PNG chunks so every consumer
receives the same color semantics. Regenerate only with:

  rtk python3 -B Tools/HangboardModels/canonical_neutral_wood.py
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import struct
import zlib


TOOLS = Path(__file__).resolve().parent
CANONICAL_TEXTURE_NAME = "canonical-neutral-wood.png"
CANONICAL_TEXTURE_PATH = TOOLS / "assets" / CANONICAL_TEXTURE_NAME
WIDTH = HEIGHT = 2048
GENERATOR_VERSION = "2026-09-09-light-neutral-wood-v5-scene-kit-calibrated"
SRGB_RENDERING_INTENT = 0
SRGB_GAMMA = 45455
SRGB_CHROMATICITIES = (
    31270,
    32900,
    64000,
    33000,
    30000,
    60000,
    15000,
    6000,
)


def _row(y: int) -> bytes:
    """One deterministic sRGB row; grain runs in the image's vertical axis."""
    v = y / (HEIGHT - 1)
    pixels = bytearray(WIDTH * 3)
    for x in range(WIDTH):
        u = x / (WIDTH - 1)
        warp = u + 0.005 * math.sin(v * 13.0) + 0.002 * math.sin(v * 37.0 + u * 11.0)
        broad = 8.0 * math.sin(warp * 58.0 + 1.4 * math.sin(v * 3.0))
        fine = 3.2 * math.sin(warp * 710.0 + v * 14.0)
        pores = -3.0 * max(0.0, math.sin(warp * 1480.0 + v * 5.0)) ** 14
        drift = 1.1 * math.sin(v * 7.0 + u * 2.0)
        shade = broad + fine + pores + drift
        offset = x * 3
        pixels[offset : offset + 3] = bytes(
            max(0, min(255, round(channel + shade)))
            for channel in (210, 196, 173)
        )
    return bytes(pixels)


def generate(path: Path = CANONICAL_TEXTURE_PATH) -> str:
    """Write the canonical source PNG and return its SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    compressor = zlib.compressobj(level=9)
    compressed = bytearray()
    for y in range(HEIGHT):
        compressed.extend(compressor.compress(b"\0" + _row(y)))
    compressed.extend(compressor.flush())
    png = b"".join(
        (
            b"\x89PNG\r\n\x1a\n",
            _chunk(b"IHDR", struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)),
            _chunk(b"sRGB", bytes((SRGB_RENDERING_INTENT,))),
            _chunk(b"gAMA", struct.pack(">I", SRGB_GAMMA)),
            _chunk(b"cHRM", struct.pack(">8I", *SRGB_CHROMATICITIES)),
            _chunk(b"IDAT", bytes(compressed)),
            _chunk(b"IEND", b""),
        )
    )
    path.write_bytes(png)
    return hashlib.sha256(png).hexdigest()


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def load_packed_image():
    """Load precisely the committed source file for a self-contained USDZ."""
    import bpy

    if not CANONICAL_TEXTURE_PATH.is_file():
        raise ValueError(f"missing canonical wood source: {CANONICAL_TEXTURE_PATH}")
    image = bpy.data.images.load(str(CANONICAL_TEXTURE_PATH), check_existing=False)
    if tuple(image.size) != (WIDTH, HEIGHT):
        raise ValueError(f"canonical wood source has unexpected dimensions: {image.size}")
    colorspace = getattr(image, "colorspace_settings", None)
    if colorspace is None:
        raise RuntimeError("Blender image has no color-space settings; cannot bind canonical sRGB texture")
    try:
        colorspace.name = "sRGB"
    except (AttributeError, TypeError, ValueError) as error:
        raise RuntimeError("Blender does not provide the required sRGB image color space") from error
    if colorspace.name != "sRGB":
        raise RuntimeError(
            f"Blender did not retain the canonical image sRGB color space: {colorspace.name!r}"
        )
    image.name = CANONICAL_TEXTURE_NAME
    image.pack()
    return image


def attach_to_materials(materials) -> None:
    """Bind each material to one packed canonical image without changing UVs."""
    image = load_packed_image()
    for material in materials:
        material.use_nodes = True
        nodes = material.node_tree.nodes
        links = material.node_tree.links
        for node in list(nodes):
            if node.type == "TEX_IMAGE":
                nodes.remove(node)
        bsdf = nodes.get("Principled BSDF")
        bsdf.inputs["Roughness"].default_value = 0.62
        bsdf.inputs["Specular IOR Level"].default_value = 0.15
        texture = nodes.new("ShaderNodeTexImage")
        texture.name = CANONICAL_TEXTURE_NAME
        texture.image = image
        texture.interpolation = "Linear"
        links.new(texture.outputs["Color"], bsdf.inputs["Base Color"])


if __name__ == "__main__":
    print(
        "CANONICAL_NEUTRAL_WOOD_GENERATED",
        f"version={GENERATOR_VERSION}",
        f"path={CANONICAL_TEXTURE_PATH.relative_to(TOOLS.parents[1])}",
        f"dimensions={WIDTH}x{HEIGHT}",
        f"sha256={generate()}",
    )
