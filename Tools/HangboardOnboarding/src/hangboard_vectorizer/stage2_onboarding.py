"""Evidence-first, transactional Stage 2 onboarding runner."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Mapping

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .hold_discovery import HoldDiscovery, discover_holds, discovery_identity
from .hold_refinement import HoldDiscoveryProfile
from .semantic_holds import CapturedSemanticGripProvider, PieceDescriptor, SemanticGripProvider
from .simplification import SimplifiedRaster


BEASTMAKER_STAGE1_POLICY_ID = "beastmaker-1000-tulipwood-stage1-v3"


@dataclass(frozen=True, slots=True)
class _Stage1EvidencePolicy:
    policy_id: str
    acceptance_raw_sha256: str
    rgba_file_sha256: str
    rgba_pixel_sha256: str
    product_id: str
    profile_id: str
    material: str
    source_id: str
    source_raw_sha256: str
    source_pixel_sha256: str
    stage0_acceptance_sha256: str
    shape: tuple[int, int, int]


_BEASTMAKER_STAGE1_POLICY = _Stage1EvidencePolicy(
    policy_id=BEASTMAKER_STAGE1_POLICY_ID,
    acceptance_raw_sha256="523a0d3a43fa71173ef0182597098977990d24a49c5463aecfda38b88b4b6290",
    rgba_file_sha256="4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627",
    rgba_pixel_sha256="7268f059f3fd285ff70ad6f016de2df74c1478c370fc8a92879ffa2aef0601cf",
    product_id="beastmaker-1000",
    profile_id="beastmaker-1000-tulipwood-v1",
    material="Tulipwood",
    source_id="official-tulipwood",
    source_raw_sha256="17e9f743f6cbacf27092a5e5073b88633be4e282cc05a656151a4bde8203328f",
    source_pixel_sha256="e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3",
    stage0_acceptance_sha256="a067c62cc1590bf3a57c952258d4c3f791b6c774ebeef624db50566b1cec4039",
    shape=(259, 1000, 4),
)
_STAGE1_POLICIES = {BEASTMAKER_STAGE1_POLICY_ID: _BEASTMAKER_STAGE1_POLICY}


@dataclass(frozen=True, slots=True)
class Stage2EvidenceInputs:
    stage1_acceptance_path: Path
    stage1_rgba_path: Path
    policy_id: str = BEASTMAKER_STAGE1_POLICY_ID


def run_stage2_onboarding(
    evidence: Stage2EvidenceInputs,
    artifact_root: Path,
    *,
    provider: SemanticGripProvider | None = None,
    profile: HoldDiscoveryProfile | None = None,
    oracle_paths: Mapping[str, str] | None = None,
) -> Mapping[str, object]:
    """Generate candidates twice, serialize/hash them, then evaluate."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"stage 2 artifact root already exists: {artifact_root}")
    acceptance, acceptance_raw_sha256, rgba, pieces = _validate_stage1(evidence)
    provider = provider or CapturedSemanticGripProvider()
    profile = profile or HoldDiscoveryProfile()
    raster = SimplifiedRaster(rgba, rgba[..., :3], np.zeros(rgba.shape[:2], dtype=np.uint8))
    first = discover_holds(raster, pieces=pieces, provider=provider, profile=profile)
    second = discover_holds(raster, pieces=pieces, provider=provider, profile=profile)
    if discovery_identity(first) != discovery_identity(second) or first.provider_response.raw_bytes != second.provider_response.raw_bytes:
        raise ValueError("semantic provider or hold tracing is nondeterministic")
    _validate_topology(first)

    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(mkdtemp(prefix=f".{artifact_root.name}.", dir=artifact_root.parent))
    try:
        _write_candidate_bundle(
            temporary, rgba, first, acceptance, acceptance_raw_sha256,
            evidence.policy_id, profile,
        )
        from .stage2_evaluation import evaluate_stage2_candidate
        document = evaluate_stage2_candidate(temporary, oracle_paths=oracle_paths)
        if artifact_root.exists():
            raise FileExistsError(f"stage 2 artifact root already exists: {artifact_root}")
        temporary.rename(artifact_root)
    except Exception:
        rmtree(temporary, ignore_errors=True)
        raise
    return document


def _validate_stage1(
    evidence: Stage2EvidenceInputs,
) -> tuple[dict[str, object], str, np.ndarray, tuple[PieceDescriptor, ...]]:
    policy = _STAGE1_POLICIES.get(evidence.policy_id)
    if policy is None:
        raise ValueError(f"unsupported Stage 1 evidence policy: {evidence.policy_id}")
    if not evidence.stage1_acceptance_path.is_file():
        raise FileNotFoundError(f"required Stage 1 acceptance is missing: {evidence.stage1_acceptance_path}")
    if not evidence.stage1_rgba_path.is_file():
        raise FileNotFoundError(f"required Stage 1 RGBA is missing: {evidence.stage1_rgba_path}")
    raw_acceptance = evidence.stage1_acceptance_path.read_bytes()
    acceptance_raw_sha256 = sha256(raw_acceptance).hexdigest()
    if acceptance_raw_sha256 != policy.acceptance_raw_sha256:
        raise ValueError("Stage 1 acceptance raw identity mismatch")
    try: document = json.loads(raw_acceptance.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error: raise ValueError("Stage 1 acceptance is invalid JSON") from error
    expected_root_fields = {
        "accepted", "artifacts", "copiedAcceptedPngBytes", "pieces",
        "profile", "source", "stage", "stage0AcceptanceSha256",
        "stage0SelectedSourceId", "validation",
    }
    if (
        not isinstance(document, dict)
        or set(document) != expected_root_fields
        or type(document.get("stage")) is not int
        or document.get("stage") != 1
        or document.get("accepted") is not True
    ):
        raise ValueError("Stage 1 acceptance does not approve hold discovery")
    profile_document = document.get("profile")
    source_document = document.get("source")
    if profile_document != {
        "id": policy.profile_id,
        "material": policy.material,
        "pieceCount": 1,
        "productId": policy.product_id,
    }:
        raise ValueError("Stage 1 profile/product contract mismatch")
    if source_document != {
        "decodedRgbSha256": policy.source_pixel_sha256,
        "id": policy.source_id,
        "rawJpegSha256": policy.source_raw_sha256,
    }:
        raise ValueError("Stage 1 source contract mismatch")
    if (
        document.get("stage0AcceptanceSha256") != policy.stage0_acceptance_sha256
        or document.get("stage0SelectedSourceId") != policy.source_id
    ):
        raise ValueError("Stage 1 acceptance chain mismatch")
    artifacts = document.get("artifacts"); validation = document.get("validation"); raw_rgba = evidence.stage1_rgba_path.read_bytes()
    if not isinstance(artifacts, dict) or artifacts.get("automatedRgba") != evidence.stage1_rgba_path.name or not isinstance(validation, dict):
        raise ValueError("Stage 1 acceptance/RGBA contract mismatch")
    expected_file = validation.get("pngFileSha256", {}).get("automatedRgba") if isinstance(validation.get("pngFileSha256"), dict) else None
    if expected_file != policy.rgba_file_sha256 or sha256(raw_rgba).hexdigest() != policy.rgba_file_sha256:
        raise ValueError("Stage 1 RGBA evidence identity mismatch")
    try:
        with Image.open(BytesIO(raw_rgba)) as image:
            if image.format != "PNG" or image.mode != "RGBA": raise ValueError("Stage 1 automated raster must be an RGBA PNG")
            rgba = np.asarray(image).copy()
    except OSError as error: raise ValueError("could not decode Stage 1 RGBA") from error
    if (
        tuple(rgba.shape) != policy.shape
        or validation.get("shape") != list(policy.shape)
        or validation.get("automatedRgbaPixelSha256") != policy.rgba_pixel_sha256
        or sha256(rgba.tobytes()).hexdigest() != policy.rgba_pixel_sha256
    ):
        raise ValueError("Stage 1 RGBA pixel identity mismatch")
    raw_pieces = document.get("pieces")
    if not isinstance(raw_pieces, list) or not raw_pieces: raise ValueError("Stage 1 piece metadata is missing")
    pieces: list[PieceDescriptor] = []
    for value in raw_pieces:
        if not isinstance(value, dict) or set(value) != {"id", "index", "material"}: raise ValueError("unsupported Stage 1 piece metadata")
        pieces.append(PieceDescriptor(value["id"], value["index"], value["material"]))
    if pieces != [PieceDescriptor(policy.product_id, 0, policy.material)]:
        raise ValueError("Stage 1 piece/profile contract mismatch")
    return document, acceptance_raw_sha256, rgba, tuple(pieces)


def _validate_topology(discovery: HoldDiscovery) -> None:
    counts = {kind: sum(hold.grip_type == kind for hold in discovery.holds) for kind in ("pocket", "jug", "sloper")}
    if len(discovery.holds) != 22 or counts != {"pocket": 17, "jug": 2, "sloper": 3}:
        raise ValueError("Stage 2 discovery did not produce the required 22-region topology")
    if tuple(hold.id for hold in discovery.holds) != tuple(f"piece-01-hold-{index:02d}" for index in range(1, 23)):
        raise ValueError("Stage 2 stable generic IDs are invalid")


def _write_candidate_bundle(
    root: Path, rgba: np.ndarray, discovery: HoldDiscovery,
    stage1: Mapping[str, object], stage1_acceptance_raw_sha256: str,
    stage1_policy_id: str, profile: HoldDiscoveryProfile,
) -> None:
    (root / "stage-2-proposals.json").write_bytes(discovery.provider_response.raw_bytes)
    Image.fromarray(rgba, "RGBA").save(root / "stage-2-source-rgba.png", format="PNG", optimize=False, compress_level=9)
    Image.fromarray(discovery.label_raster, mode="I;16").save(root / "stage-2-labels.png", format="PNG", optimize=False, compress_level=9)
    Image.fromarray(discovery.candidate_evidence_rgb).save(root / "stage-2-candidates.png", format="PNG", optimize=False, compress_level=9)
    _write_json(root / "stage-2-auto-regions.json", discovery.regions_document())
    Image.fromarray(_labeled_trace(rgba, discovery)).save(root / "stage-2-auto-regions-labeled.png", format="PNG", optimize=False, compress_level=9)
    generation = {
        "candidateIdentity": discovery_identity(discovery),
        "profile": profile.profile_id,
        "provider": {
            "id": discovery.provider_response.provider_id,
            "inputPixelSha256": discovery.provider_response.input_pixel_sha256,
            "model": discovery.provider_response.model_id,
            "promptId": discovery.provider_response.prompt_id,
            "promptSha256": discovery.provider_response.prompt_sha256,
            "responseSha256": discovery.provider_response.response_sha256,
        },
        "schemaVersion": 1,
        "stage1AcceptanceRawSha256": stage1_acceptance_raw_sha256,
        "stage1AcceptancePolicyId": stage1_policy_id,
        "stage1ChainSha256": stage1["stage0AcceptanceSha256"],
        "stage1PixelSha256": discovery.pixel_sha256,
    }
    _write_json(root / "stage-2-generation.json", generation)
    candidate_names = ("stage-2-proposals.json", "stage-2-source-rgba.png", "stage-2-labels.png", "stage-2-candidates.png", "stage-2-auto-regions.json", "stage-2-auto-regions-labeled.png", "stage-2-generation.json")
    hashes = {name: sha256((root / name).read_bytes()).hexdigest() for name in candidate_names}
    _write_json(root / "stage-2-candidate-hashes.json", {"files": hashes, "schemaVersion": 1})


def _labeled_trace(rgba: np.ndarray, discovery: HoldDiscovery) -> np.ndarray:
    base = rgba[..., :3].copy(); base[rgba[..., 3] < 128] = 245
    palette = ((35, 205, 235), (255, 116, 62), (170, 92, 240))
    blended = base.astype(np.float32)
    for index, hold in enumerate(discovery.holds):
        color = np.asarray(palette[index % len(palette)], dtype=np.float32)
        selected = hold.mask.astype(bool); blended[selected] = blended[selected] * 0.48 + color * 0.52
        boundary = selected & ~(cv2.erode(hold.mask, np.ones((3, 3), np.uint8)) > 0); blended[boundary] = (18, 18, 18)
    image = Image.fromarray(np.clip(blended, 0, 255).astype(np.uint8)); draw = ImageDraw.Draw(image); font = ImageFont.load_default()
    for index, hold in enumerate(discovery.holds, start=1):
        x, y = hold.center; label = str(index); box = draw.textbbox((0, 0), label, font=font); tw, th = box[2] - box[0], box[3] - box[1]
        draw.ellipse((x - tw / 2 - 3, y - th / 2 - 2, x + tw / 2 + 3, y + th / 2 + 2), fill=(255, 255, 255), outline=(10, 10, 10))
        draw.text((x - tw / 2, y - th / 2), label, fill=(5, 5, 5), font=font)
    return np.asarray(image)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
