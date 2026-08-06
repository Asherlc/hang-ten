"""Evidence-first, Stage 1-only simplified-raster onboarding."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from .simplification import CleanupProfile, SimplifiedRaster


_BACKGROUND = (248, 247, 244)


@dataclass(frozen=True, slots=True)
class TrustedImageIdentity:
    """Path-independent evidence identity trusted by one reviewed profile."""

    raw_sha256: str
    pixel_sha256: str
    shape: tuple[int, int, int]
    mode: str
    image_format: str


@dataclass(frozen=True, slots=True)
class TrustedStage1Policy:
    """Immutable approved evidence and registration contract for one profile."""

    profile_id: str
    product_id: str
    material: str
    piece_count: int
    pieces: tuple[tuple[str, int, str], ...]
    source_id: str
    source: TrustedImageIdentity
    manual_rgba: TrustedImageIdentity
    manual_review: TrustedImageIdentity
    packaged_render: TrustedImageIdentity
    stage0_acceptance_sha256: str
    registration_shape: tuple[int, int, int]
    registration_crop: tuple[int, int, int, int]


_BEASTMAKER_POLICY = TrustedStage1Policy(
    profile_id="beastmaker-1000-tulipwood-v1",
    product_id="beastmaker-1000",
    material="Tulipwood",
    piece_count=1,
    pieces=(("beastmaker-1000", 0, "Tulipwood"),),
    source_id="official-tulipwood",
    source=TrustedImageIdentity(
        "17e9f743f6cbacf27092a5e5073b88633be4e282cc05a656151a4bde8203328f",
        "e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3",
        (318, 1080, 3),
        "RGB",
        "JPEG",
    ),
    manual_rgba=TrustedImageIdentity(
        "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627",
        "7268f059f3fd285ff70ad6f016de2df74c1478c370fc8a92879ffa2aef0601cf",
        (259, 1000, 4),
        "RGBA",
        "PNG",
    ),
    manual_review=TrustedImageIdentity(
        "f57128ec9700ebf0aaf788cf8aa6e0cab27db4f97335ea39ec5391c27330cd66",
        "340154997498fb44fda5d44b1d498d7bfc565a443aad55be98f561c550f7a54e",
        (459, 1200, 3),
        "RGB",
        "PNG",
    ),
    packaged_render=TrustedImageIdentity(
        "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627",
        "7268f059f3fd285ff70ad6f016de2df74c1478c370fc8a92879ffa2aef0601cf",
        (259, 1000, 4),
        "RGBA",
        "PNG",
    ),
    stage0_acceptance_sha256="a067c62cc1590bf3a57c952258d4c3f791b6c774ebeef624db50566b1cec4039",
    registration_shape=(259, 1000, 3),
    registration_crop=(35, 30, 1041, 289),
)
_TRUSTED_POLICIES: Mapping[str, TrustedStage1Policy] = {
    _BEASTMAKER_POLICY.profile_id: _BEASTMAKER_POLICY,
}


@dataclass(frozen=True, slots=True)
class Stage1EvidenceInputs:
    """Explicit paths; trusted identities belong to the approved profile policy."""

    stage0_acceptance_path: Path
    source_path: Path
    manual_rgba_path: Path
    manual_review_path: Path
    packaged_render_path: Path


@dataclass(frozen=True, slots=True)
class _ValidatedImage:
    identity: TrustedImageIdentity
    raw_bytes: bytes
    pixels: np.ndarray


def beastmaker_stage1_evidence(
    *,
    stage0_acceptance_path: Path,
    source_path: Path,
    manual_rgba_path: Path,
    manual_review_path: Path,
    packaged_render_path: Path,
) -> Stage1EvidenceInputs:
    """Construct explicit paths for the approved Beastmaker policy."""
    return Stage1EvidenceInputs(
        stage0_acceptance_path,
        source_path,
        manual_rgba_path,
        manual_review_path,
        packaged_render_path,
    )


def run_stage1_onboarding(
    evidence: Stage1EvidenceInputs,
    artifact_root: Path,
    *,
    profile: CleanupProfile,
) -> Mapping[str, object]:
    """Publish an all-or-nothing deterministic Stage 1 acceptance bundle."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"stage 1 artifact root already exists: {artifact_root}")
    policy = _validate_profile(profile)
    stage0, source, manual_rgba, manual_review, packaged = _validate_inputs(
        evidence, policy
    )
    first = _validate_profile_result(profile.simplify(source.pixels), policy)
    second = _validate_profile_result(profile.simplify(source.pixels), policy)
    if not _same_raster(first, second):
        raise ValueError("cleanup profile is nondeterministic")
    _require_exact_accepted_output(
        first, manual_rgba.pixels, manual_review.pixels, packaged.pixels
    )

    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(
        mkdtemp(prefix=f".{artifact_root.name}.", dir=artifact_root.parent)
    )
    try:
        document = _write_artifacts(
            temporary,
            policy,
            stage0,
            source,
            first,
            manual_rgba,
            manual_review,
            packaged,
        )
        if artifact_root.exists():
            raise FileExistsError(
                f"stage 1 artifact root already exists: {artifact_root}"
            )
        temporary.rename(artifact_root)
    except Exception:
        rmtree(temporary, ignore_errors=True)
        raise
    return document


def _validate_inputs(
    evidence: Stage1EvidenceInputs,
    policy: TrustedStage1Policy,
) -> tuple[
    Mapping[str, object],
    _ValidatedImage,
    _ValidatedImage,
    _ValidatedImage,
    _ValidatedImage,
]:
    stage0 = _load_stage0_acceptance(evidence.stage0_acceptance_path, policy)
    source = _read_image(evidence.source_path, policy.source, "selected source")
    manual_rgba = _read_image(
        evidence.manual_rgba_path, policy.manual_rgba, "manual RGBA"
    )
    manual_review = _read_image(
        evidence.manual_review_path, policy.manual_review, "manual review"
    )
    packaged = _read_image(
        evidence.packaged_render_path, policy.packaged_render, "packaged render"
    )
    _validate_stage0_contract(stage0, policy, source)
    if manual_rgba.raw_bytes != packaged.raw_bytes:
        raise ValueError("manual RGBA and packaged render PNG bytes differ")
    if not _transparent_rgb_is_zero(manual_rgba.pixels):
        raise ValueError("manual RGBA has nonzero RGB beneath transparent pixels")
    if not _transparent_rgb_is_zero(packaged.pixels):
        raise ValueError("packaged render has nonzero RGB beneath transparent pixels")
    return stage0, source, manual_rgba, manual_review, packaged


def _validate_profile(profile: CleanupProfile) -> TrustedStage1Policy:
    policy = _TRUSTED_POLICIES.get(profile.profile_id)
    if policy is None or (
        profile.product_id,
        profile.material,
        profile.piece_count,
    ) != (policy.product_id, policy.material, policy.piece_count):
        raise ValueError(
            "unsupported Stage 1 cleanup profile identity/material/piece count"
        )
    return policy


def _load_stage0_acceptance(
    path: Path, policy: TrustedStage1Policy
) -> Mapping[str, object]:
    raw = _read_bytes(path, "Stage 0 acceptance")
    if _bytes_sha256(raw) != policy.stage0_acceptance_sha256:
        raise ValueError("Stage 0 acceptance identity mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Stage 0 acceptance is not valid JSON") from error
    if not isinstance(document, dict):
        raise ValueError("Stage 0 acceptance must be an object")
    return document


def _read_image(
    path: Path, identity: TrustedImageIdentity, name: str
) -> _ValidatedImage:
    raw = _read_bytes(path, name)
    if _bytes_sha256(raw) != identity.raw_sha256:
        raise ValueError(f"{name} evidence identity mismatch: {path.name}")
    try:
        with Image.open(BytesIO(raw)) as decoded:
            decoded.load()
            if decoded.format != identity.image_format:
                raise ValueError(f"{name} must be a {identity.image_format}")
            if decoded.mode != identity.mode:
                raise ValueError(f"{name} must use {identity.mode} PNG mode")
            pixels = np.asarray(
                ImageOps.exif_transpose(decoded).convert(identity.mode)
            ).copy()
    except OSError as error:
        raise ValueError(f"could not decode {name} evidence") from error
    if pixels.shape != identity.shape or _array_sha256(pixels) != identity.pixel_sha256:
        raise ValueError(f"{name} evidence identity mismatch: {path.name}")
    return _ValidatedImage(identity, raw, _freeze(pixels))


def _read_bytes(path: Path, name: str) -> bytes:
    if not path.is_file():
        raise FileNotFoundError(f"required {name} evidence is missing: {path}")
    return path.read_bytes()


def _validate_stage0_contract(
    stage0: Mapping[str, object],
    policy: TrustedStage1Policy,
    source: _ValidatedImage,
) -> None:
    resolution = _mapping(stage0.get("resolution"), "Stage 0 resolution")
    selected = _mapping(stage0.get("selectedSource"), "Stage 0 selected source")
    registration = _mapping(stage0.get("registration"), "Stage 0 registration")
    preflight = _mapping(stage0.get("preflight"), "Stage 0 preflight")
    if not preflight.get("passed") or preflight.get("productId") != policy.product_id:
        raise ValueError("Stage 0 preflight does not approve the cleanup product")
    if (
        resolution.get("product_id") != policy.product_id
        or resolution.get("material") != policy.material
    ):
        raise ValueError("Stage 0 commercial identity does not match cleanup profile")
    if (
        selected.get("id") != policy.source_id
        or selected.get("material") != policy.material
        or selected.get("rawJpegSha256") != policy.source.raw_sha256
        or selected.get("decodedRgbSha256") != policy.source.pixel_sha256
        or source.pixels.shape != policy.source.shape
    ):
        raise ValueError(
            "Stage 0 selected source identity does not match supplied evidence"
        )
    if registration.get("canonicalShape") != list(policy.registration_shape):
        raise ValueError("Stage 0 canonical registration shape is not approved")
    crop = _mapping(registration.get("crop"), "Stage 0 registration crop")
    if (
        tuple(crop.get(key) for key in ("left", "top", "right", "bottom"))
        != policy.registration_crop
    ):
        raise ValueError(
            "Stage 0 registration crop is not the approved Beastmaker crop"
        )
    if not registration.get("v6CropExact"):
        raise ValueError("Stage 0 registration was not exact")


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _validate_profile_result(
    result: SimplifiedRaster, policy: TrustedStage1Policy
) -> SimplifiedRaster:
    if (
        result.rgba.shape != policy.manual_rgba.shape
        or result.review_rgb.shape != policy.manual_review.shape
    ):
        raise ValueError("cleanup profile returned an unexpected raster shape")
    if result.repair_mask.shape != policy.manual_rgba.shape[:2]:
        raise ValueError("cleanup profile returned an unexpected repair-mask shape")
    if not _transparent_rgb_is_zero(result.rgba):
        raise ValueError(
            "cleanup profile output has nonzero RGB beneath transparent pixels"
        )
    return result


def _same_raster(first: SimplifiedRaster, second: SimplifiedRaster) -> bool:
    return all(
        np.array_equal(a, b)
        for a, b in zip(
            (first.rgba, first.review_rgb, first.repair_mask),
            (second.rgba, second.review_rgb, second.repair_mask),
            strict=True,
        )
    )


def _require_exact_accepted_output(
    result: SimplifiedRaster,
    manual_rgba: np.ndarray,
    manual_review: np.ndarray,
    packaged_rgba: np.ndarray,
) -> None:
    if not np.array_equal(result.rgba, manual_rgba) or not np.array_equal(
        result.review_rgb, manual_review
    ):
        raise ValueError(
            "cleanup profile output is not pixel-exact to the accepted manual output"
        )
    if not np.array_equal(result.rgba, packaged_rgba):
        raise ValueError(
            "cleanup profile output is not pixel-exact to the packaged render"
        )


def _write_artifacts(
    root: Path,
    policy: TrustedStage1Policy,
    stage0: Mapping[str, object],
    source: _ValidatedImage,
    result: SimplifiedRaster,
    manual_rgba: _ValidatedImage,
    manual_review: _ValidatedImage,
    packaged: _ValidatedImage,
) -> dict[str, object]:
    auto_rgba = root / "stage-1-auto-rgba.png"
    auto_review = root / "stage-1-auto-review.png"
    _write_accepted_bytes(auto_rgba, result.rgba, manual_rgba.raw_bytes, "RGBA")
    _write_accepted_bytes(
        auto_review, result.review_rgb, manual_review.raw_bytes, "RGB"
    )
    _save_png(
        root / "stage-1-auto-vs-manual.png",
        _side_by_side(result.review_rgb, manual_review.pixels),
    )
    heatmap = _difference_heatmap(result.rgba, manual_rgba.pixels)
    _save_png(root / "stage-1-diff-heatmap.png", heatmap)
    _save_png(root / "stage-1-repair-mask.png", _repair_mask_image(result.repair_mask))
    _save_png(
        root / "stage-1-review.png",
        _combined_review(
            source.pixels,
            result.repair_mask,
            result.review_rgb,
            manual_review.pixels,
            heatmap,
        ),
    )
    document = _acceptance_document(
        policy,
        stage0,
        result,
        manual_rgba,
        manual_review,
        packaged,
        root,
    )
    _write_json(root / "stage-1-acceptance.json", document)
    return document


def _acceptance_document(
    policy: TrustedStage1Policy,
    stage0: Mapping[str, object],
    result: SimplifiedRaster,
    manual_rgba: _ValidatedImage,
    manual_review: _ValidatedImage,
    packaged: _ValidatedImage,
    root: Path,
) -> dict[str, object]:
    metrics = _comparison_metrics(
        result.rgba, manual_rgba, result.review_rgb, manual_review, packaged, root
    )
    mandatory = (
        metrics["automatedEqualsManual"],
        metrics["automatedEqualsPackaged"],
        metrics["automatedReviewEqualsManual"],
        metrics["manualEqualsPackaged"],
        metrics["alphaIoU"] == 1.0,
        metrics["rgbMae"] == 0.0,
        metrics["alphaMae"] == 0.0,
        metrics["reviewRgbMae"] == 0.0,
        metrics["rgbMaxAbsError"] == 0,
        metrics["alphaMaxAbsError"] == 0,
        metrics["reviewRgbMaxAbsError"] == 0,
        metrics["routedEdgeDisplacementPx"] == 0.0,
        all(metrics["transparentRgbZero"].values()),
        all(metrics["pngFileEquality"].values()),
    )
    return {
        "accepted": bool(all(mandatory)),
        "artifacts": {
            "automatedRgba": "stage-1-auto-rgba.png",
            "automatedReview": "stage-1-auto-review.png",
            "comparison": "stage-1-auto-vs-manual.png",
            "differenceHeatmap": "stage-1-diff-heatmap.png",
            "repairMask": "stage-1-repair-mask.png",
            "review": "stage-1-review.png",
        },
        "copiedAcceptedPngBytes": {"automatedReview": True, "automatedRgba": True},
        "pieces": [
            {"id": identifier, "index": index, "material": material}
            for identifier, index, material in policy.pieces
        ],
        "profile": {
            "id": policy.profile_id,
            "material": policy.material,
            "pieceCount": policy.piece_count,
            "productId": policy.product_id,
        },
        "source": {
            "decodedRgbSha256": policy.source.pixel_sha256,
            "id": policy.source_id,
            "rawJpegSha256": policy.source.raw_sha256,
        },
        "stage": 1,
        "stage0AcceptanceSha256": policy.stage0_acceptance_sha256,
        "stage0SelectedSourceId": _mapping(
            stage0["selectedSource"], "Stage 0 selected source"
        )["id"],
        "validation": metrics,
    }


def _comparison_metrics(
    automated: np.ndarray,
    manual: _ValidatedImage,
    automated_review: np.ndarray,
    manual_review: _ValidatedImage,
    packaged: _ValidatedImage,
    root: Path,
) -> dict[str, object]:
    rgba, review, packaged_rgba = manual.pixels, manual_review.pixels, packaged.pixels
    rgb_error = np.abs(
        automated[..., :3].astype(np.int16) - rgba[..., :3].astype(np.int16)
    )
    alpha_error = np.abs(
        automated[..., 3].astype(np.int16) - rgba[..., 3].astype(np.int16)
    )
    review_error = np.abs(automated_review.astype(np.int16) - review.astype(np.int16))
    auto_alpha, manual_alpha = automated[..., 3] >= 128, rgba[..., 3] >= 128
    union = int(np.count_nonzero(auto_alpha | manual_alpha))
    auto_rgba_bytes = (root / "stage-1-auto-rgba.png").read_bytes()
    auto_review_bytes = (root / "stage-1-auto-review.png").read_bytes()
    return {
        "alphaIoU": float(np.count_nonzero(auto_alpha & manual_alpha) / union)
        if union
        else 1.0,
        "alphaMae": float(alpha_error.mean()),
        "alphaMaxAbsError": int(alpha_error.max()),
        "automatedEqualsManual": bool(np.array_equal(automated, rgba)),
        "automatedEqualsPackaged": bool(np.array_equal(automated, packaged_rgba)),
        "automatedReviewEqualsManual": bool(np.array_equal(automated_review, review)),
        "automatedReviewPixelSha256": _array_sha256(automated_review),
        "automatedRgbaPixelSha256": _array_sha256(automated),
        "manualEqualsPackaged": bool(np.array_equal(rgba, packaged_rgba)),
        "manualReviewPixelSha256": _array_sha256(review),
        "manualRgbaPixelSha256": _array_sha256(rgba),
        "packagedRgbaPixelSha256": _array_sha256(packaged_rgba),
        "pngFileEquality": {
            "automatedReviewEqualsManual": auto_review_bytes == manual_review.raw_bytes,
            "automatedRgbaEqualsManual": auto_rgba_bytes == manual.raw_bytes,
            "automatedRgbaEqualsPackaged": auto_rgba_bytes == packaged.raw_bytes,
        },
        "pngFileSha256": {
            "automatedReview": _bytes_sha256(auto_review_bytes),
            "automatedRgba": _bytes_sha256(auto_rgba_bytes),
            "manualReview": _bytes_sha256(manual_review.raw_bytes),
            "manualRgba": _bytes_sha256(manual.raw_bytes),
            "packagedRgba": _bytes_sha256(packaged.raw_bytes),
        },
        "reviewRgbMae": float(review_error.mean()),
        "reviewRgbMaxAbsError": int(review_error.max()),
        "rgbMae": float(rgb_error.mean()),
        "rgbMaxAbsError": int(rgb_error.max()),
        "routedEdgeDisplacementPx": _edge_displacement(automated, rgba),
        "shape": list(automated.shape),
        "transparentRgbZero": {
            "automated": _transparent_rgb_is_zero(automated),
            "manual": _transparent_rgb_is_zero(rgba),
            "packaged": _transparent_rgb_is_zero(packaged_rgba),
        },
    }


def _edge_displacement(first: np.ndarray, second: np.ndarray) -> float:
    def edges(rgba: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)
        return (cv2.Canny(rgb, 24, 72) > 0) | (cv2.Canny(rgba[..., 3], 12, 36) > 0)

    first_edges, second_edges = edges(first), edges(second)
    if np.array_equal(first_edges, second_edges):
        return 0.0

    def directed(source: np.ndarray, target: np.ndarray) -> float:
        if not np.any(source) or not np.any(target):
            return float("inf")
        return float(
            cv2.distanceTransform((~target).astype(np.uint8), cv2.DIST_L2, 5)[
                source
            ].max()
        )

    return max(directed(first_edges, second_edges), directed(second_edges, first_edges))


def _side_by_side(automated: np.ndarray, manual: np.ndarray) -> np.ndarray:
    height, width, _ = automated.shape
    canvas = Image.new("RGB", (width * 2 + 72, height + 86), _BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    canvas.paste(Image.fromarray(automated), (24, 54))
    canvas.paste(Image.fromarray(manual), (width + 48, 54))
    draw.text((24, 20), "Stage 1 — automated cleanup", fill=(34, 34, 34), font=font)
    draw.text((width + 48, 20), "Accepted manual cleanup", fill=(34, 34, 34), font=font)
    return np.asarray(canvas)


def _difference_heatmap(automated: np.ndarray, manual: np.ndarray) -> np.ndarray:
    difference = np.max(
        np.abs(automated.astype(np.int16) - manual.astype(np.int16)), axis=2
    ).astype(np.uint8)
    amplified = np.clip(difference.astype(np.uint16) * 16, 0, 255).astype(np.uint8)
    heat = cv2.cvtColor(
        cv2.applyColorMap(amplified, cv2.COLORMAP_TURBO), cv2.COLOR_BGR2RGB
    )
    heat[amplified == 0] = (0, 0, 0)
    canvas = Image.new("RGB", (1040, 323), _BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (20, 18),
        "Stage 1 — amplified absolute RGBA difference (16x; black means exact)",
        fill=(34, 34, 34),
        font=ImageFont.load_default(),
    )
    canvas.paste(Image.fromarray(heat), (20, 44))
    return np.asarray(canvas)


def _repair_mask_image(mask: np.ndarray) -> np.ndarray:
    canvas = np.full((*mask.shape, 3), 255, dtype=np.uint8)
    canvas[mask > 0] = (222, 65, 52)
    return canvas


def _combined_review(
    source: np.ndarray,
    repair_mask: np.ndarray,
    automated_review: np.ndarray,
    manual_review: np.ndarray,
    heatmap: np.ndarray,
) -> np.ndarray:
    panels = (
        ("Registered source", source),
        ("Repair mask", _repair_mask_image(repair_mask)),
        ("Automated cleanup", automated_review),
        ("Accepted manual cleanup", manual_review),
        ("Amplified exact-difference check", heatmap),
    )
    cell_width, cell_height = 1240, 500
    canvas = Image.new("RGB", (cell_width * 2, cell_height * 3), _BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    for index, (title, pixels) in enumerate(panels):
        column, row = index % 2, index // 2
        x, y = column * cell_width + 20, row * cell_height + 20
        image = Image.fromarray(pixels).convert("RGB")
        image.thumbnail((cell_width - 40, cell_height - 64), Image.Resampling.LANCZOS)
        canvas.paste(image, (x, y + 24))
        draw.text((x, y), title, fill=(34, 34, 34), font=font)
    return np.asarray(canvas)


def _write_accepted_bytes(
    path: Path, pixels: np.ndarray, accepted: bytes, mode: str
) -> None:
    with Image.open(BytesIO(accepted)) as image:
        if (
            image.format != "PNG"
            or image.mode != mode
            or not np.array_equal(pixels, np.asarray(image))
        ):
            raise ValueError("refusing to write non-exact accepted output")
    path.write_bytes(accepted)


def _save_png(path: Path, pixels: np.ndarray) -> None:
    Image.fromarray(pixels).save(path, format="PNG", optimize=False, compress_level=9)


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _freeze(value: np.ndarray) -> np.ndarray:
    return np.frombuffer(value.tobytes(), dtype=np.uint8).reshape(value.shape)


def _bytes_sha256(value: bytes) -> str:
    return sha256(value).hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    return sha256(value.tobytes()).hexdigest()


def _transparent_rgb_is_zero(rgba: np.ndarray) -> bool:
    return bool(np.all(rgba[..., :3][rgba[..., 3] == 0] == 0))
