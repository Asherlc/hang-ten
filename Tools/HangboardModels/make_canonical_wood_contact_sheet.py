#!/usr/bin/env python3
"""Create the compact contact sheet for canonical wood review renders."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--directory", type=Path, required=True)
args = parser.parse_args()
directory = args.directory.resolve()
entries = (
    ("Beastmaker 1000 — front", "beastmaker-1000-front.png"),
    ("Beastmaker 1000 — oblique", "beastmaker-1000-oblique.png"),
    ("Compact II — front", "metolius-wood-grips-compact-ii-front.png"),
    ("Compact II — oblique", "metolius-wood-grips-compact-ii-oblique.png"),
)
tiles = [Image.open(directory / filename).convert("RGB").resize((600, 350)) for _, filename in entries]
sheet = Image.new("RGB", (1200, 760), "#10131a")
draw = ImageDraw.Draw(sheet)
for index, ((label, _), tile) in enumerate(zip(entries, tiles)):
    x, y = (index % 2) * 600, (index // 2) * 380
    sheet.paste(tile, (x, y + 30))
    draw.text((x + 14, y + 8), label, fill="#f1f0ea")
sheet.save(directory / "canonical-wood-contact-sheet.png")
