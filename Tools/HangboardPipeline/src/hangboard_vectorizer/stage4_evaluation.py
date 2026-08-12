"""Oracle-isolated validation and visual review for finalized Stage 4 candidates."""

from __future__ import annotations

import base64
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from typing import Mapping
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .display_paths import parse_display_path
from .stage4_composition import Stage4Candidate, compose_stage4
from .vector_smoothing import rasterize_paths_half_open


_CANDIDATE_NAMES = frozenset(
    (
        "stage-4-product.svg",
        "stage-4-manifest.json",
        "stage-4-normal.png",
        "stage-4-highlight-jugs.png",
        "stage-4-highlight-slopers.png",
        "stage-4-highlight-symmetric-pockets.png",
        "stage-4-highlight-mixed.png",
        "stage-4-highlight-all.png",
        "stage-4-highlights.json",
    )
)


def evaluate_stage4_candidate(
    candidate_root: Path,
    *,
    source_png: bytes,
    stage3_document: Mapping[str, object],
    stage3_acceptance_raw_sha256: str,
    manual_oracle_path: Path | None,
    browser_oracle_path: Path | None,
    oracle_paths: Mapping[str, str] | None,
    stage3_acceptance: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Verify candidate integrity before reading any optional comparison evidence."""
    hashes = _verify_hashes(candidate_root)
    candidate = compose_stage4(source_png, stage3_document)
    _verify_bytes(candidate_root, candidate)
    _verify_svg_manifest(candidate_root, candidate)
    # Recomposition checks the path parser, coverage masks, scenario selection,
    # source-over blending, and every preview before the first oracle read.
    _verify_highlight_contract(candidate_root, candidate)

    source = _decode_png(source_png, "Stage 4 source")
    manual_png_exact: bool | None = None
    manual_rgb_mae: float | None = None
    manual_maximum_rgb_error: int | None = None
    product_mask_iou: float | None = None
    full_canvas_rgb_mae: float | None = None
    maximum_rgb_error: int | None = None
    browser_rgb_mae: float | None = None
    manual = None
    if manual_oracle_path is not None:
        manual_bytes = manual_oracle_path.read_bytes()
        manual_png_exact = manual_bytes == source_png
        manual = _decode_png(manual_bytes, "manual oracle")
        if manual.shape != source.shape:
            raise ValueError("manual oracle dimensions differ from Stage 4 source")
        manual_mask_iou = _iou(source[..., 3] > 0, manual[..., 3] > 0)
        difference = np.abs(
            source[..., :3].astype(np.int16) - manual[..., :3].astype(np.int16)
        )
        manual_rgb_mae = float(difference.mean())
        manual_maximum_rgb_error = int(difference.max())
    if browser_oracle_path is not None:
        browser = _decode_png(browser_oracle_path.read_bytes(), "browser oracle")
        generated, generated_mask = _browser_proof(
            source, browser.shape[1], browser.shape[0]
        )
        browser_rgb = _opaque_rgb(browser)
        difference = np.abs(generated.astype(np.int16) - browser_rgb.astype(np.int16))
        browser_rgb_mae = float(difference.mean())
        product_mask_iou = _iou(generated_mask, np.any(255 - browser_rgb > 1, axis=2))
        full_canvas_rgb_mae = browser_rgb_mae
        maximum_rgb_error = int(difference.max())
    elif manual_oracle_path is not None:
        product_mask_iou = manual_mask_iou
        full_canvas_rgb_mae = manual_rgb_mae
        maximum_rgb_error = manual_maximum_rgb_error

    # Optional V14 data is deliberately read only after immutable candidate gates.
    oracle_geometry = None
    oracle_region_count = None
    if stage3_acceptance is not None:
        if oracle_paths is None:
            from .beastmaker_v14_paths import ACCEPTED_V14_PATHS

            oracle_paths = ACCEPTED_V14_PATHS
        oracle_geometry = _validate_v14_geometry(
            candidate, stage3_document, stage3_acceptance, oracle_paths
        )
        oracle_region_count = oracle_geometry["regionCount"]
    manual_accepted = (
        (
            manual_png_exact is True
            and manual_rgb_mae is not None
            and manual_rgb_mae <= 4.0
            and manual_maximum_rgb_error is not None
            and manual_maximum_rgb_error <= 32
        )
        if manual_oracle_path is not None
        else True
    )
    browser_accepted = (
        (
            product_mask_iou is not None
            and product_mask_iou >= 0.995
            and full_canvas_rgb_mae is not None
            and full_canvas_rgb_mae <= 4.0
            and maximum_rgb_error is not None
            and maximum_rgb_error <= 32
        )
        if browser_oracle_path is not None
        else True
    )
    accepted = manual_accepted and browser_accepted
    review = _review_image(
        manual,
        _decode_png(candidate.normal_png, "normal preview"),
        candidate,
        manual_rgb_mae,
        browser_rgb_mae,
    )
    _encode_png(review, candidate_root / "stage-4-review.png")
    acceptance = {
        "accepted": accepted,
        "artifacts": {
            "candidateHashes": "stage-4-candidate-hashes.json",
            "manifest": "stage-4-manifest.json",
            "product": "stage-4-product.svg",
            "review": "stage-4-review.png",
        },
        "candidateHashes": hashes,
        "metrics": {
            "browserRgbMae": browser_rgb_mae,
            "fullCanvasRgbMae": full_canvas_rgb_mae,
            "highlightValidation": "delegated-to-stage4-composition",
            "manualPngExact": manual_png_exact,
            "manualRgbMae": manual_rgb_mae,
            "manualMaximumRgbError": manual_maximum_rgb_error,
            "maximumRgbError": maximum_rgb_error,
            "productMaskIou": product_mask_iou,
        },
        "stage3Geometry": oracle_geometry,
        "oracleRegionCount": oracle_region_count,
        "schemaVersion": 1,
        "stage": 4,
        "stage3AcceptanceRawSha256": stage3_acceptance_raw_sha256,
    }
    _write_json(candidate_root / "stage-4-acceptance.json", acceptance)
    if not accepted:
        raise ValueError(
            "Stage 4 candidate does not meet comparison acceptance thresholds"
        )
    return acceptance


def _verify_hashes(root: Path) -> dict[str, str]:
    expected_set = set(_CANDIDATE_NAMES) | {"stage-4-candidate-hashes.json"}
    if {path.name for path in root.iterdir()} != expected_set:
        raise ValueError("Stage 4 candidate file set is invalid")
    try:
        document = json.loads(
            (root / "stage-4-candidate-hashes.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("Stage 4 candidate hash manifest is invalid") from error
    files = document.get("files") if isinstance(document, dict) else None
    if (
        not isinstance(document, dict)
        or set(document) != {"files", "schemaVersion"}
        or document.get("schemaVersion") != 1
        or not isinstance(files, dict)
        or set(files) != _CANDIDATE_NAMES
    ):
        raise ValueError("Stage 4 candidate hash manifest is invalid")
    for name, digest in files.items():
        if (
            not isinstance(digest, str)
            or sha256((root / name).read_bytes()).hexdigest() != digest
        ):
            raise ValueError(f"serialized Stage 4 candidate was changed: {name}")
    return {name: files[name] for name in sorted(files)}


def _verify_bytes(root: Path, candidate: Stage4Candidate) -> None:
    expected = _candidate_bytes(candidate)
    for name, value in expected.items():
        if (root / name).read_bytes() != value:
            raise ValueError(f"serialized Stage 4 candidate does not reproduce: {name}")


def _verify_svg_manifest(root: Path, candidate: Stage4Candidate) -> None:
    try:
        svg = ET.fromstring((root / "stage-4-product.svg").read_bytes())
        manifest = json.loads(
            (root / "stage-4-manifest.json").read_text(encoding="utf-8")
        )
    except (ET.ParseError, json.JSONDecodeError) as error:
        raise ValueError("serialized Stage 4 SVG or manifest is invalid") from error
    ns = "{http://www.w3.org/2000/svg}"
    if (
        svg.tag != ns + "svg"
        or svg.get("viewBox") != f"0 0 {candidate.width} {candidate.height}"
    ):
        raise ValueError("serialized Stage 4 SVG dimensions mismatch")
    images = svg.findall(ns + "image")
    paths = svg.findall(ns + "path")
    if len(images) != 1 or len(paths) != len(json.loads(candidate.manifest)["regions"]):
        raise ValueError("serialized Stage 4 SVG element count is invalid")
    href = images[0].get("href")
    if (
        not isinstance(href, str)
        or not href.startswith("data:image/png;base64,")
        or base64.b64decode(href.split(",", 1)[1], validate=True)
        != candidate.source_png
    ):
        raise ValueError("serialized Stage 4 SVG image does not match source PNG")
    if manifest != json.loads(candidate.manifest):
        raise ValueError("serialized Stage 4 manifest is not canonical")
    for item, path in zip(manifest["regions"], paths, strict=True):
        if (
            path.get("id"),
            path.get("data-piece"),
            path.get("data-type"),
            path.get("d"),
        ) != (item["id"], item["pieceId"], item["type"], item["displayPath"]):
            raise ValueError("serialized Stage 4 SVG path parity mismatch")


def _verify_highlight_contract(root: Path, candidate: Stage4Candidate) -> None:
    expected = json.loads(candidate.highlight_manifest)
    actual = json.loads((root / "stage-4-highlights.json").read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("serialized Stage 4 highlight manifest is not canonical")
    for name, data in candidate.highlight_pngs:
        if (root / f"stage-4-highlight-{name}.png").read_bytes() != data:
            raise ValueError(f"serialized Stage 4 highlight does not reproduce: {name}")


def _candidate_bytes(candidate: Stage4Candidate) -> dict[str, bytes]:
    return {
        "stage-4-product.svg": candidate.svg,
        "stage-4-manifest.json": candidate.manifest,
        "stage-4-normal.png": candidate.normal_png,
        "stage-4-highlights.json": candidate.highlight_manifest,
        **{
            f"stage-4-highlight-{name}.png": data
            for name, data in candidate.highlight_pngs
        },
    }


def _decode_png(data: bytes, label: str) -> np.ndarray:
    try:
        with Image.open(BytesIO(data)) as image:
            if (
                image.format != "PNG"
                or image.mode not in {"RGB", "RGBA"}
                or getattr(image, "n_frames", 1) != 1
            ):
                raise ValueError(f"{label} must be a static RGB(A) PNG")
            return np.asarray(image).copy()
    except OSError as error:
        raise ValueError(f"could not decode {label}") from error


def _browser_proof(
    rgba: np.ndarray, width: int, height: int
) -> tuple[np.ndarray, np.ndarray]:
    """Place the source on white using the browser's generic contain transform."""
    scale = min(width / rgba.shape[1], height / rgba.shape[0])
    target = Image.fromarray(rgba, mode="RGBA").resize(
        (round(rgba.shape[1] * scale), round(rgba.shape[0] * scale)),
        Image.Resampling.BICUBIC,
    )
    x, y = (width - target.width) // 2, (height - target.height) // 2
    canvas = Image.new("RGBA", (width, height), "white")
    canvas.alpha_composite(target, (x, y))
    product_mask = np.zeros((height, width), dtype=bool)
    product_mask[y : y + target.height, x : x + target.width] = (
        np.asarray(target)[..., 3] > 1
    )
    return np.asarray(canvas.convert("RGB")), product_mask


def _review_image(
    manual: np.ndarray | None,
    normal: np.ndarray,
    candidate: Stage4Candidate,
    manual_mae: float | None,
    browser_mae: float | None,
) -> np.ndarray:
    lookup = dict(candidate.highlight_pngs)
    panels = [
        manual if manual is not None else normal,
        normal,
        *(
            _decode_png(lookup[name], name)
            for name in ("jugs", "slopers", "symmetric-pockets", "mixed")
        ),
    ]
    height, width = normal.shape[:2]
    label_height, footer = 16, 16
    canvas = Image.new(
        "RGB", (width * 2, (height + label_height) * 3 + footer), "white"
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    labels = (
        "manual normal",
        "automatic normal",
        "jugs",
        "slopers",
        "symmetric pockets",
        "mixed",
    )
    for index, (label, rgba) in enumerate(zip(labels, panels, strict=True)):
        x, y = (index % 2) * width, (index // 2) * (height + label_height)
        draw.text((x + 2, y + 2), label, fill=(25, 25, 25), font=font)
        image = (
            Image.fromarray(rgba, mode="RGBA")
            if rgba.shape[2] == 4
            else Image.fromarray(rgba, mode="RGB")
        )
        canvas.paste(
            image, (x, y + label_height), image if image.mode == "RGBA" else None
        )
    manual_text = "unavailable" if manual_mae is None else f"{manual_mae:.3f}"
    browser_text = "unavailable" if browser_mae is None else f"{browser_mae:.3f}"
    draw.text(
        (2, canvas.height - footer + 2),
        f"normal MAE: {manual_text}; browser MAE: {browser_text}; highlights validated during composition",
        fill=(25, 25, 25),
        font=font,
    )
    return np.asarray(canvas)


def _encode_png(array: np.ndarray, path: Path) -> None:
    Image.fromarray(array).save(path, format="PNG", optimize=False, compress_level=9)


def _iou(first: np.ndarray, second: np.ndarray) -> float:
    union = np.count_nonzero(first | second)
    return float(np.count_nonzero(first & second) / union) if union else 1.0


def _opaque_rgb(image: np.ndarray) -> np.ndarray:
    if image.shape[2] == 3:
        return image
    alpha = image[..., 3:4].astype(np.float32) / 255.0
    return np.rint(
        image[..., :3].astype(np.float32) * alpha + 255.0 * (1.0 - alpha)
    ).astype(np.uint8)


def _validate_v14_geometry(
    candidate: Stage4Candidate,
    document: Mapping[str, object],
    acceptance: Mapping[str, object],
    oracle_paths: Mapping[str, str],
) -> dict[str, object]:
    """Bind the finalized Stage 4 paths to the accepted Stage 3/V14 pairing."""
    regions = document.get("regions")
    pairing = acceptance.get("pairing")
    expected_regions = acceptance.get("oracleRegions")
    expected_metrics = acceptance.get("oracleMetrics")
    raw_regions = acceptance.get("rawRegions")
    raw_metrics = acceptance.get("rawMetrics")
    if (
        not isinstance(regions, list)
        or len(regions) != 22
        or not isinstance(pairing, list)
        or not isinstance(expected_regions, list)
        or not isinstance(expected_metrics, dict)
        or not isinstance(raw_regions, list)
        or not isinstance(raw_metrics, dict)
    ):
        raise ValueError("Stage 3 V14 geometry evidence is invalid")
    region_ids = [item.get("id") for item in regions if isinstance(item, dict)]
    types = [item.get("type") for item in regions if isinstance(item, dict)]
    if (
        len(region_ids) != 22
        or len(set(region_ids)) != 22
        or {kind: types.count(kind) for kind in ("pocket", "sloper", "jug")}
        != {"pocket": 17, "sloper": 3, "jug": 2}
    ):
        raise ValueError("Stage 4 V14 topology is invalid")
    pairs = [
        (item.get("candidateId"), item.get("oracleId"))
        for item in pairing
        if isinstance(item, dict)
    ]
    if (
        len(pairs) != 22
        or len(set(pairs)) != 22
        or {first for first, _ in pairs} != set(region_ids)
        or {second for _, second in pairs} != set(oracle_paths)
        or len(oracle_paths) != 22
    ):
        raise ValueError("Stage 4 V14 pairing is invalid")
    center = [
        second
        for first, second in pairs
        if next(item["type"] for item in regions if item["id"] == first) == "sloper"
        and second == "sloper-center"
    ]
    if center != ["sloper-center"]:
        raise ValueError("Stage 4 V14 center sloper is not continuous")
    paths = []
    for region in regions:
        assert isinstance(region, dict)
        parsed = parse_display_path(
            region.get("displayPath"),
            str(region.get("id")),
            candidate.width,
            candidate.height,
            allow_linear_segments=True,
        )
        if parsed is None:
            raise ValueError("Stage 4 geometry path is missing")
        paths.append(parsed)
    from .stage2_evaluation import _oracle_masks, _region_metrics, _summary

    masks = dict(
        zip(
            region_ids,
            rasterize_paths_half_open(tuple(paths), candidate.width, candidate.height),
            strict=True,
        )
    )
    oracle = _oracle_masks(oracle_paths, candidate.width, candidate.height)
    actual_regions = [
        _region_metrics(first, second, masks[first], oracle[second][1])
        for first, second in pairs
    ]
    actual_metrics = _summary(actual_regions)
    if actual_regions != expected_regions or actual_metrics != expected_metrics:
        raise ValueError(
            "Stage 4 geometry metrics do not exactly inherit accepted Stage 3"
        )
    return {
        "oracleMetrics": expected_metrics,
        "rawMetrics": raw_metrics,
        "rawRegions": raw_regions,
        "regionCount": 22,
    }


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
