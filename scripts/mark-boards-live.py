#!/usr/bin/env python3
"""Validate migration draft board directories without authoring placeholder live JSON."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        if handle.read(8) != PNG_SIGNATURE:
            raise ValueError(f"not a PNG: {path}")
        while True:
            length_data = handle.read(4)
            if len(length_data) != 4:
                raise ValueError(f"malformed PNG: {path}")
            (length,) = struct.unpack(">I", length_data)
            chunk_type = handle.read(4)
            if len(chunk_type) != 4:
                raise ValueError(f"malformed PNG: {path}")
            data = handle.read(length)
            if len(data) != length:
                raise ValueError(f"malformed PNG: {path}")
            handle.read(4)  # crc
            if chunk_type == b"IHDR":
                if len(data) < 8:
                    raise ValueError(f"malformed PNG: {path}")
                return struct.unpack(">II", data[:8])
            if chunk_type == b"IEND":
                break
    raise ValueError(f"missing PNG header: {path}")


def mark_all_live(hangboards: Path) -> None:
    hangboards = hangboards.resolve()
    for child in sorted(hangboards.iterdir(), key=lambda path: path.name):
        if not child.is_dir():
            continue
        manifest = child / "board.json"
        if manifest.exists():
            continue
        image = child / "assets" / "primary.png"
        if not image.is_file():
            continue
        width, height = _png_dimensions(image)
        if width <= 0 or height <= 0:
            raise ValueError(f"invalid dimensions for {image}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hangboards", type=Path, default=Path("Hangboards"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mark_all_live(args.hangboards)


if __name__ == "__main__":
    main()
