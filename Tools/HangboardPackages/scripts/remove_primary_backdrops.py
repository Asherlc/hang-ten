#!/usr/bin/env python3
"""Remove primary-image backdrops with Apple's foreground instance segmenter."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path
from typing import NamedTuple

from PIL import Image


MODEL_IDENTIFIER = "Vision.VNGenerateForegroundInstanceMaskRequest"
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
VISION_SOURCE = SCRIPT_DIRECTORY / "vision_foreground_mask.swift"
DEFAULT_BUILD_ROOT = Path(".context/hangboard-vision-segmentation")


class SegmentationResult(NamedTuple):
    model_identifier: str
    transparent_pixels: int
    opaque_pixels: int


def _vision_binary(build_root: Path) -> Path:
    build_root.mkdir(parents=True, exist_ok=True)
    binary = build_root / "vision-foreground-mask"
    if binary.is_file() and binary.stat().st_mtime_ns >= VISION_SOURCE.stat().st_mtime_ns:
        return binary
    module_cache = build_root / "module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["CLANG_MODULE_CACHE_PATH"] = str(module_cache)
    environment["SWIFT_MODULECACHE_PATH"] = str(module_cache)
    subprocess.run(
        [
            "xcrun",
            "swiftc",
            "-O",
            "-framework",
            "Vision",
            "-framework",
            "CoreImage",
            "-framework",
            "CoreML",
            str(VISION_SOURCE),
            "-o",
            str(binary),
        ],
        check=True,
        env=environment,
    )
    return binary


def _generate_mask(source: Path, destination: Path, *, build_root: Path) -> None:
    subprocess.run(
        [str(_vision_binary(build_root)), str(source), str(destination)],
        check=True,
    )


def process_png(
    path: Path, *, build_root: Path = DEFAULT_BUILD_ROOT
) -> SegmentationResult:
    """Segment one PNG in place without changing its dimensions or RGB samples."""
    path = Path(path)
    build_root = Path(build_root)
    with Image.open(path) as existing_image:
        existing_alpha = existing_image.convert("RGBA").getchannel("A").histogram()
    if existing_alpha[0] > 0:
        return SegmentationResult(
            model_identifier="existing-alpha",
            transparent_pixels=existing_alpha[0],
            opaque_pixels=sum(existing_alpha[1:]),
        )

    mask_path: Path | None = None
    output_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".mask.png",
            delete=False,
        ) as temporary:
            mask_path = Path(temporary.name)
        _generate_mask(path, mask_path, build_root=build_root)

        with Image.open(path) as source_image, Image.open(mask_path) as mask_image:
            source = source_image.convert("RGBA")
            mask = mask_image.convert("L")
            if mask.size != source.size:
                raise ValueError(
                    f"Vision mask size {mask.size} does not match source {source.size}"
                )
            source.putalpha(mask)
            alpha = source.getchannel("A")
            histogram = alpha.histogram()
            transparent_pixels = histogram[0]
            opaque_pixels = sum(histogram[1:])
            if transparent_pixels == 0 or opaque_pixels == 0:
                raise ValueError(
                    f"Vision did not separate foreground and background for {path}"
                )

            with tempfile.NamedTemporaryFile(
                dir=path.parent,
                prefix=f".{path.name}.",
                suffix=".output.png",
                delete=False,
            ) as temporary:
                output_path = Path(temporary.name)
            source.save(output_path, format="PNG", compress_level=9, optimize=False)
        os.replace(output_path, path)
        output_path = None
    finally:
        if mask_path is not None:
            mask_path.unlink(missing_ok=True)
        if output_path is not None:
            output_path.unlink(missing_ok=True)

    return SegmentationResult(
        model_identifier=MODEL_IDENTIFIER,
        transparent_pixels=transparent_pixels,
        opaque_pixels=opaque_pixels,
    )


def _primary_assets(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("*/assets/primary.png")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("Hangboards"))
    parser.add_argument("--build-root", type=Path, default=DEFAULT_BUILD_ROOT)
    args = parser.parse_args(argv)
    assets = _primary_assets(args.root)
    if not assets:
        parser.error(f"no primary PNGs found beneath {args.root}")
    for path in assets:
        result = process_png(path, build_root=args.build_root)
        print(
            f"segmented: {path} "
            f"({result.transparent_pixels} transparent, "
            f"{result.opaque_pixels} retained)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
