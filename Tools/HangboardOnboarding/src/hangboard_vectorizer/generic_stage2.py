"""Generic, proposal-driven Stage 2 semantic grip capture.

The generic algorithm owns validation, deterministic refinement, labeling, and
rendering.  Product topology and coarse geometry live in a run-local proposal,
which may be produced by a file, a human, or a model-backed provider.
"""

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
from .semantic_cache import CacheTelemetry, SemanticCache, invoke_with_semantic_cache
from .semantic_vision import (
    ModelInvocation,
    SemanticVisionProvider,
    SemanticVisionRequest,
    SemanticVisionResponse,
)


@dataclass(frozen=True, slots=True)
class GenericStage2Profile:
    profile_id: str = "generic-semantic-capture-v1"
    aperture_padding: int = 8
    minimum_region_pixels: int = 120


class Stage2RunContext(Protocol):
    root: Path
    manifest: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class SemanticProposalRequest:
    """The approved pixels and provenance available to one semantic capture."""

    context: Stage2RunContext
    registered_rgba: np.ndarray
    input_evidence: Mapping[str, Mapping[str, object]]

    def __post_init__(self) -> None:
        if (
            self.registered_rgba.ndim != 3
            or self.registered_rgba.shape[2] != 4
            or self.registered_rgba.dtype != np.uint8
        ):
            raise ValueError("semantic proposal requests require uint8 RGBA pixels")
        pixels = self.registered_rgba.view()
        pixels.setflags(write=False)
        object.__setattr__(self, "registered_rgba", pixels)
        object.__setattr__(
            self,
            "input_evidence",
            MappingProxyType(
                {name: MappingProxyType(dict(value)) for name, value in self.input_evidence.items()}
            ),
        )


class CompactProposalRefiner(Protocol):
    """Structural seam for compact-response geometry refinement."""

    def refine(
        self,
        registered_rgba: np.ndarray,
        response: SemanticVisionResponse,
    ) -> object: ...


@dataclass(frozen=True, slots=True)
class SemanticProposalCapture:
    """One provider response, separated from repeatable local raster work."""

    proposal: Mapping[str, object]
    raw_bytes: bytes
    content_type: str
    identity: Mapping[str, object]
    invocation: ModelInvocation | None = None
    cache: CacheTelemetry | None = None
    emit_response_evidence: bool = False
    compact_response: SemanticVisionResponse | None = None
    compact_refiner: CompactProposalRefiner | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.proposal, Mapping):
            raise ValueError("semantic proposal capture content must be an object")
        if not isinstance(self.raw_bytes, bytes):
            raise ValueError("semantic proposal capture bytes must be immutable")
        if not isinstance(self.content_type, str) or not self.content_type:
            raise ValueError("semantic proposal capture content type is required")
        if not isinstance(self.identity, Mapping):
            raise ValueError("semantic proposal capture identity must be an object")
        if self.invocation is not None and not isinstance(self.invocation, ModelInvocation):
            raise ValueError("semantic proposal capture invocation must be typed telemetry")
        if self.cache is not None and not isinstance(self.cache, CacheTelemetry):
            raise ValueError("semantic proposal capture cache must be typed telemetry")
        if not isinstance(self.emit_response_evidence, bool):
            raise ValueError("semantic proposal capture evidence flag must be boolean")
        if (self.compact_response is None) != (self.compact_refiner is None):
            raise ValueError("compact response and refiner must be captured together")
        if self.compact_response is not None:
            if not isinstance(self.compact_response, SemanticVisionResponse):
                raise ValueError("semantic proposal compact response must be typed")
            if self.raw_bytes != self.compact_response.raw_bytes:
                raise ValueError("semantic proposal bytes do not match compact response evidence")
        try:
            json.dumps(dict(self.identity), ensure_ascii=True, sort_keys=True)
        except (TypeError, ValueError) as error:
            raise ValueError("semantic proposal capture identity must be JSON-serializable") from error
        object.__setattr__(self, "proposal", MappingProxyType(dict(self.proposal)))
        object.__setattr__(self, "raw_bytes", bytes(self.raw_bytes))
        object.__setattr__(self, "identity", MappingProxyType(dict(self.identity)))

    @property
    def records_response_evidence(self) -> bool:
        """Compact captures carry telemetry; file-only captures retain legacy output."""
        return self.emit_response_evidence or self.invocation is not None or self.cache is not None


class SemanticProposalProvider(Protocol):
    """Seam for file-, human-, or model-produced semantic proposals."""

    def capture(self, request: SemanticProposalRequest) -> SemanticProposalCapture: ...


@dataclass(frozen=True, slots=True)
class FileSemanticProposalProvider:
    relative_path: str = "inputs/stage-2-semantic-proposal.json"

    def capture(self, request: SemanticProposalRequest) -> SemanticProposalCapture:
        path = _inside_root(request.context.root, self.relative_path)
        raw_bytes = _read_bytes(path)
        proposal = _parse_json_object(raw_bytes, path)
        return SemanticProposalCapture(
            proposal=proposal,
            raw_bytes=raw_bytes,
            content_type="application/json",
            identity={
                "path": path.relative_to(request.context.root).as_posix(),
                "provider": proposal.get("provider", "file"),
                "sha256": sha256(raw_bytes).hexdigest(),
            },
        )


@dataclass(frozen=True, slots=True)
class CachedSemanticProposalProvider:
    """Adapt an immutable compact semantic cache to generic Stage 2 capture."""

    cache: SemanticCache
    client: SemanticVisionProvider
    proposal: Mapping[str, object]
    refiner: CompactProposalRefiner
    prompt_bytes: bytes
    provider_id: str
    model_id: str
    request_kind: str = "full-board"
    cache_only: bool = False

    def capture(self, request: SemanticProposalRequest) -> SemanticProposalCapture:
        semantic_request = SemanticVisionRequest(
            registered_pixel_sha256=sha256(request.registered_rgba.tobytes()).hexdigest(),
            prompt_bytes=self.prompt_bytes,
            provider_id=self.provider_id,
            model_id=self.model_id,
            request_kind=self.request_kind,
        )
        result = invoke_with_semantic_cache(
            self.cache,
            semantic_request,
            self.client,
            cache_only=self.cache_only,
        )
        return SemanticProposalCapture(
            proposal=self.proposal,
            raw_bytes=result.response.raw_bytes,
            content_type="application/json",
            identity={
                "modelId": self.model_id,
                "promptSha256": semantic_request.prompt_sha256,
                "provider": self.provider_id,
                "registeredPixelSha256": semantic_request.registered_pixel_sha256,
                "requestKind": self.request_kind,
                "responseSha256": result.response.response_sha256,
                "schemaVersion": semantic_request.schema_version,
            },
            invocation=result.model_invocation,
            cache=result.cache,
            emit_response_evidence=True,
            compact_response=result.response,
            compact_refiner=self.refiner,
        )


@dataclass(frozen=True, slots=True)
class GenericStage2Runner:
    provider: SemanticProposalProvider = FileSemanticProposalProvider()
    profile: GenericStage2Profile = GenericStage2Profile()
    stage: int = 2

    def run(self, context: Stage2RunContext, artifact_root: Path) -> StageCheckpoint:
        return run_generic_stage2(
            context,
            artifact_root,
            provider=self.provider,
            profile=self.profile,
        )


_CANDIDATE_FILES = (
    "stage-2-semantic-capture.json",
    "stage-2-labels.png",
    "stage-2-regions.json",
    "stage-2-review.png",
    "stage-2-candidate.json",
)
_GENERATED_ARTIFACT_NAMES = frozenset(
    (*_CANDIDATE_FILES[1:], "candidate-hashes.json")
)
_TYPE_COLORS: Mapping[str, tuple[int, int, int]] = MappingProxyType(
    {
        "jug": (238, 105, 54),
        "sloper": (25, 159, 174),
        "edge": (117, 79, 194),
        "pocket": (218, 60, 132),
    }
)


def run_generic_stage2(
    context: Stage2RunContext,
    artifact_root: Path,
    *,
    provider: SemanticProposalProvider = FileSemanticProposalProvider(),
    profile: GenericStage2Profile = GenericStage2Profile(),
) -> StageCheckpoint:
    """Capture selectable grip regions from an accepted Stage 1 raster."""
    if artifact_root.exists():
        raise FileExistsError(f"Stage 2 artifact root already exists: {artifact_root}")
    rgba, input_evidence = _approved_stage1_rgba(context)
    capture = provider.capture(SemanticProposalRequest(context, rgba, input_evidence))
    if not isinstance(capture, SemanticProposalCapture):
        raise ConversionError("Stage 2 semantic provider returned an unsupported capture")
    proposal = dict(capture.proposal)
    proposal_hash = sha256(capture.raw_bytes).hexdigest()
    _validate_proposal(proposal, context, rgba, input_evidence)

    labels, regions = _capture_geometry(capture, rgba, proposal, profile)
    labels_again, regions_again = _capture_geometry(capture, rgba, proposal, profile)
    if labels.tobytes() != labels_again.tobytes() or regions != regions_again:
        raise ConversionError("generic Stage 2 capture is not deterministic")

    capture_document = {
        "canvas": {"height": int(rgba.shape[0]), "width": int(rgba.shape[1])},
        "inputAcceptance": input_evidence["acceptance"],
        "inputRaster": input_evidence["registered"],
        "profile": asdict(profile),
        "proposal": dict(capture.identity),
        "regionCount": len(regions),
        "stage": 2,
    }
    semantic_response: dict[str, object] | None = None
    semantic_evidence_response: dict[str, object] | None = None
    candidate_files = list(_CANDIDATE_FILES)
    preserved_files = {
        "stage-2-semantic-capture.json": _json_bytes(capture_document),
    }
    if capture.records_response_evidence:
        response_name = "stage-2-semantic-response.json"
        semantic_response = {
            "contentType": capture.content_type,
            "fileSha256": proposal_hash,
            "path": response_name,
        }
        semantic_evidence_response = {
            "contentType": capture.content_type,
            "path": response_name,
            "sha256": proposal_hash,
        }
        candidate_files.append(response_name)
        preserved_files[response_name] = capture.raw_bytes
        preserved_files["stage-2-semantic-evidence.json"] = _json_bytes(
            {
                "cache": _cache_document(capture.cache),
                "identity": dict(capture.identity),
                "invocation": _invocation_document(capture.invocation),
                "response": semantic_evidence_response,
                "stage": 2,
            }
        )
    region_document = {
        "canvas": {"height": int(rgba.shape[0]), "width": int(rgba.shape[1])},
        "labelEncoding": "uint16-region-id",
        "regions": regions,
        "stage": 2,
    }
    candidate = {
        "inputAcceptance": input_evidence["acceptance"],
        "inputRegistered": input_evidence["registered"],
        "profile": asdict(profile),
        "proposalSha256": proposal_hash,
        "stage": 2,
    }
    if semantic_response is not None:
        candidate["semanticResponse"] = semantic_response

    temporary_root: Path | None = None
    try:
        artifact_root.parent.mkdir(parents=True, exist_ok=True)
        temporary_root = Path(
            tempfile.mkdtemp(prefix=f".{artifact_root.name}.tmp-", dir=artifact_root.parent)
        )
        hashes = build_stage2_artifacts(
            temporary_root,
            rgba=rgba,
            labels=labels,
            region_document=region_document,
            candidate=candidate,
            preserved_files=preserved_files,
            candidate_files=tuple(candidate_files),
        )
        temporary_root.replace(artifact_root)
        return StageCheckpoint(
            stage=2,
            artifact_root=artifact_root,
            candidate_hashes=MappingProxyType(hashes),
            review_path=artifact_root / "stage-2-review.png",
            machine_passed=True,
        )
    except Exception:
        if temporary_root is not None:
            shutil.rmtree(temporary_root, ignore_errors=True)
        raise


def build_stage2_artifacts(
    artifact_root: Path,
    *,
    rgba: np.ndarray,
    labels: np.ndarray,
    region_document: Mapping[str, object],
    candidate: Mapping[str, object],
    preserved_files: Mapping[str, bytes],
    candidate_files: tuple[str, ...],
) -> dict[str, str]:
    """Write one complete deterministic Stage 2 candidate into an empty directory."""
    if any(artifact_root.iterdir()):
        raise FileExistsError(f"Stage 2 artifact root is not empty: {artifact_root}")
    regions = region_document["regions"]
    if not isinstance(regions, list):
        raise ConversionError("Stage 2 region document is invalid")
    for name, content in preserved_files.items():
        _validate_artifact_name(name)
        if name in _GENERATED_ARTIFACT_NAMES:
            raise ConversionError(f"Stage 2 preserved artifact name is reserved: {name}")
        (artifact_root / name).write_bytes(content)

    label_path = artifact_root / "stage-2-labels.png"
    regions_path = artifact_root / "stage-2-regions.json"
    _write_label_png(label_path, labels)
    _write_json(regions_path, region_document)
    _write_png(artifact_root / "stage-2-review.png", _review_image(rgba, labels, regions))

    candidate_document = dict(candidate)
    candidate_document.update(
        {
            "regionCount": len(regions),
            "regions": {
                "fileSha256": _hash_file(regions_path),
                "path": "stage-2-regions.json",
            },
            "registered": {
                "fileSha256": _hash_file(label_path),
                "height": int(labels.shape[0]),
                "labelSha256": sha256(labels.tobytes()).hexdigest(),
                "path": "stage-2-labels.png",
                "width": int(labels.shape[1]),
            },
            "stage": 2,
        }
    )
    _write_json(artifact_root / "stage-2-candidate.json", candidate_document)
    hashes = _candidate_hashes(artifact_root, candidate_files)
    _write_json(artifact_root / "candidate-hashes.json", hashes)
    _verify_candidate_hashes(artifact_root, hashes)
    return hashes


def _capture_geometry(
    capture: SemanticProposalCapture,
    rgba: np.ndarray,
    proposal: Mapping[str, object],
    profile: GenericStage2Profile,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    if capture.compact_response is None or capture.compact_refiner is None:
        return rasterize_semantic_proposal(rgba, proposal, profile=profile)
    result = capture.compact_refiner.refine(rgba, capture.compact_response)
    labels = getattr(result, "labels", None)
    raw_regions = getattr(result, "regions", None)
    if not isinstance(labels, np.ndarray) or labels.dtype != np.uint16:
        raise ConversionError("compact Stage 2 refinement did not return uint16 labels")
    if labels.shape != rgba.shape[:2]:
        raise ConversionError("compact Stage 2 labels do not match registered pixels")
    if not isinstance(raw_regions, tuple) or not all(
        isinstance(region, Mapping) for region in raw_regions
    ):
        raise ConversionError("compact Stage 2 refinement did not return typed regions")
    regions = [dict(region) for region in raw_regions]
    hints = capture.compact_response.hints
    if len(regions) != len(hints):
        raise ConversionError("compact Stage 2 inventory does not match refined regions")
    expected_ids = set(range(1, len(regions) + 1))
    actual_ids = {int(value) for value in np.unique(labels) if int(value) != 0}
    if actual_ids != expected_ids:
        raise ConversionError("compact Stage 2 label inventory is incomplete")
    for expected_id, (region, hint) in enumerate(zip(regions, hints, strict=True), start=1):
        if region.get("id") != expected_id or region.get("type") != hint.grip_type:
            raise ConversionError("compact Stage 2 refined region semantics changed")
        mask = labels == expected_id
        if int(mask.sum()) < profile.minimum_region_pixels:
            raise ConversionError(f"Stage 2 region {expected_id} is too small")
        count, _components = cv2.connectedComponents(mask.astype(np.uint8))
        if count != 2:
            raise ConversionError(f"Stage 2 region {expected_id} is not connected")
        if region.get("areaPixels") != int(mask.sum()):
            raise ConversionError("compact Stage 2 refined region area changed")
    return labels, regions


def rasterize_semantic_proposal(
    rgba: np.ndarray,
    proposal: Mapping[str, object],
    *,
    profile: GenericStage2Profile = GenericStage2Profile(),
) -> tuple[np.ndarray, list[dict[str, object]]]:
    """Refine and rasterize an already validated product-specific proposal."""
    if rgba.ndim != 3 or rgba.shape[2] != 4 or rgba.dtype != np.uint8:
        raise ValueError("Stage 2 input must be a uint8 RGBA image")
    alpha = rgba[..., 3] > 0
    lab = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2LAB)
    raw_regions = proposal.get("regions")
    if not isinstance(raw_regions, list):
        raise ConversionError("Stage 2 proposal regions must be a list")

    labels = np.zeros(alpha.shape, dtype=np.uint16)
    regions: list[dict[str, object]] = []
    for expected_id, raw in enumerate(raw_regions, start=1):
        if not isinstance(raw, Mapping):
            raise ConversionError("Stage 2 proposal region must be an object")
        region_id = raw.get("id")
        if region_id != expected_id:
            raise ConversionError("Stage 2 proposal region IDs must be stable and contiguous")
        kind = raw.get("type")
        if kind not in _TYPE_COLORS:
            raise ConversionError(f"unsupported Stage 2 grip type: {kind}")
        geometry = raw.get("geometry")
        if not isinstance(geometry, Mapping):
            raise ConversionError("Stage 2 proposal region geometry is missing")
        mode = geometry.get("mode")
        if mode == "aperture":
            mask = _refine_aperture(lab, alpha, geometry, profile)
        elif mode == "surface":
            mask = _surface_mask(alpha, geometry)
        else:
            raise ConversionError(f"unsupported Stage 2 geometry mode: {mode}")
        mask &= labels == 0
        area = int(mask.sum())
        if area < profile.minimum_region_pixels:
            raise ConversionError(f"Stage 2 region {region_id} is too small")
        count, components = cv2.connectedComponents(mask.astype(np.uint8))
        if count != 2:
            raise ConversionError(f"Stage 2 region {region_id} is not connected")
        labels[mask] = region_id
        ys, xs = np.nonzero(mask)
        contour = _largest_contour(mask)
        metadata = raw.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ConversionError("Stage 2 region metadata must be an object")
        anchor = raw.get("anchor")
        if not _point(anchor):
            anchor = [int(np.median(xs)), int(np.median(ys))]
        if labels[int(anchor[1]), int(anchor[0])] != region_id:
            anchor = [int(np.median(xs)), int(np.median(ys))]
        regions.append(
            {
                "anchor": [int(anchor[0]), int(anchor[1])],
                "areaPixels": area,
                "bounds": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
                "contour": [[int(point[0][0]), int(point[0][1])] for point in contour],
                "id": region_id,
                "key": raw.get("key"),
                "metadata": dict(metadata),
                "type": kind,
            }
        )
    return labels, regions


def _refine_aperture(
    lab: np.ndarray,
    alpha: np.ndarray,
    geometry: Mapping[str, object],
    profile: GenericStage2Profile,
) -> np.ndarray:
    bbox = geometry.get("bbox")
    anchor = geometry.get("anchor")
    if not _box(bbox) or not _point(anchor):
        raise ConversionError("aperture geometry requires bbox and anchor")
    height, width = alpha.shape
    x0, y0, x1, y1 = (int(value) for value in bbox)
    padding = int(geometry.get("padding", profile.aperture_padding))
    xx0, yy0 = max(0, x0 - padding), max(0, y0 - padding)
    xx1, yy1 = min(width, x1 + padding + 1), min(height, y1 + padding + 1)
    crop = lab[yy0:yy1, xx0:xx1, 0]
    if crop.size == 0:
        raise ConversionError("aperture geometry is outside the canvas")
    blurred = cv2.GaussianBlur(crop, (5, 5), 0)
    _threshold, binary = cv2.threshold(
        blurred, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    binary &= alpha[yy0:yy1, xx0:xx1].astype(np.uint8) * 255
    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)),
    )
    binary = cv2.morphologyEx(
        binary,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    count, components, stats, centroids = cv2.connectedComponentsWithStats((binary > 0).astype(np.uint8))
    local_anchor = (int(anchor[0]) - xx0, int(anchor[1]) - yy0)
    selected = 0
    if 0 <= local_anchor[0] < binary.shape[1] and 0 <= local_anchor[1] < binary.shape[0]:
        selected = int(components[local_anchor[1], local_anchor[0]])
    if selected == 0 and count > 1:
        distances = [
            (float((centroids[index][0] - local_anchor[0]) ** 2 + (centroids[index][1] - local_anchor[1]) ** 2), index)
            for index in range(1, count)
        ]
        selected = min(distances)[1]
    local = components == selected
    if selected == 0 or int(local.sum()) < profile.minimum_region_pixels:
        local = _rounded_box_mask(binary.shape, (x0 - xx0, y0 - yy0, x1 - xx0, y1 - yy0))
    else:
        # A dark knot or logo can be connected to the recess by its shadow.  The
        # captured mouth bounds are the semantic guardrail; refinement may snap
        # inward to image seams but never grow a tail beyond that local capture.
        guard = _rounded_box_mask(
            binary.shape,
            (x0 - xx0, y0 - yy0, x1 - xx0, y1 - yy0),
        )
        local &= guard
    local = cv2.morphologyEx(
        local.astype(np.uint8),
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)),
    ).astype(bool)
    local_count, local_labels, local_stats, _ = cv2.connectedComponentsWithStats(local.astype(np.uint8))
    local_selected = 0
    if 0 <= local_anchor[0] < local.shape[1] and 0 <= local_anchor[1] < local.shape[0]:
        local_selected = int(local_labels[local_anchor[1], local_anchor[0]])
    if local_selected == 0 and local_count > 1:
        local_selected = 1 + int(np.argmax(local_stats[1:, cv2.CC_STAT_AREA]))
    local = local_labels == local_selected
    local_ys, local_xs = np.nonzero(local)
    if len(local_xs):
        # The local image seam determines the final extents.  Reconstructing a
        # smooth mouth from those extents removes wood-grain and knot spurs while
        # retaining the photographed size and position.
        local = _rounded_box_mask(
            local.shape,
            (
                int(local_xs.min()),
                int(local_ys.min()),
                int(local_xs.max()),
                int(local_ys.max()),
            ),
        )
    result = np.zeros(alpha.shape, dtype=bool)
    result[yy0:yy1, xx0:xx1] = local
    result &= alpha
    return result


def _surface_mask(alpha: np.ndarray, geometry: Mapping[str, object]) -> np.ndarray:
    polygon = geometry.get("polygon")
    if not isinstance(polygon, list) or len(polygon) < 3 or not all(_point(point) for point in polygon):
        raise ConversionError("surface geometry requires a polygon")
    points = np.asarray(polygon, dtype=np.int32)
    mask = np.zeros(alpha.shape, dtype=np.uint8)
    cv2.fillPoly(mask, [points], 1, lineType=cv2.LINE_8)
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
    )
    return (mask > 0) & alpha


def _review_image(
    rgba: np.ndarray,
    labels: np.ndarray,
    regions: list[dict[str, object]],
) -> np.ndarray:
    height, width = labels.shape
    legend_height = 66
    base = Image.new("RGB", (width, height + legend_height), (246, 245, 242))
    product = Image.fromarray(rgba, "RGBA")
    base.paste(product, (0, 0), product)
    overlay = np.zeros((height + legend_height, width, 4), dtype=np.uint8)
    for region in regions:
        mask = labels == region["id"]
        color = _TYPE_COLORS[str(region["type"])]
        overlay[:height][mask, :3] = color
        overlay[:height][mask, 3] = 92
    base = Image.alpha_composite(base.convert("RGBA"), Image.fromarray(overlay, "RGBA"))
    draw = ImageDraw.Draw(base)
    font = _font(13, bold=True)
    small = _font(12)
    for region in regions:
        region_id = int(region["id"])
        mask = (labels == region_id).astype(np.uint8)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        color = _TYPE_COLORS[str(region["type"])]
        outline = tuple(max(0, channel - 82) for channel in color) + (255,)
        for contour in contours:
            points = [(int(point[0][0]), int(point[0][1])) for point in contour]
            if len(points) >= 2:
                draw.line(points + [points[0]], fill=outline, width=2, joint="curve")
        x, y = (int(value) for value in region["anchor"])
        radius = 10
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(28, 28, 28, 235), outline=(255, 255, 255, 255), width=1)
        text = str(region_id)
        box = draw.textbbox((0, 0), text, font=font)
        draw.text((x - (box[2] - box[0]) / 2, y - (box[3] - box[1]) / 2 - 1), text, font=font, fill=(255, 255, 255, 255))

    legend_y = height
    draw.rectangle((0, legend_y, width, height + legend_height), fill=(246, 245, 242, 255))
    draw.line((0, legend_y, width, legend_y), fill=(204, 201, 194, 255), width=1)
    draw.text(
        (18, legend_y + 10),
        f"{len(regions)} independently selectable grip regions",
        font=font,
        fill=(32, 32, 32, 255),
    )
    x = 18
    for kind in ("jug", "sloper", "edge", "pocket"):
        color = _TYPE_COLORS[kind]
        y = legend_y + 42
        draw.rounded_rectangle((x, y - 7, x + 14, y + 7), radius=4, fill=color + (210,))
        draw.text((x + 21, y - 8), kind, font=small, fill=(48, 48, 48, 255))
        x += 112
    draw.text((520, legend_y + 34), "Numbers follow top, middle, then bottom — left to right", font=small, fill=(75, 75, 75, 255))
    return np.asarray(base.convert("RGB"), dtype=np.uint8)


def _approved_stage1_rgba(
    context: Stage2RunContext,
) -> tuple[np.ndarray, dict[str, Mapping[str, object]]]:
    stages = context.manifest.get("stages")
    if not isinstance(stages, list) or len(stages) < 2 or not isinstance(stages[1], Mapping):
        raise ConversionError("Stage 1 checkpoint is missing")
    record = stages[1]
    if record.get("stage") != 1 or record.get("status") != "approved":
        raise ConversionError("Stage 1 checkpoint is not approved")
    acceptance_path = _inside_root(context.root, record.get("acceptancePath"))
    if _hash_file(acceptance_path) != record.get("acceptanceSha256"):
        raise ConversionError("Stage 1 acceptance does not match its recorded hash")
    acceptance = _read_json(acceptance_path)
    if acceptance.get("stage") != 1 or acceptance.get("runIdentitySha256") != context.manifest.get("runIdentitySha256"):
        raise ConversionError("Stage 1 acceptance is inconsistent with the run")
    registered = acceptance.get("registered")
    if not isinstance(registered, Mapping):
        raise ConversionError("Stage 1 acceptance is missing registered evidence")
    raster_path = _inside_root(context.root, registered.get("path"))
    if _hash_file(raster_path) != registered.get("fileSha256"):
        raise ConversionError("Stage 1 raster does not match its acceptance")
    with Image.open(raster_path) as image:
        if image.mode != "RGBA":
            raise ConversionError("Stage 1 raster is not RGBA")
        rgba = np.asarray(image, dtype=np.uint8)
    if sha256(rgba.tobytes()).hexdigest() != registered.get("pixelSha256"):
        raise ConversionError("Stage 1 pixels do not match their acceptance")
    acceptance_evidence: Mapping[str, object] = {
        "path": acceptance_path.relative_to(context.root).as_posix(),
        "sha256": record["acceptanceSha256"],
    }
    registered_evidence: Mapping[str, object] = {
        "alphaSha256": sha256(rgba[..., 3].tobytes()).hexdigest(),
        "fileSha256": registered["fileSha256"],
        "height": int(rgba.shape[0]),
        "path": raster_path.relative_to(context.root).as_posix(),
        "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
        "width": int(rgba.shape[1]),
    }
    return rgba, {"acceptance": acceptance_evidence, "registered": registered_evidence}


def _validate_proposal(
    proposal: Mapping[str, object],
    context: Stage2RunContext,
    rgba: np.ndarray,
    evidence: Mapping[str, Mapping[str, object]],
) -> None:
    if proposal.get("schemaVersion") != 1:
        raise ConversionError("unsupported Stage 2 proposal schema")
    product = context.manifest.get("product")
    if not isinstance(product, Mapping) or proposal.get("productKey") != product.get("key"):
        raise ConversionError("Stage 2 proposal is for a different product")
    canvas = proposal.get("canvas")
    if canvas != {"height": int(rgba.shape[0]), "width": int(rgba.shape[1])}:
        raise ConversionError("Stage 2 proposal canvas does not match Stage 1")
    if proposal.get("inputAcceptanceSha256") != evidence["acceptance"]["sha256"]:
        raise ConversionError("Stage 2 proposal does not bind the Stage 1 acceptance")
    if proposal.get("inputRasterSha256") != evidence["registered"]["fileSha256"]:
        raise ConversionError("Stage 2 proposal does not bind the Stage 1 raster")
    regions = proposal.get("regions")
    if not isinstance(regions, list) or not regions:
        raise ConversionError("Stage 2 proposal has no regions")


def _largest_contour(mask: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ConversionError("Stage 2 region has no contour")
    contour = max(contours, key=cv2.contourArea)
    epsilon = max(1.0, cv2.arcLength(contour, True) * 0.003)
    return cv2.approxPolyDP(contour, epsilon, True)


def _rounded_box_mask(shape: tuple[int, int], box: tuple[int, int, int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=np.uint8)
    x0, y0, x1, y1 = box
    radius = max(2, min(x1 - x0, y1 - y0) // 3)
    cv2.rectangle(mask, (x0 + radius, y0), (x1 - radius, y1), 1, -1)
    cv2.rectangle(mask, (x0, y0 + radius), (x1, y1 - radius), 1, -1)
    cv2.ellipse(mask, (x0 + radius, y0 + radius), (radius, radius), 0, 0, 360, 1, -1)
    cv2.ellipse(mask, (x1 - radius, y0 + radius), (radius, radius), 0, 0, 360, 1, -1)
    cv2.ellipse(mask, (x0 + radius, y1 - radius), (radius, radius), 0, 0, 360, 1, -1)
    cv2.ellipse(mask, (x1 - radius, y1 - radius), (radius, radius), 0, 0, 360, 1, -1)
    return mask.astype(bool)


def _box(value: object) -> bool:
    return isinstance(value, list) and len(value) == 4 and all(isinstance(item, int) for item in value) and value[0] < value[2] and value[1] < value[3]


def _point(value: object) -> bool:
    return isinstance(value, list) and len(value) == 2 and all(isinstance(item, int) for item in value)


def _inside_root(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ConversionError("Stage 2 evidence path is invalid")
    path = (root / relative).resolve()
    resolved_root = root.resolve()
    if path == resolved_root or resolved_root not in path.parents:
        raise ConversionError("Stage 2 evidence path escapes the run")
    return path


def _read_json(path: Path) -> dict[str, object]:
    return _parse_json_object(_read_bytes(path), path)


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ConversionError(f"could not read Stage 2 evidence: {path.name}") from error


def _parse_json_object(raw_bytes: bytes, path: Path) -> dict[str, object]:
    try:
        value = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ConversionError(f"could not read Stage 2 evidence: {path.name}") from error
    if not isinstance(value, dict):
        raise ConversionError(f"Stage 2 evidence is not an object: {path.name}")
    return value


def _write_label_png(path: Path, labels: np.ndarray) -> None:
    Image.fromarray(labels.astype(np.uint16), mode="I;16").save(
        path, format="PNG", optimize=False, compress_level=9
    )


def _write_png(path: Path, pixels: np.ndarray) -> None:
    Image.fromarray(pixels).save(path, format="PNG", optimize=False, compress_level=9)


def _write_json(path: Path, value: object) -> None:
    path.write_bytes(_json_bytes(value))


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _hash_file(path: Path) -> str:
    try:
        return sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise ConversionError(f"could not read Stage 2 evidence: {path.name}") from error


def _candidate_hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in names:
        _validate_artifact_name(name)
        if name == "candidate-hashes.json" or name in hashes:
            raise ConversionError(f"invalid Stage 2 candidate artifact: {name}")
        path = root / name
        if not path.is_file():
            raise ConversionError(f"missing Stage 2 candidate artifact: {name}")
        hashes[name] = _hash_file(path)
    return hashes


def _verify_candidate_hashes(root: Path, hashes: Mapping[str, str]) -> None:
    recorded = _read_json(root / "candidate-hashes.json")
    if recorded != hashes or any(_hash_file(root / name) != expected for name, expected in hashes.items()):
        raise ConversionError("Stage 2 candidate hash verification failed")


def _validate_artifact_name(name: str) -> None:
    if not isinstance(name, str) or not name or Path(name).name != name:
        raise ConversionError("Stage 2 candidate artifact name is invalid")


def _cache_document(cache: CacheTelemetry | None) -> dict[str, object] | None:
    if cache is None:
        return None
    return {"hit": cache.hit, "modelCalls": cache.model_calls}


def _invocation_document(invocation: ModelInvocation | None) -> dict[str, object] | None:
    return None if invocation is None else invocation.as_document()


def _font(size: int, *, bold: bool = False) -> ImageFont.ImageFont:
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.load_default()
