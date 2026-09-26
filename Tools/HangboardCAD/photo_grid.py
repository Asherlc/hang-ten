"""Reading aids for authoring a board's front view from a manufacturer photo.

A diagnostic, never a build input, and never a geometry source by itself: the
operator reads coordinates off the gridded crops by eye and types them into the
authoring script. Nothing here detects, segments, traces, fits or registers
anything (see AGENTS.md). The scale and origin are the operator's own
measurement of a known feature lying in the photo's plane, and belong in the
board's provenance record.

    # 1 mm-gridded, contrast-stretched crop of a region (photo frame, mm)
    python Tools/HangboardCAD/photo_grid.py crop PHOTO --scale 3.82 --origin 473 925.5 \
        --region 40 105 -50 -2 --out crop.png [--mark 64.8,-9 75,-18.2]

    # the compiled model's front view blended over the photo at the same scale
    python Tools/HangboardCAD/photo_grid.py overlay PHOTO --scale 3.82 --origin 473 925.5 \
        --package <slug> --shift 3.35 13.55 --out overlay.png

`--scale` is photo pixels per millimetre and `--origin` is the photo pixel of
the frame origin. Photo-frame X runs right and Z runs up. `--shift` is the
native position of the photo origin (native = photo + shift), as used by the
authoring script. Run it with a host venv that has numpy, pillow and usd-core.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

REPOSITORY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def _pixel(args, x, z):
    return args.origin[0] + x * args.scale, args.origin[1] - z * args.scale


def crop(args) -> None:
    x0, x1, z0, z1 = args.region
    photo = Image.open(args.photo).convert("RGB")
    left, top = (round(v) for v in _pixel(args, x0, z1))
    right, bottom = (round(v) for v in _pixel(args, x1, z0))
    tile = photo.crop((left, top, right, bottom))
    if not args.no_contrast:
        tile = ImageOps.autocontrast(tile, cutoff=1)
    zoom = min(args.width / tile.width, args.height / tile.height)
    tile = tile.resize((round(tile.width * zoom), round(tile.height * zoom)), Image.LANCZOS)
    draw = ImageDraw.Draw(tile, "RGBA")
    font = ImageFont.load_default()

    def sx(x):
        return (_pixel(args, x, 0)[0] - left) * zoom

    def sy(z):
        return (_pixel(args, 0, z)[1] - top) * zoom

    for gx in range(math.ceil(x0), math.floor(x1) + 1):
        major = gx % 5 == 0
        draw.line([(sx(gx), 0), (sx(gx), tile.height)], fill=(255, 0, 0, 200) if major else (0, 170, 255, 90))
        if major:
            draw.text((sx(gx) + 2, 2), str(gx), fill=(255, 0, 0), font=font)
    for gz in range(math.ceil(z0), math.floor(z1) + 1):
        major = gz % 5 == 0
        draw.line([(0, sy(gz)), (tile.width, sy(gz))], fill=(255, 0, 0, 200) if major else (0, 170, 255, 90))
        if major:
            draw.text((2, sy(gz) + 2), str(gz), fill=(255, 0, 0), font=font)
    for mark in args.mark:
        mx, mz = (float(v) for v in mark.split(","))
        draw.ellipse([sx(mx) - 5, sy(mz) - 5, sx(mx) + 5, sy(mz) + 5], outline=(0, 220, 0, 255), width=2)
    tile.save(args.out)
    print(f"wrote {args.out} ({tile.width}x{tile.height}, {zoom * args.scale:.1f} px/mm)")


def overlay(args) -> None:
    from preview import _triangles  # noqa: E402
    from usdz_writer import read_usdz  # noqa: E402

    asset = Path(args.asset) if args.asset else REPOSITORY / "Hangboards" / args.package / "assets/primary.usdz"
    points, normals = _triangles(read_usdz(asset))
    photo_xz = points[:, :, [0, 2]] - np.array(args.shift)  # native -> photo frame
    x0, z0 = photo_xz.reshape(-1, 2).min(axis=0) - args.margin
    x1, z1 = photo_xz.reshape(-1, 2).max(axis=0) + args.margin
    photo = Image.open(args.photo).convert("RGB")
    left, top = (round(v) for v in _pixel(args, x0, z1))
    right, bottom = (round(v) for v in _pixel(args, x1, z0))
    base = photo.crop((left, top, right, bottom))
    render = Image.new("RGB", base.size, (255, 255, 255))
    draw = ImageDraw.Draw(render)
    light = np.array([-0.3, -0.8, 0.5])
    light /= np.linalg.norm(light)
    order = np.argsort(-points[:, :, 1].mean(axis=1))  # back (larger y) first
    for index in order:
        corners = [(_pixel(args, x, z)[0] - left, _pixel(args, x, z)[1] - top) for x, z in photo_xz[index]]
        grey = int(60 + 180 * abs(float(normals[index] @ light)))
        draw.polygon(corners, fill=(grey, grey, int(grey * 0.7 + 60)))
    Image.blend(base, render, args.alpha).save(args.out)
    print(f"wrote {args.out}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("crop", "overlay"):
        p = sub.add_parser(name)
        p.add_argument("photo")
        p.add_argument("--scale", type=float, required=True, help="photo px per mm")
        p.add_argument("--origin", type=float, nargs=2, required=True, metavar=("PX", "PY"))
        p.add_argument("--out", required=True)
    c = sub.choices["crop"]
    c.add_argument("--region", type=float, nargs=4, required=True, metavar=("X0", "X1", "Z0", "Z1"))
    c.add_argument("--mark", nargs="*", default=[], help="x,z points to circle, e.g. authored joints")
    c.add_argument("--no-contrast", action="store_true")
    c.add_argument("--width", type=int, default=1000)
    c.add_argument("--height", type=int, default=760)
    o = sub.choices["overlay"]
    o.add_argument("--package")
    o.add_argument("--asset", help="USDZ path (defaults to the package's primary.usdz)")
    o.add_argument("--shift", type=float, nargs=2, default=(0.0, 0.0), metavar=("DX", "DZ"))
    o.add_argument("--margin", type=float, default=8.0)
    o.add_argument("--alpha", type=float, default=0.45)
    args = parser.parse_args(argv)
    if args.command == "overlay" and not (args.package or args.asset):
        parser.error("overlay needs --package or --asset")
    crop(args) if args.command == "crop" else overlay(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
