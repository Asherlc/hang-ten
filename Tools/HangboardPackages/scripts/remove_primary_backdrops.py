#!/usr/bin/env python3
"""Remove primary-image backdrops with the pinned rembg U-2-Net model."""

from __future__ import annotations

import argparse
from collections import deque
from contextlib import contextmanager
import os
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

from PIL import Image


DEFAULT_MODEL_NAME = "u2net"
MODEL_IDENTIFIER = f"rembg.{DEFAULT_MODEL_NAME}"
DEFAULT_MODEL_ROOT = Path(".context/hangboard-rembg-models")
_SESSION_ARTIFACT = ":memory:.ses"
_MAX_ENCLOSED_BACKGROUND_PIXELS = 100_000
_ENCLOSED_BACKGROUND_SEEDS = {
    "tension-grindstone": ((887, 443),),
    "yy-travelboard": ((190, 625), (1348, 625)),
    "yy-verticalboard-evo": ((887, 500),),
    "yy-penta-evo": ((145, 595), (1385, 595), (180, 720), (1355, 720)),
}


class SegmentationResult(NamedTuple):
    model_identifier: str
    transparent_pixels: int
    opaque_pixels: int


@contextmanager
def _rembg_working_directory(model_root: Path):
    """Contain ONNX Runtime's session sidecar outside the repository root."""
    model_root.mkdir(parents=True, exist_ok=True)
    original_directory = Path.cwd()
    original_artifact = original_directory / _SESSION_ARTIFACT
    artifact_was_present = original_artifact.exists()
    try:
        os.chdir(model_root)
        yield
    finally:
        os.chdir(original_directory)
        (model_root / _SESSION_ARTIFACT).unlink(missing_ok=True)
        if not artifact_was_present:
            original_artifact.unlink(missing_ok=True)


def _rembg_session(model_name: str, model_root: Path) -> Any:
    """Create one rembg session and keep its downloaded model in the workspace."""
    model_root.mkdir(parents=True, exist_ok=True)
    os.environ["U2NET_HOME"] = str(model_root.resolve())
    os.environ["ORT_DISABLE_TELEMETRY"] = "1"
    try:
        from rembg import new_session
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "rembg is required; install Tools/HangboardPackages[backdrop] first"
        ) from error
    with _rembg_working_directory(model_root):
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


def _clear_known_enclosed_backgrounds(
    source: Image.Image, mask: Image.Image, package_name: str
) -> Image.Image:
    """Clear only reviewed, source-color-connected through-hole backgrounds.

    U-2-Net occasionally retains a white background enclosed by a board.  These
    seeds were reviewed against the source photos; each flood fill is bounded by
    its own RGB sample, so it cannot remove shaded wood, ropes, lettering, or a
    disconnected board surface.
    """
    seeds = _ENCLOSED_BACKGROUND_SEEDS.get(package_name, ())
    if not seeds:
        return mask
    rgb_source = source.convert("RGB")
    pixels = rgb_source.load()
    alpha = bytearray(mask.convert("L").tobytes())
    width, height = source.size
    for seed_x, seed_y in seeds:
        if not 0 <= seed_x < width or not 0 <= seed_y < height:
            raise ValueError(f"enclosed-background seed is outside {package_name}")
        seed_color = pixels[seed_x, seed_y]
        pending = deque([(seed_x, seed_y)])
        visited: set[tuple[int, int]] = set()
        while pending:
            x, y = pending.popleft()
            if (x, y) in visited:
                continue
            visited.add((x, y))
            offset = y * width + x
            color = pixels[x, y]
            if max(abs(color[index] - seed_color[index]) for index in range(3)) > 12:
                continue
            alpha[offset] = 0
            if len(visited) > _MAX_ENCLOSED_BACKGROUND_PIXELS:
                raise ValueError(f"enclosed-background fill exceeded its limit for {package_name}")
            for neighbor_x, neighbor_y in (
                (x - 1, y),
                (x + 1, y),
                (x, y - 1),
                (x, y + 1),
            ):
                if 0 <= neighbor_x < width and 0 <= neighbor_y < height:
                    pending.append((neighbor_x, neighbor_y))
    return Image.frombytes("L", source.size, bytes(alpha))


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
            with _rembg_working_directory(model_root):
                mask = _remove_background(source, session=session).convert("L")
            if mask.size != source.size:
                raise ValueError(
                    f"rembg mask size {mask.size} does not match source {source.size}"
                )
            mask = _clear_known_enclosed_backgrounds(
                source, mask, path.parent.parent.name
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
