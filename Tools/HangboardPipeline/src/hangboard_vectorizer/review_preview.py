"""Render deterministic review previews and self-contained comparison HTML."""

from __future__ import annotations

from base64 import b64encode
from collections.abc import Iterable, Mapping
from html import escape
from io import BytesIO
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
from uuid import uuid4

from PIL import Image, ImageDraw

from .review_artifacts import ReviewRun, load_json, sha256_file

_TYPE_COLORS = {
    "jug": "#ff754f",
    "sloper": "#32bbc1",
    "edge": "#9a6cf2",
    "pocket": "#ee4d97",
}
_TYPE_ORDER = ("jug", "sloper", "edge", "pocket")


def render_preview_bundle(run: ReviewRun, output: Path) -> dict[str, object]:
    """Write one deterministic preview bundle below *output*."""
    stage1 = _load_stage1_image(run.stage1_image)
    automatic = _load_regions_document(run.stage2_regions, "stage-2 baseline")
    edited = _load_regions_document(
        run.edited_regions or run.stage2_regions,
        "stage-2 edited regions" if run.edited_regions is not None else "stage-2 baseline",
    )

    root = output.resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    target = root / "review-preview"
    temporary_root = Path(tempfile.mkdtemp(prefix=".review-preview.tmp-", dir=root))
    bundle = temporary_root / "review-preview"
    bundle.mkdir()
    try:
        _save_png(bundle / "normal.png", stage1)
        _save_png(bundle / "automatic.png", _overlay_preview(stage1, automatic["regions"]))
        _save_png(bundle / "edited.png", _overlay_preview(stage1, edited["regions"]))
        _save_png(bundle / "all-highlighted.png", _highlight_preview(stage1, edited["regions"]))

        present_types = [
            grip_type
            for grip_type in _TYPE_ORDER
            if any(region["type"] == grip_type for region in edited["regions"])
        ]
        for grip_type in present_types:
            filtered = [
                region for region in edited["regions"] if region["type"] == grip_type
            ]
            _save_png(bundle / f"{grip_type}.png", _highlight_preview(stage1, filtered))

        gallery = _build_gallery_document(
            run=run,
            present_types=present_types,
        )
        _write_text(bundle / "review-gallery.html", gallery)
        _publish_preview_bundle(bundle, target)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)

    payload: dict[str, object] = {
        "galleryPath": str((target / "review-gallery.html").resolve(strict=False)),
        "previewDir": str(target),
        "baselineSha256": sha256_file(run.stage2_regions),
        "editedSha256": sha256_file(run.edited_regions or run.stage2_regions),
        "stage1ImageSha256": sha256_file(run.stage1_image),
    }
    if run.corrections is not None:
        payload["correctionsSha256"] = sha256_file(run.corrections)
    return payload


def build_comparison_document(run: ReviewRun) -> str:
    """Return one fully self-contained read-only comparison document."""
    if run.edited_regions is None:
        raise ValueError("edited regions artifact is missing")

    automatic = _load_regions_document(run.stage2_regions, "stage-2 baseline")
    edited = _load_regions_document(run.edited_regions, "stage-2 edited regions")
    corrections = (
        load_json(run.corrections, "stage-2 review corrections")
        if run.corrections is not None
        else None
    )

    payload = {
        "runRoot": str(run.root),
        "stage1": {
            "dataUrl": _stage1_data_url(run.stage1_image),
            "hash": sha256_file(run.stage1_image),
            "path": str(run.stage1_image.relative_to(run.root)),
        },
        "automatic": {
            "hash": sha256_file(run.stage2_regions),
            "path": str(run.stage2_regions.relative_to(run.root)),
            **automatic,
        },
        "edited": {
            "hash": sha256_file(run.edited_regions),
            "path": str(run.edited_regions.relative_to(run.root)),
            **edited,
        },
        "corrections": (
            {
                "hash": sha256_file(run.corrections),
                "path": str(run.corrections.relative_to(run.root)),
                **corrections,
            }
            if run.corrections is not None and corrections is not None
            else None
        ),
    }

    editor_root = _editor_root()
    template = (editor_root / "compare.html").read_text(encoding="utf-8")
    stylesheet = (editor_root / "compare.css").read_text(encoding="utf-8")
    model = (editor_root / "compare-model.js").read_text(encoding="utf-8")
    return (
        template.replace("__COMPARE_CSS__", stylesheet)
        .replace("__COMPARE_MODEL__", model)
        .replace(
            "__COMPARISON_DATA__",
            _json_for_html(payload),
        )
    )


def write_comparison_document(run: ReviewRun, output: Path) -> Path:
    """Write one self-contained comparison document to *output* atomically."""
    document = build_comparison_document(run)
    target = output.resolve(strict=False)
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.tmp-",
        suffix=target.suffix or ".html",
        dir=target.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(document)
        temporary_path.replace(target)
    finally:
        temporary_path.unlink(missing_ok=True)
    return target


def _build_gallery_document(*, run: ReviewRun, present_types: Iterable[str]) -> str:
    rows = [
        ("Stage 1 image", str(run.stage1_image.relative_to(run.root)), sha256_file(run.stage1_image)),
        ("Automatic regions", str(run.stage2_regions.relative_to(run.root)), sha256_file(run.stage2_regions)),
        (
            "Edited regions",
            str((run.edited_regions or run.stage2_regions).relative_to(run.root)),
            sha256_file(run.edited_regions or run.stage2_regions),
        ),
    ]
    if run.corrections is not None:
        rows.append(
            (
                "Corrections",
                str(run.corrections.relative_to(run.root)),
                sha256_file(run.corrections),
            )
        )

    cards = [
        ("Normal", "normal.png"),
        ("Automatic overlay", "automatic.png"),
        ("Edited overlay", "edited.png"),
        ("All highlighted", "all-highlighted.png"),
    ]
    cards.extend((f"{grip_type.title()} highlighted", f"{grip_type}.png") for grip_type in present_types)

    metadata_rows = "\n".join(
        f"<tr><th>{escape(label)}</th><td>{escape(path)}</td><td><code>{digest}</code></td></tr>"
        for label, path, digest in rows
    )
    preview_cards = "\n".join(
        (
            "<figure>"
            f"<img src=\"{escape(filename)}\" alt=\"{escape(label)}\" />"
            f"<figcaption>{escape(label)}</figcaption>"
            "</figure>"
        )
        for label, filename in cards
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Hold Region Review Preview</title>
    <style>
      :root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
      body {{ margin: 0; background: #101210; color: #f3f0e8; }}
      main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
      h1 {{ margin: 0 0 6px; font-size: 22px; }}
      p {{ margin: 0 0 24px; color: #a0a69d; }}
      .gallery {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 18px; margin-bottom: 28px; }}
      figure {{ margin: 0; background: #171916; border: 1px solid #30352e; border-radius: 14px; overflow: hidden; }}
      img {{ display: block; width: 100%; height: auto; background: #d6d7d3; }}
      figcaption {{ padding: 10px 12px 12px; font-size: 13px; }}
      table {{ width: 100%; border-collapse: collapse; background: #171916; border: 1px solid #30352e; border-radius: 14px; overflow: hidden; }}
      th, td {{ padding: 10px 12px; border-bottom: 1px solid #252925; text-align: left; vertical-align: top; font-size: 13px; }}
      th {{ width: 170px; color: #a0a69d; }}
      code {{ font-size: 12px; word-break: break-all; color: #ffd7bf; }}
    </style>
  </head>
  <body>
    <main>
      <h1>Hold Region Review Preview</h1>
      <p>Deterministic preview bundle rendered from immutable review artifacts with relative asset references only.</p>
      <section class="gallery">
        {preview_cards}
      </section>
      <table>
        <thead>
          <tr><th>Artifact</th><th>Relative path</th><th>SHA-256</th></tr>
        </thead>
        <tbody>
          {metadata_rows}
        </tbody>
      </table>
    </main>
  </body>
</html>
"""


def _publish_preview_bundle(bundle: Path, target: Path) -> None:
    if target.exists() and not target.is_dir():
        raise ValueError(f"preview target must be a directory: {target}")

    backup: Path | None = None
    if target.exists():
        backup = target.parent / f".{target.name}.backup-{uuid4().hex}"
        target.replace(backup)

    try:
        bundle.replace(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.replace(target)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)


def _editor_root() -> Path:
    return Path(__file__).resolve().parents[3] / "HangboardWorkbench"


def _stage1_data_url(path: Path) -> str:
    stage1 = _load_stage1_image(path)
    buffer = BytesIO()
    stage1.save(buffer, format="PNG", compress_level=9)
    encoded = b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _load_stage1_image(path: Path) -> Image.Image:
    try:
        with Image.open(path) as image:
            stage1 = image.convert("RGBA")
    except OSError as error:
        raise ValueError(f"stage 1 image is not a valid raster image: {path}") from error
    return stage1


def _load_regions_document(path: Path, label: str) -> dict[str, object]:
    document = load_json(path, label)
    canvas = document.get("canvas")
    if not isinstance(canvas, Mapping):
        raise ValueError(f"{label} canvas must be a JSON object")
    width = _positive_int(canvas.get("width"))
    height = _positive_int(canvas.get("height"))
    if width is None or height is None:
        raise ValueError(f"{label} canvas must define positive integer width and height")
    raw_regions = document.get("regions")
    if not isinstance(raw_regions, list):
        raise ValueError(f"{label} regions must be a JSON array")

    seen_ids: set[int] = set()
    regions: list[dict[str, object]] = []
    for index, region in enumerate(raw_regions):
        path_label = f"{label} regions[{index}]"
        if not isinstance(region, Mapping):
            raise ValueError(f"{path_label} must be a JSON object")
        region_id = region.get("id")
        if not isinstance(region_id, int) or isinstance(region_id, bool):
            raise ValueError(f"{path_label}.id must be an integer")
        if region_id in seen_ids:
            raise ValueError(f"{path_label}.id must be unique")
        seen_ids.add(region_id)
        key = region.get("key")
        grip_type = region.get("type")
        mode = _region_mode(region)
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{path_label}.key must be a non-empty string")
        if grip_type not in _TYPE_COLORS:
            raise ValueError(f"{path_label}.type must be one of {', '.join(_TYPE_ORDER)}")
        if mode not in {"surface", "aperture"}:
            raise ValueError(f"{path_label}.mode must be aperture or surface")
        contour = _validate_contour(region.get("contour"), width, height, path_label)
        regions.append(
            {
                "id": region_id,
                "key": key,
                "type": grip_type,
                "mode": mode,
                "contour": contour,
            }
        )

    return {"canvas": {"width": width, "height": height}, "regions": regions}


def _validate_contour(
    raw_contour: object, width: int, height: int, path_label: str
) -> list[list[float]]:
    if not isinstance(raw_contour, list) or len(raw_contour) < 3:
        raise ValueError(f"{path_label}.contour must contain at least three points")
    contour: list[list[float]] = []
    for point_index, point in enumerate(raw_contour):
        if not isinstance(point, list | tuple) or len(point) != 2:
            raise ValueError(f"{path_label}.contour[{point_index}] must be a point pair")
        x = _finite_number(point[0])
        y = _finite_number(point[1])
        if x is None or y is None:
            raise ValueError(f"{path_label}.contour[{point_index}] must be finite")
        if x < 0 or y < 0 or x > width or y > height:
            raise ValueError(f"{path_label}.contour[{point_index}] must stay inside the canvas")
        contour.append([float(x), float(y)])
    if abs(_shoelace_area(contour)) == 0:
        raise ValueError(f"{path_label}.contour must have positive area")
    return contour


def _positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value if value > 0 else None


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _region_mode(region: Mapping[str, object]) -> object:
    metadata = region.get("metadata")
    if isinstance(metadata, Mapping) and metadata.get("mode") is not None:
        return metadata.get("mode")
    return region.get("mode", region.get("visualMode"))


def _json_for_html(payload: Mapping[str, object]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return (
        serialized.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _shoelace_area(points: list[list[float]]) -> float:
    total = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        total += (x1 * y2) - (x2 * y1)
    return total / 2.0


def _overlay_preview(image: Image.Image, regions: list[dict[str, object]]) -> Image.Image:
    preview = image.copy()
    draw = ImageDraw.Draw(preview, "RGBA")
    for region in sorted(regions, key=lambda item: int(item["id"])):
        color = _hex_to_rgba(_TYPE_COLORS[str(region["type"])], 128)
        stroke = _hex_to_rgba(_TYPE_COLORS[str(region["type"])], 255)
        contour = [tuple(point) for point in region["contour"]]
        draw.polygon(contour, fill=color, outline=stroke, width=2)
    return preview


def _highlight_preview(
    image: Image.Image, regions: list[dict[str, object]]
) -> Image.Image:
    preview = image.copy()
    draw = ImageDraw.Draw(preview, "RGBA")
    for region in sorted(regions, key=lambda item: int(item["id"])):
        color = _hex_to_rgba(_TYPE_COLORS[str(region["type"])], 184)
        contour = [tuple(point) for point in region["contour"]]
        draw.polygon(contour, fill=color, outline=_hex_to_rgba("#ffffff", 220), width=2)
    return preview


def _hex_to_rgba(value: str, alpha: int) -> tuple[int, int, int, int]:
    value = value.removeprefix("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        alpha,
    )


def _save_png(path: Path, image: Image.Image) -> None:
    image.save(path, format="PNG", compress_level=9)


def _write_text(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")
