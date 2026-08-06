"""Evidence-first transactional runner for Stage 3 vector smoothing."""

from __future__ import annotations

import base64
from dataclasses import asdict, dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from shutil import rmtree
from tempfile import mkdtemp
from typing import Mapping

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .hold_discovery import _mask_geometry, decode_mask_rle
from .vector_smoothing import (
    Stage2MaskRegion,
    VectorizationProfile,
    VectorizedLayout,
    rasterize_display_path,
    vectorize_layout,
)


BEASTMAKER_STAGE2_POLICY_ID = "beastmaker-1000-stage2-v2"
_BEASTMAKER_STAGE2_ACCEPTANCE_SHA256 = "5aed70191f32c7b3c841e3cb3cb95cef8b163b6c70ed43e073346b403e06ae68"
_STAGE2_CANDIDATE_NAMES = frozenset(
    {
        "stage-2-proposals.json",
        "stage-2-source-rgba.png",
        "stage-2-labels.png",
        "stage-2-candidates.png",
        "stage-2-auto-regions.json",
        "stage-2-auto-regions-labeled.png",
        "stage-2-generation.json",
    }
)
_STAGE3_CANDIDATE_NAMES = (
    "stage-3-vector-regions.json",
    "stage-3-vector.svg",
    "stage-3-vector-overlay.png",
)


@dataclass(frozen=True, slots=True)
class Stage3EvidenceInputs:
    stage2_acceptance_path: Path
    stage2_regions_path: Path
    stage2_labels_path: Path
    stage2_source_rgba_path: Path
    policy_id: str = BEASTMAKER_STAGE2_POLICY_ID

    @classmethod
    def from_root(cls, root: Path) -> "Stage3EvidenceInputs":
        return cls(
            root / "stage-2-acceptance.json",
            root / "stage-2-auto-regions.json",
            root / "stage-2-labels.png",
            root / "stage-2-source-rgba.png",
        )


def run_stage3_onboarding(
    evidence: Stage3EvidenceInputs,
    artifact_root: Path,
    *,
    profile: VectorizationProfile | None = None,
    oracle_paths: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    """Validate Stage 2, finalize deterministic candidates, then evaluate."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"stage 3 artifact root already exists: {artifact_root}")
    acceptance, acceptance_digest, rgba, labels, regions = _validate_stage2(evidence)
    profile = profile or VectorizationProfile()
    first = vectorize_layout(rgba, labels, regions, profile=profile)
    second = vectorize_layout(rgba, labels, regions, profile=profile)
    first_bytes = _layout_bytes(first, profile, acceptance_digest)
    second_bytes = _layout_bytes(second, profile, acceptance_digest)
    if first_bytes != second_bytes:
        raise ValueError("Stage 3 vectorization is nondeterministic")
    _validate_beastmaker_topology(first, regions)

    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(mkdtemp(prefix=f".{artifact_root.name}.", dir=artifact_root.parent))
    try:
        _write_candidate_bundle(temporary, rgba, first, first_bytes)
        from .stage3_evaluation import evaluate_stage3_candidate

        document = evaluate_stage3_candidate(
            temporary,
            source_rgba=rgba,
            raw_regions=regions,
            stage2_acceptance=acceptance,
            stage2_acceptance_raw_sha256=acceptance_digest,
            oracle_paths=oracle_paths,
        )
        if artifact_root.exists():
            raise FileExistsError(f"stage 3 artifact root already exists: {artifact_root}")
        temporary.rename(artifact_root)
    except Exception:
        rmtree(temporary, ignore_errors=True)
        raise
    return document


def _validate_stage2(
    evidence: Stage3EvidenceInputs,
) -> tuple[dict[str, object], str, np.ndarray, np.ndarray, tuple[Stage2MaskRegion, ...]]:
    if evidence.policy_id != BEASTMAKER_STAGE2_POLICY_ID:
        raise ValueError(f"unsupported Stage 2 evidence policy: {evidence.policy_id}")
    paths = (
        evidence.stage2_acceptance_path,
        evidence.stage2_regions_path,
        evidence.stage2_labels_path,
        evidence.stage2_source_rgba_path,
    )
    if any(not path.is_file() for path in paths):
        raise FileNotFoundError("required accepted Stage 2 evidence is missing")
    acceptance_raw = evidence.stage2_acceptance_path.read_bytes()
    acceptance_digest = sha256(acceptance_raw).hexdigest()
    if acceptance_digest != _BEASTMAKER_STAGE2_ACCEPTANCE_SHA256:
        raise ValueError("Stage 2 acceptance raw identity mismatch")
    acceptance = _json(acceptance_raw, "Stage 2 acceptance")
    if (
        set(acceptance) != {
            "accepted", "artifacts", "candidateHashes", "generationEvidence",
            "metrics", "pairing", "regions", "schemaVersion", "stage", "thresholds",
        }
        or acceptance.get("accepted") is not True
        or acceptance.get("stage") != 2
        or acceptance.get("schemaVersion") != 1
    ):
        raise ValueError("Stage 2 acceptance does not approve vector smoothing")
    hashes = acceptance.get("candidateHashes")
    if not isinstance(hashes, dict) or set(hashes) != _STAGE2_CANDIDATE_NAMES:
        raise ValueError("accepted Stage 2 candidate artifact set is invalid")
    expected_names = {
        evidence.stage2_regions_path.name,
        evidence.stage2_labels_path.name,
        evidence.stage2_source_rgba_path.name,
    }
    if expected_names != {
        "stage-2-auto-regions.json", "stage-2-labels.png", "stage-2-source-rgba.png"
    }:
        raise ValueError("Stage 2 evidence filenames are invalid")
    for path in paths[1:]:
        expected = hashes.get(path.name)
        if not isinstance(expected, str) or sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"accepted Stage 2 evidence was changed: {path.name}")

    try:
        with Image.open(BytesIO(evidence.stage2_source_rgba_path.read_bytes())) as image:
            if image.format != "PNG" or image.mode != "RGBA":
                raise ValueError("Stage 2 source must be an RGBA PNG")
            rgba = np.asarray(image).copy()
        with Image.open(BytesIO(evidence.stage2_labels_path.read_bytes())) as image:
            if image.format != "PNG" or image.mode != "I;16" or image.size != (rgba.shape[1], rgba.shape[0]):
                raise ValueError("Stage 2 labels must be a matching 16-bit PNG")
            labels = np.asarray(image).astype(np.uint16)
    except OSError as error:
        raise ValueError("could not decode accepted Stage 2 images") from error
    regions_document = _json(evidence.stage2_regions_path.read_bytes(), "Stage 2 regions")
    regions = _parse_regions(regions_document, rgba, labels)
    return acceptance, acceptance_digest, rgba, labels, regions


def _parse_regions(
    document: object, rgba: np.ndarray, labels: np.ndarray
) -> tuple[Stage2MaskRegion, ...]:
    height, width = rgba.shape[:2]
    expected_root = {"candidatePixelSha256", "height", "regions", "schemaVersion", "stage", "width"}
    if (
        not isinstance(document, dict)
        or set(document) != expected_root
        or document.get("schemaVersion") != 1
        or document.get("stage") != 2
        or document.get("width") != width
        or document.get("height") != height
        or document.get("candidatePixelSha256") != sha256(rgba.tobytes()).hexdigest()
    ):
        raise ValueError("invalid accepted Stage 2 regions document")
    values = document.get("regions")
    if not isinstance(values, list) or len(values) != 22:
        raise ValueError("accepted Stage 2 region count is invalid")
    expected_fields = {
        "anchorCell", "areaPixels", "bbox", "center", "contour", "id", "maskRle",
        "maskSha256", "pieceIndex", "provenance", "row", "type", "visualMode",
    }
    result: list[Stage2MaskRegion] = []
    reconstructed = np.zeros((height, width), dtype=np.uint16)
    for index, item in enumerate(values, start=1):
        if (
            not isinstance(item, dict)
            or set(item) != expected_fields
            or item.get("id") != f"piece-{int(item.get('pieceIndex', -1)) + 1:02d}-hold-{index:02d}"
            or not re.fullmatch(r"piece-[0-9]{2}-hold-[0-9]{2}", item["id"])
            or item.get("type") not in {"pocket", "jug", "sloper"}
            or item.get("visualMode") not in {"aperture", "surface"}
            or type(item.get("pieceIndex")) is not int
            or type(item.get("row")) is not int
        ):
            raise ValueError("invalid accepted Stage 2 region")
        mask = decode_mask_rle(item["maskRle"], (height, width))
        contour, center, bbox, area = _mask_geometry(mask)
        if (
            item.get("areaPixels") != area
            or item.get("bbox") != list(bbox)
            or item.get("center") != [round(center[0], 6), round(center[1], 6)]
            or item.get("contour") != [list(point) for point in contour]
            or item.get("maskSha256") != sha256(mask.tobytes()).hexdigest()
        ):
            raise ValueError("accepted Stage 2 region metadata does not match its mask")
        if np.any(reconstructed[mask.astype(bool)]):
            raise ValueError("accepted Stage 2 region masks overlap")
        reconstructed[mask.astype(bool)] = index
        result.append(
            Stage2MaskRegion(
                id=item["id"],
                piece_index=item["pieceIndex"],
                grip_type=item["type"],
                visual_mode=item["visualMode"],
                row=item["row"],
                mask=mask,
                raw_mask_sha256=item["maskSha256"],
            )
        )
    if not np.array_equal(labels, reconstructed):
        raise ValueError("Stage 2 label raster does not match ordered RLE masks")
    return tuple(result)


def _validate_beastmaker_topology(
    layout: VectorizedLayout, raw_regions: tuple[Stage2MaskRegion, ...]
) -> None:
    if len(layout.regions) != 22:
        raise ValueError("Stage 3 must retain exactly 22 regions")
    expected = tuple(
        (region.id, region.piece_index, region.grip_type) for region in raw_regions
    )
    actual = tuple(
        (region.id, region.piece_index, region.grip_type) for region in layout.regions
    )
    if actual != expected:
        raise ValueError("Stage 3 changed Stage 2 region identity or order")
    counts = {kind: sum(region.grip_type == kind for region in layout.regions) for kind in ("pocket", "jug", "sloper")}
    if counts != {"pocket": 17, "jug": 2, "sloper": 3}:
        raise ValueError("Stage 3 changed the accepted grip topology")
    piece_x = np.nonzero(np.logical_or.reduce(tuple(region.mask.astype(bool) for region in raw_regions)))[1]
    midpoint = (float(piece_x.min()) + float(piece_x.max()) + 1.0) / 2.0
    crossing = []
    for region in raw_regions:
        if region.grip_type != "sloper":
            continue
        xs = np.nonzero(region.mask)[1]
        crossing.append(float(xs.min()) <= midpoint <= float(xs.max() + 1))
    if sum(crossing) != 1:
        raise ValueError("Stage 3 must retain one continuous center sloper")


def _layout_bytes(
    layout: VectorizedLayout, profile: VectorizationProfile, acceptance_digest: str
) -> bytes:
    document = {
        "canonicalSeams": [
            {
                "firstId": seam.first_id,
                "id": seam.id,
                "kind": seam.kind,
                "path": seam.path.data,
                "rawCoordinates": [[_round(x), _round(y)] for x, y in seam.raw_coordinates],
                "reversePath": seam.path.reversed().data,
                "secondId": seam.second_id,
            }
            for seam in layout.canonical_seams
        ],
        "height": layout.height,
        "pieces": [
            {
                "displayPath": piece.display_path.data,
                "id": piece.id,
                "outputMaskSha256": piece.output_mask_sha256,
                "pieceIndex": piece.piece_index,
                "rawMaskSha256": piece.raw_mask_sha256,
                "sharedSeamIds": list(piece.shared_seam_ids),
            }
            for piece in layout.pieces
        ],
        "profile": asdict(profile),
        "regions": [
            {
                "displayPath": region.display_path.data,
                "id": region.id,
                "lockedCorners": [[_round(x), _round(y)] for x, y in region.locked_corners],
                "outputMaskSha256": region.output_mask_sha256,
                "pieceIndex": region.piece_index,
                "primitive": region.primitive,
                "rawMaskSha256": region.raw_mask_sha256,
                "sharedSeamIds": list(region.shared_seam_ids),
                "type": region.grip_type,
            }
            for region in layout.regions
        ],
        "schemaVersion": 1,
        "stage": 3,
        "stage2AcceptanceRawSha256": acceptance_digest,
        "width": layout.width,
    }
    return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode()


def _write_candidate_bundle(
    root: Path, rgba: np.ndarray, layout: VectorizedLayout, layout_bytes: bytes
) -> None:
    (root / "stage-3-vector-regions.json").write_bytes(layout_bytes)
    overlay = _vector_overlay(rgba, layout)
    Image.fromarray(overlay).save(root / "stage-3-vector-overlay.png", format="PNG", optimize=False, compress_level=9)
    source = BytesIO()
    Image.fromarray(rgba, mode="RGBA").save(source, format="PNG", optimize=False, compress_level=9)
    (root / "stage-3-vector.svg").write_text(_svg(layout, source.getvalue()), encoding="utf-8")
    hashes = {name: sha256((root / name).read_bytes()).hexdigest() for name in _STAGE3_CANDIDATE_NAMES}
    _write_json(root / "stage-3-candidate-hashes.json", {"files": hashes, "schemaVersion": 1})


def _vector_overlay(rgba: np.ndarray, layout: VectorizedLayout) -> np.ndarray:
    base = rgba[..., :3].copy()
    base[rgba[..., 3] < 128] = 245
    blended = base.astype(np.float32)
    palette = ((42, 194, 218), (238, 113, 63), (161, 92, 220))
    image_masks: list[np.ndarray] = []
    for index, region in enumerate(layout.regions):
        mask = rasterize_display_path(region.display_path, layout.width, layout.height)
        image_masks.append(mask)
        color = np.asarray(palette[index % len(palette)], dtype=np.float32)
        selected = mask.astype(bool)
        blended[selected] = blended[selected] * 0.56 + color * 0.44
        boundary = selected & ~(cv2.erode(mask, np.ones((3, 3), np.uint8)) > 0)
        blended[boundary] = (22, 24, 24)
    image = Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    for index, mask in enumerate(image_masks, start=1):
        moments = cv2.moments(mask, binaryImage=True)
        x, y = moments["m10"] / moments["m00"], moments["m01"] / moments["m00"]
        label = str(index)
        box = draw.textbbox((0, 0), label, font=font)
        text_width, text_height = box[2] - box[0], box[3] - box[1]
        draw.ellipse((x - text_width / 2 - 3, y - text_height / 2 - 2, x + text_width / 2 + 3, y + text_height / 2 + 2), fill=(255, 255, 255), outline=(18, 18, 18))
        draw.text((x - text_width / 2, y - text_height / 2), label, fill=(8, 8, 8), font=font)
    return np.asarray(image)


def _svg(layout: VectorizedLayout, source_png: bytes) -> str:
    encoded = base64.b64encode(source_png).decode("ascii")
    piece_paths = "\n".join(
        f'  <path id="{piece.id}" data-type="piece-silhouette" d="{piece.display_path.data}" fill="none" stroke="#735b42" stroke-width="0.75" />'
        for piece in layout.pieces
    )
    region_paths = "\n".join(
        f'  <path id="{region.id}" data-type="{region.grip_type}" data-primitive="{region.primitive}" d="{region.display_path.data}" fill="none" stroke="#171919" stroke-width="1" />'
        for region in layout.regions
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{layout.width}" height="{layout.height}" viewBox="0 0 {layout.width} {layout.height}">\n'
        f'  <image width="{layout.width}" height="{layout.height}" href="data:image/png;base64,{encoded}" />\n'
        f"{piece_paths}\n{region_paths}\n</svg>\n"
    )


def _json(raw: bytes, name: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} is invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be a JSON object")
    return value


def _round(value: float) -> float:
    return round(float(value), 6)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
