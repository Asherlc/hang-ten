#!/usr/bin/env python3
"""Mark migration draft board directories as live by authoring placeholder board JSON."""

from __future__ import annotations

import argparse
import json
import math
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


def _slug_to_title(slug: str) -> str:
    return " ".join(part.capitalize() for part in slug.split("-"))


def _manifest_for_slug(slug: str, width: int, height: int) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "id": slug,
        "manufacturer": "Draft Board",
        "name": _slug_to_title(slug),
        "subtitle": "Marked live from migration draft metadata.",
        "productURL": f"https://example.com/{slug}",
        "dimensions": "Unknown",
        "aspectRatio": width / height,
        "presentation": {
            "assetPath": "assets/primary.png",
        },
        "holds": [
            {
                "id": "placeholder",
                "name": "Placeholder hold",
                "kind": "sloper",
                "geometry": [
                    {
                        "frame": {
                            "x": 0.0,
                            "y": 0.0,
                            "width": 1.0,
                            "height": 1.0,
                        },
                        "shape": {
                            "type": "roundedRect",
                            "cornerRadiusFraction": 0.0,
                        },
                    }
                ],
            }
        ],
    }


def mark_all_live(hangboards: Path) -> list[str]:
    hangboards = hangboards.resolve()
    created: list[str] = []
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
        if not math.isfinite(width / height):
            raise ValueError(f"invalid dimensions for {image}")
        manifest.write_text(
            json.dumps(_manifest_for_slug(child.name, width, height), indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
        created.append(child.name)
    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hangboards", type=Path, default=Path("Hangboards"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    created = mark_all_live(args.hangboards)
    for slug in created:
        print(slug)


if __name__ == "__main__":
    main()
