"""Encoded-sRGB audit helpers for the committed canonical wood PNG."""

from __future__ import annotations

import struct
import zlib


STANDARD_SRGB_RENDERING_INTENT = 0
STANDARD_SRGB_GAMMA = 45455
STANDARD_SRGB_CHROMATICITIES = (
    31270,
    32900,
    64000,
    33000,
    30000,
    60000,
    15000,
    6000,
)


def assert_standard_srgb_png_profile(payload: bytes) -> None:
    """Require a self-contained, standard-sRGB PNG color declaration."""
    png_dimensions(payload)
    cursor = 8
    chunks: list[tuple[bytes, bytes]] = []
    while cursor < len(payload):
        if cursor + 12 > len(payload):
            raise AssertionError("canonical texture has a truncated PNG chunk")
        length = struct.unpack(">I", payload[cursor : cursor + 4])[0]
        end = cursor + length + 12
        if end > len(payload):
            raise AssertionError("canonical texture has a truncated PNG chunk payload")
        kind = payload[cursor + 4 : cursor + 8]
        chunk = payload[cursor + 8 : cursor + 8 + length]
        expected_crc = struct.unpack(">I", payload[cursor + 8 + length : end])[0]
        actual_crc = zlib.crc32(kind + chunk) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise AssertionError(f"canonical texture has an invalid {kind!r} CRC")
        chunks.append((kind, chunk))
        cursor = end
        if kind == b"IEND":
            break
    if cursor != len(payload):
        raise AssertionError("canonical texture has bytes after IEND")

    kinds = [kind for kind, _ in chunks]
    if not kinds or kinds[0] != b"IHDR" or kinds[-1] != b"IEND":
        raise AssertionError("canonical texture must have ordered IHDR/IEND chunks")
    try:
        idat_index = kinds.index(b"IDAT")
    except ValueError as error:
        raise AssertionError("canonical texture must contain IDAT") from error

    expected = {
        b"sRGB": bytes((STANDARD_SRGB_RENDERING_INTENT,)),
        b"gAMA": struct.pack(">I", STANDARD_SRGB_GAMMA),
        b"cHRM": struct.pack(">8I", *STANDARD_SRGB_CHROMATICITIES),
    }
    for kind, expected_payload in expected.items():
        indexes = [index for index, (actual_kind, _) in enumerate(chunks) if actual_kind == kind]
        if len(indexes) != 1:
            raise AssertionError(f"canonical texture must contain exactly one {kind.decode()} chunk")
        index = indexes[0]
        if not 0 < index < idat_index:
            raise AssertionError(f"canonical texture {kind.decode()} chunk must precede IDAT")
        if chunks[index][1] != expected_payload:
            raise AssertionError(f"canonical texture has nonstandard {kind.decode()} metadata")


def png_dimensions(payload: bytes) -> tuple[int, int]:
    if payload[:8] != b"\x89PNG\r\n\x1a\n" or payload[12:16] != b"IHDR":
        raise AssertionError("canonical texture must be a PNG with IHDR")
    width, height = struct.unpack(">II", payload[16:24])
    if width <= 0 or height <= 0:
        raise AssertionError("canonical texture must have positive dimensions")
    return width, height


def srgb_color_evidence(payload: bytes) -> tuple[float, float, float, float]:
    """Sample encoded RGB bytes, not a renderer's color-managed pixel buffer."""
    width, height = png_dimensions(payload)
    cursor = 8
    compressed = bytearray()
    while cursor < len(payload):
        length = struct.unpack(">I", payload[cursor : cursor + 4])[0]
        kind = payload[cursor + 4 : cursor + 8]
        chunk = payload[cursor + 8 : cursor + 8 + length]
        cursor += length + 12
        if kind == b"IHDR":
            # The deterministic generator uses auditable RGB/8 non-interlaced
            # scanlines, all with filter type 0.
            assert chunk[8:13] == bytes((8, 2, 0, 0, 0)), chunk[8:13]
        elif kind == b"IDAT":
            compressed.extend(chunk)
        elif kind == b"IEND":
            break
    rows = zlib.decompress(compressed)
    stride = width * 3 + 1
    assert len(rows) == height * stride, (len(rows), width, height)
    row_indexes = range(16, height, max(1, height // 48))
    column_indexes = range(16, width, max(1, width // 48))
    assert all(rows[row * stride] == 0 for row in row_indexes)
    samples = [
        tuple(rows[row * stride + 1 + column * 3 : row * stride + 4 + column * 3])
        for row in row_indexes
        for column in column_indexes
    ]
    assert samples
    red = sum(pixel[0] for pixel in samples) / len(samples) / 255
    green = sum(pixel[1] for pixel in samples) / len(samples) / 255
    blue = sum(pixel[2] for pixel in samples) / len(samples) / 255
    grain_range = (max(sum(pixel) / 3 for pixel in samples) - min(sum(pixel) / 3 for pixel in samples)) / 255
    return red, green, blue, grain_range


def assert_light_neutral_wood_srgb(evidence: tuple[float, float, float, float]) -> None:
    """Reject white/high-albedo and non-neutral encoded wood color evidence."""
    red, green, blue, grain_range = evidence
    assert 0.70 <= (red + green + blue) / 3 <= 0.82, (
        "canonical wood encoded sRGB must remain light beige/tan rather than dark or white",
        evidence,
    )
    assert red > green > blue and red - blue < 0.18, evidence
    assert 0.012 <= grain_range <= 0.12, grain_range
