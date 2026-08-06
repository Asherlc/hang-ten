"""Product-neutral Stage 1 cleanup of an approved registered RGBA image."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import tempfile
from types import MappingProxyType
from typing import Protocol

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .generic_stage0 import StageCheckpoint
from .models import ConversionError


@dataclass(frozen=True, slots=True)
class GenericStage1Profile:
    profile_id: str = "generic-photo-cleanup-v1"
    detail_mix: float = 0.65
    tone_cap_lab: float = 5.0


class Stage1RunContext(Protocol):
    root: Path
    manifest: Mapping[str, object]


class GenericStage1Runner:
    stage = 1

    def run(self, context: Stage1RunContext, artifact_root: Path) -> StageCheckpoint:
        return run_generic_stage1(context, artifact_root)


_CANDIDATE_FILES = (
    "stage-1-auto-rgba.png",
    "stage-1-review.png",
    "stage-1-candidate.json",
)
_BACKGROUND = (238, 238, 236)


def clean_registered_rgba(
    registered_rgba: np.ndarray,
    *,
    profile: GenericStage1Profile = GenericStage1Profile(),
) -> np.ndarray:
    """Apply a mild deterministic cleanup while preserving geometry and alpha."""
    if registered_rgba.ndim != 3 or registered_rgba.shape[2] != 4:
        raise ValueError("registered image must be RGBA")
    if registered_rgba.dtype != np.uint8:
        raise ValueError("registered image must use uint8 pixels")
    if not 0.0 <= profile.detail_mix <= 1.0 or profile.tone_cap_lab < 0:
        raise ValueError("generic Stage 1 profile has invalid limits")

    alpha = registered_rgba[..., 3]
    mask = alpha > 0
    if not mask.any():
        raise ConversionError("approved Stage 0 registration has no foreground")

    rgb = registered_rgba[..., :3]
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    # Extend only for filter support, so transparent black cannot darken irregular
    # edges or the gaps between separate product pieces. Output alpha is untouched.
    filled_lab = _nearest_foreground_fill(lab, mask)
    smooth_lab = cv2.bilateralFilter(
        filled_lab,
        d=7,
        sigmaColor=9,
        sigmaSpace=4,
        borderType=cv2.BORDER_REPLICATE,
    )
    mixed_lab = np.rint(
        profile.detail_mix * lab.astype(np.float32)
        + (1.0 - profile.detail_mix) * smooth_lab.astype(np.float32)
    ).clip(0, 255).astype(np.uint8)

    cleaned = np.empty_like(registered_rgba)
    cleaned[..., :3] = cv2.cvtColor(mixed_lab, cv2.COLOR_LAB2RGB)
    cleaned[..., 3] = alpha
    cleaned[~mask, :3] = 0
    return cleaned


def run_generic_stage1(
    context: Stage1RunContext,
    artifact_root: Path,
    *,
    profile: GenericStage1Profile = GenericStage1Profile(),
) -> StageCheckpoint:
    """Clean only the hash-bound Stage 0 acceptance and registered RGBA."""
    if artifact_root.exists():
        raise FileExistsError(f"Stage 1 artifact root already exists: {artifact_root}")
    input_rgba, evidence = _approved_stage0_rgba(context)
    first = clean_registered_rgba(input_rgba, profile=profile)
    second = clean_registered_rgba(input_rgba, profile=profile)
    if first.tobytes() != second.tobytes():
        raise ConversionError("generic Stage 1 cleanup is not deterministic")
    if first.shape != input_rgba.shape or not np.array_equal(first[..., 3], input_rgba[..., 3]):
        raise ConversionError("generic Stage 1 cleanup changed registered geometry")

    temporary_root: Path | None = None
    try:
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent)
        )
        auto_path = temporary_root / "stage-1-auto-rgba.png"
        _write_png(auto_path, first)
        auto_file_hash = _hash_file(auto_path)
        candidate = {
            "inputAcceptance": evidence["acceptance"],
            "inputRegistered": evidence["registered"],
            "profile": asdict(profile),
            "registered": {
                "alphaSha256": sha256(first[..., 3].tobytes()).hexdigest(),
                "fileSha256": auto_file_hash,
                "height": int(first.shape[0]),
                "pixelSha256": sha256(first.tobytes()).hexdigest(),
                "width": int(first.shape[1]),
            },
            "stage": 1,
            "transform": {
                "bilateralDiameter": 7,
                "bilateralSigmaColor": 9,
                "bilateralSigmaSpace": 4,
                "detailMix": profile.detail_mix,
                "smoothMix": 1.0 - profile.detail_mix,
                "toneCorrectionApplied": False,
            },
        }
        candidate_path = temporary_root / "stage-1-candidate.json"
        _write_json(candidate_path, candidate)
        review_path = temporary_root / "stage-1-review.png"
        _write_png(review_path, _review_image(input_rgba, first))
        hashes = {name: _hash_file(temporary_root / name) for name in _CANDIDATE_FILES}
        _write_json(temporary_root / "candidate-hashes.json", hashes)
        temporary_root.replace(artifact_root)
        return StageCheckpoint(
            stage=1,
            artifact_root=artifact_root,
            candidate_hashes=MappingProxyType(hashes),
            review_path=artifact_root / "stage-1-review.png",
            machine_passed=True,
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def _approved_stage0_rgba(
    context: Stage1RunContext,
) -> tuple[np.ndarray, dict[str, Mapping[str, object]]]:
    stages = context.manifest.get("stages")
    if not isinstance(stages, list) or not stages or not isinstance(stages[0], Mapping):
        raise ConversionError("Stage 0 checkpoint is missing")
    record = stages[0]
    if record.get("stage") != 0 or record.get("status") != "approved":
        raise ConversionError("Stage 0 checkpoint is not approved")

    acceptance_path = _inside_root(context.root, record.get("acceptancePath"))
    if _hash_file(acceptance_path) != record.get("acceptanceSha256"):
        raise ConversionError("Stage 0 acceptance does not match its recorded hash")
    acceptance = _read_json(acceptance_path)
    if (
        acceptance.get("stage") != 0
        or acceptance.get("runIdentitySha256") != context.manifest.get("runIdentitySha256")
    ):
        raise ConversionError("Stage 0 acceptance is inconsistent with the run")

    artifact_root = _inside_root(context.root, record.get("artifactRoot"))
    registered_path = artifact_root / "stage-0-registered-rgba.png"
    registered = acceptance.get("registered")
    candidate_hashes = acceptance.get("candidateHashes")
    if not isinstance(registered, Mapping) or not isinstance(candidate_hashes, Mapping):
        raise ConversionError("Stage 0 acceptance is missing registered evidence")
    actual_file_hash = _hash_file(registered_path)
    if (
        actual_file_hash != registered.get("fileSha256")
        or actual_file_hash != candidate_hashes.get(registered_path.name)
    ):
        raise ConversionError("Stage 0 registered image does not match its acceptance")

    with Image.open(registered_path) as image:
        if image.mode != "RGBA":
            raise ConversionError("Stage 0 registered image is not RGBA")
        rgba = np.asarray(image, dtype=np.uint8)
    if (
        rgba.shape[1] != registered.get("width")
        or rgba.shape[0] != registered.get("height")
        or sha256(rgba.tobytes()).hexdigest() != registered.get("pixelSha256")
    ):
        raise ConversionError("Stage 0 registered pixels do not match their acceptance")

    acceptance_evidence: Mapping[str, object] = {
        "path": acceptance_path.relative_to(context.root).as_posix(),
        "sha256": record["acceptanceSha256"],
    }
    registered_evidence: Mapping[str, object] = {
        "alphaSha256": sha256(rgba[..., 3].tobytes()).hexdigest(),
        "fileSha256": actual_file_hash,
        "height": int(rgba.shape[0]),
        "path": registered_path.relative_to(context.root).as_posix(),
        "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
        "width": int(rgba.shape[1]),
    }
    return rgba, {"acceptance": acceptance_evidence, "registered": registered_evidence}


def _nearest_foreground_fill(lab: np.ndarray, mask: np.ndarray) -> np.ndarray:
    if mask.all():
        return lab.copy()
    _, labels = cv2.distanceTransformWithLabels(
        (~mask).astype(np.uint8),
        cv2.DIST_L2,
        cv2.DIST_MASK_3,
        labelType=cv2.DIST_LABEL_PIXEL,
    )
    lookup = np.zeros((int(labels.max()) + 1, 3), dtype=np.uint8)
    lookup[labels[mask]] = lab[mask]
    return lookup[labels]


def _review_image(approved: np.ndarray, candidate: np.ndarray) -> np.ndarray:
    height, width = approved.shape[:2]
    margin = 50
    label_height = 44
    gap = 42
    canvas = Image.new(
        "RGB",
        (width + 2 * margin, 2 * height + 2 * label_height + gap + 2 * margin),
        _BACKGROUND,
    )
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    top_y = margin + label_height
    bottom_label_y = top_y + height + gap
    bottom_y = bottom_label_y + label_height
    draw.text((margin, margin + 14), "Approved Stage 0 — registered photo", fill=(32, 32, 32), font=font)
    draw.text((margin, bottom_label_y + 14), "Stage 1 — mild photo cleanup candidate", fill=(32, 32, 32), font=font)
    _paste_rgba(canvas, approved, (margin, top_y))
    _paste_rgba(canvas, candidate, (margin, bottom_y))
    return np.asarray(canvas, dtype=np.uint8)


def _paste_rgba(canvas: Image.Image, rgba: np.ndarray, origin: tuple[int, int]) -> None:
    product = Image.fromarray(rgba, "RGBA")
    canvas.paste(product, origin, product)


def _inside_root(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ConversionError("Stage 0 evidence path is invalid")
    path = (root / relative).resolve()
    resolved_root = root.resolve()
    if path == resolved_root or resolved_root not in path.parents:
        raise ConversionError("Stage 0 evidence path escapes the run")
    return path


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ConversionError(f"could not read Stage 0 evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise ConversionError(f"Stage 0 evidence is not an object: {path.name}")
    return value


def _write_png(path: Path, pixels: np.ndarray) -> None:
    Image.fromarray(pixels).save(path, format="PNG", optimize=False, compress_level=9)


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _hash_file(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ConversionError(f"could not read Stage 0 evidence: {path.name}") from error
