#!/usr/bin/env python3
"""Remove primary-image backdrops with the pinned rembg U-2-Net model."""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

from PIL import Image


DEFAULT_MODEL_NAME = "u2net"
MODEL_IDENTIFIER = f"rembg.{DEFAULT_MODEL_NAME}"
DEFAULT_MODEL_ROOT = Path(".context/hangboard-rembg-models")


class SegmentationResult(NamedTuple):
    model_identifier: str
    transparent_pixels: int
    opaque_pixels: int


def _rembg_session(model_name: str, model_root: Path) -> Any:
    """Create one rembg session and keep its downloaded model in the workspace."""
    model_root.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(model_root.resolve())
    try:
        from rembg import new_session
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "rembg is required; install Tools/HangboardPackages[backdrop] first"
        ) from error
    return new_session(model_name)


def _remove_background(source: Image.Image, *, session: Any) -> Image.Image:
    """Return rembg's mask only, so output RGB samples always come from *source*."""
    from rembg import remove

    mask = remove(
        source.convert("RGB"),
        session=session,
        only_mask=True,
        post_process_mask=False,
    )
    if not isinstance(mask, Image.Image):
        raise ValueError("rembg did not return a PIL mask")
    return mask


def process_png(
    path: Path,
    *,
    model_name: str = DEFAULT_MODEL_NAME,
    model_root: Path = DEFAULT_MODEL_ROOT,
    session: Any | None = None,
) -> SegmentationResult:
    """Segment one PNG in place without changing dimensions or RGB samples."""
    path = Path(path)
    model_root = Path(model_root)
    if session is None:
        session = _rembg_session(model_name, model_root)

    output_path: Path | None = None
    try:
        with Image.open(path) as source_image:
            source = source_image.convert("RGBA")
            mask = _remove_background(source, session=session).convert("L")
            if mask.size != source.size:
                raise ValueError(
                    f"rembg mask size {mask.size} does not match source {source.size}"
                )
            source.putalpha(mask)
            histogram = mask.histogram()
            transparent_pixels = histogram[0]
            opaque_pixels = sum(histogram[1:])
            if transparent_pixels == 0 or opaque_pixels == 0:
                raise ValueError(f"rembg did not separate foreground and background for {path}")

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
        if output_path is not None:
            output_path.unlink(missing_ok=True)

    return SegmentationResult(
        model_identifier=f"rembg.{model_name}",
        transparent_pixels=transparent_pixels,
        opaque_pixels=opaque_pixels,
    )


def _primary_assets(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("*/assets/primary.png")))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("Hangboards"))
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--model-root", type=Path, default=DEFAULT_MODEL_ROOT)
    args = parser.parse_args(argv)
    assets = _primary_assets(args.root)
    if not assets:
        parser.error(f"no primary PNGs found beneath {args.root}")
    session = _rembg_session(args.model_name, args.model_root)
    for path in assets:
        result = process_png(
            path,
            model_name=args.model_name,
            model_root=args.model_root,
            session=session,
        )
        print(
            f"segmented: {path} "
            f"({result.transparent_pixels} transparent, "
            f"{result.opaque_pixels} retained)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
