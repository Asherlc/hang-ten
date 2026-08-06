"""Deterministic refinement and narrowly targeted compact-hint escalation.

Model responses in this module remain geometry-free.  Reviewed geometry is
replayed only after both the registered pixels and every compact hint field
match an independently accepted registration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from types import MappingProxyType
from typing import Protocol

import cv2
import numpy as np

from .generic_stage2 import rasterize_semantic_proposal
from .semantic_cache import SemanticCache, invoke_with_semantic_cache
from .semantic_vision import (
    CompactHoldHint,
    ProviderInvocation,
    SemanticVisionRequest,
    SemanticVisionResponse,
    canonical_json_bytes,
    parse_compact_semantic_response,
)


_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _sha256(value: object, *, name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be a lowercase SHA-256")
    return value


def _validated_rgba(value: np.ndarray) -> np.ndarray:
    if (
        not isinstance(value, np.ndarray)
        or value.dtype != np.uint8
        or value.ndim != 3
        or value.shape[2] != 4
    ):
        raise ValueError("semantic refinement requires uint8 RGBA registered pixels")
    return value


def _validated_response(response: SemanticVisionResponse) -> SemanticVisionResponse:
    if type(response) is not SemanticVisionResponse:
        raise ValueError("semantic refinement requires a typed compact response")
    parsed = parse_compact_semantic_response(response.raw_bytes)
    if parsed != response:
        raise ValueError("typed compact response does not match its wire evidence")
    return parsed


@dataclass(frozen=True, slots=True, eq=False)
class SemanticRefinement:
    """Local pixel geometry produced from one validated compact inventory."""

    labels: np.ndarray
    regions: tuple[Mapping[str, object], ...]

    def __post_init__(self) -> None:
        labels = np.asarray(self.labels)
        if labels.ndim != 2 or labels.dtype != np.uint16:
            raise ValueError("semantic refinement labels must be a uint16 raster")
        frozen = np.frombuffer(labels.tobytes(), dtype=np.uint16).reshape(labels.shape)
        object.__setattr__(self, "labels", frozen)
        object.__setattr__(
            self,
            "regions",
            tuple(MappingProxyType(dict(region)) for region in self.regions),
        )


class CompactGeometryRefiner(Protocol):
    """The geometry boundary: compact hints and registered pixels in, masks out."""

    def refine(
        self,
        registered_rgba: np.ndarray,
        response: SemanticVisionResponse,
    ) -> SemanticRefinement: ...


class RegionAmbiguity(ValueError):
    """A single hint cannot be resolved locally without a corrected compact hint."""

    __slots__ = ("hint_key", "reason", "crop_bounds")

    def __init__(
        self,
        hint_key: str,
        reason: str,
        crop_bounds: tuple[int, int, int, int],
    ) -> None:
        if not isinstance(hint_key, str) or not hint_key:
            raise ValueError("region ambiguity requires a hint key")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("region ambiguity requires a reason")
        if (
            not isinstance(crop_bounds, tuple)
            or len(crop_bounds) != 4
            or any(type(value) is not int for value in crop_bounds)
            or crop_bounds[0] < 0
            or crop_bounds[1] < 0
            or crop_bounds[0] >= crop_bounds[2]
            or crop_bounds[1] >= crop_bounds[3]
        ):
            raise ValueError("region ambiguity requires valid integer crop bounds")
        self.hint_key = hint_key
        self.reason = reason
        self.crop_bounds = crop_bounds
        super().__init__(f"ambiguous semantic region {hint_key}: {reason}")


def compact_response_from_reviewed_proposal(
    proposal: Mapping[str, object],
) -> SemanticVisionResponse:
    """Reduce reviewed proposal semantics to generic ordered 20x8 hints.

    Geometry and accepted labels are deliberately omitted.  Every reviewed
    region is observed independently and receives one sequential generic key;
    this function contains no symmetry or mirroring path.
    """
    if not isinstance(proposal, Mapping):
        raise ValueError("reviewed proposal must be an object")
    canvas = proposal.get("canvas")
    if not isinstance(canvas, Mapping):
        raise ValueError("reviewed proposal canvas is missing")
    width, height = canvas.get("width"), canvas.get("height")
    if type(width) is not int or type(height) is not int or width <= 0 or height <= 0:
        raise ValueError("reviewed proposal canvas must have positive integer dimensions")
    raw_regions = proposal.get("regions")
    if not isinstance(raw_regions, list) or not raw_regions:
        raise ValueError("reviewed proposal must contain regions")

    hints: list[dict[str, object]] = []
    for expected_id, raw in enumerate(raw_regions, start=1):
        if not isinstance(raw, Mapping) or raw.get("id") != expected_id:
            raise ValueError("reviewed proposal region IDs must be contiguous and ordered")
        grip_type = raw.get("type")
        if grip_type not in {"jug", "sloper", "edge", "pocket"}:
            raise ValueError("reviewed proposal contains an unsupported grip type")
        geometry = raw.get("geometry")
        if not isinstance(geometry, Mapping) or geometry.get("mode") not in {
            "aperture", "surface",
        }:
            raise ValueError("reviewed proposal contains an unsupported geometry mode")
        mode = geometry["mode"]
        if (grip_type == "pocket") != (mode == "aperture"):
            raise ValueError("reviewed proposal grip type and visual mode disagree")
        anchor = raw.get("anchor")
        if (
            not isinstance(anchor, list)
            or len(anchor) != 2
            or any(type(value) is not int for value in anchor)
            or not (0 <= anchor[0] < width and 0 <= anchor[1] < height)
        ):
            raise ValueError("reviewed proposal region anchor is outside the canvas")
        piece_index = raw.get("pieceIndex", 0)
        if type(piece_index) is not int or piece_index < 0:
            raise ValueError("reviewed proposal piece index must be nonnegative")
        hints.append({
            "a": [min(19, anchor[0] * 20 // width), min(7, anchor[1] * 8 // height)],
            "k": f"grip-{expected_id:03d}",
            "m": mode,
            "p": piece_index,
            "t": grip_type,
        })
    return parse_compact_semantic_response(canonical_json_bytes({"h": hints}))


@dataclass(frozen=True, slots=True)
class ReviewedRefinementRegistration:
    """One immutable binding from accepted pixels and hints to reviewed geometry."""

    registered_pixel_sha256: str
    compact_response: SemanticVisionResponse
    reviewed_proposal: Mapping[str, object]
    accepted_label_sha256: str
    accepted_regions_file_sha256: str

    def __post_init__(self) -> None:
        _sha256(self.registered_pixel_sha256, name="registered pixel identity")
        _sha256(self.accepted_label_sha256, name="accepted label identity")
        _sha256(self.accepted_regions_file_sha256, name="accepted regions identity")
        response = _validated_response(self.compact_response)
        try:
            proposal = json.loads(json.dumps(dict(self.reviewed_proposal)))
        except (TypeError, ValueError) as error:
            raise ValueError("reviewed proposal must be JSON-serializable") from error
        derived = compact_response_from_reviewed_proposal(proposal)
        if derived.hints != response.hints:
            raise ValueError("reviewed proposal semantics do not match compact response")
        object.__setattr__(self, "compact_response", response)
        object.__setattr__(self, "reviewed_proposal", MappingProxyType(proposal))

    @property
    def compact_inventory_sha256(self) -> str:
        return sha256(self.compact_response.canonical_bytes).hexdigest()


class ReviewedRefinementBridge:
    """Replay independently accepted geometry only for an exact reviewed key."""

    def __init__(self, registrations: tuple[ReviewedRefinementRegistration, ...]) -> None:
        records: dict[tuple[str, str], ReviewedRefinementRegistration] = {}
        for registration in registrations:
            if type(registration) is not ReviewedRefinementRegistration:
                raise ValueError("reviewed bridge registration has the wrong type")
            key = (
                registration.registered_pixel_sha256,
                registration.compact_inventory_sha256,
            )
            if key in records:
                raise ValueError("duplicate reviewed refinement registration")
            records[key] = registration
        self.__registrations = MappingProxyType(records)

    def refine(
        self,
        registered_rgba: np.ndarray,
        response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        rgba = _validated_rgba(registered_rgba)
        actual_response = _validated_response(response)
        pixel_sha = sha256(rgba.tobytes()).hexdigest()
        inventory_sha = sha256(actual_response.canonical_bytes).hexdigest()
        registration = self.__registrations.get((pixel_sha, inventory_sha))
        if registration is None:
            raise ValueError("registered pixels or reviewed compact response are not registered")
        expected = registration.compact_response
        if actual_response.response_sha256 != expected.response_sha256:
            raise ValueError("reviewed compact response byte identity does not match")
        if len(actual_response.hints) != len(expected.hints):
            raise ValueError("reviewed compact response inventory length does not match")
        for index, (actual, wanted) in enumerate(zip(actual_response.hints, expected.hints)):
            if (
                actual.hint_key,
                actual.piece_index,
                actual.grip_type,
                actual.visual_mode,
                actual.anchor,
            ) != (
                wanted.hint_key,
                wanted.piece_index,
                wanted.grip_type,
                wanted.visual_mode,
                wanted.anchor,
            ):
                raise ValueError(f"reviewed compact response hint {index} does not match")

        labels, regions = rasterize_semantic_proposal(rgba, registration.reviewed_proposal)
        if sha256(labels.tobytes()).hexdigest() != registration.accepted_label_sha256:
            raise ValueError("reviewed refinement label identity regressed")
        regions_document = {
            "canvas": {"height": int(labels.shape[0]), "width": int(labels.shape[1])},
            "labelEncoding": "uint16-region-id",
            "regions": regions,
            "stage": 2,
        }
        regions_bytes = (json.dumps(regions_document, indent=2, sort_keys=True) + "\n").encode()
        if sha256(regions_bytes).hexdigest() != registration.accepted_regions_file_sha256:
            raise ValueError("reviewed refinement regions identity regressed")
        return SemanticRefinement(labels, tuple(regions))


@dataclass(frozen=True, slots=True)
class RegionEscalationRequest:
    """A high-resolution region crop plus downscaled full-board context."""

    semantic_request: SemanticVisionRequest
    target_hint: CompactHoldHint
    crop_bounds: tuple[int, int, int, int]
    crop_rgba: np.ndarray
    board_context_rgba: np.ndarray

    def __post_init__(self) -> None:
        if self.semantic_request.request_kind != "region-escalation":
            raise ValueError("targeted requests must use the region-escalation kind")
        for name in ("crop_rgba", "board_context_rgba"):
            rgba = _validated_rgba(getattr(self, name))
            frozen = np.frombuffer(rgba.tobytes(), dtype=np.uint8).reshape(rgba.shape)
            object.__setattr__(self, name, frozen)


class RegionEscalationClient(Protocol):
    def invoke(self, request: RegionEscalationRequest) -> ProviderInvocation: ...


@dataclass(slots=True)
class _BoundEscalationProvider:
    client: RegionEscalationClient
    escalation_request: RegionEscalationRequest

    def invoke(self, request: SemanticVisionRequest) -> ProviderInvocation:
        if request != self.escalation_request.semantic_request:
            raise ValueError("cached escalation request identity changed")
        return self.client.invoke(self.escalation_request)


@dataclass(frozen=True, slots=True)
class TargetedEscalationCoordinator:
    """Escalate one typed ambiguous region, then rerun local refinement once."""

    local_refiner: CompactGeometryRefiner
    stronger_client: RegionEscalationClient
    cache: SemanticCache
    provider_id: str
    model_id: str
    context_max_side: int = 320

    def __post_init__(self) -> None:
        if type(self.context_max_side) is not int or self.context_max_side < 8:
            raise ValueError("escalation context size must be at least eight pixels")

    def refine(
        self,
        registered_rgba: np.ndarray,
        response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        rgba = _validated_rgba(registered_rgba)
        original = _validated_response(response)
        try:
            return self.local_refiner.refine(rgba, original)
        except RegionAmbiguity as ambiguity:
            escalation = self._request(rgba, original, ambiguity)
            ambiguous_hint_key = ambiguity.hint_key

        cached = invoke_with_semantic_cache(
            self.cache,
            escalation.semantic_request,
            _BoundEscalationProvider(self.stronger_client, escalation),
        )
        correction = cached.response
        if len(correction.hints) != 1 or correction.hints[0].hint_key != ambiguous_hint_key:
            raise ValueError("region escalation must return exactly its targeted compact hint")
        merged = _replace_hint(original, correction.hints[0])
        # Intentionally not caught: another ambiguity, or any geometry/topology
        # failure on this one permitted rerun, fails closed without re-escalating.
        return self.local_refiner.refine(rgba, merged)

    def _request(
        self,
        rgba: np.ndarray,
        response: SemanticVisionResponse,
        ambiguity: RegionAmbiguity,
    ) -> RegionEscalationRequest:
        hints = {hint.hint_key: hint for hint in response.hints}
        target = hints.get(ambiguity.hint_key)
        if target is None:
            raise ValueError("ambiguous region does not exist in compact inventory")
        x0, y0, x1, y1 = ambiguity.crop_bounds
        height, width = rgba.shape[:2]
        if x1 > width or y1 > height:
            raise ValueError("ambiguous region crop extends outside registered pixels")
        crop = rgba[y0:y1, x0:x1]
        scale = min(1.0, self.context_max_side / max(height, width))
        context_width = max(1, int(round(width * scale)))
        context_height = max(1, int(round(height * scale)))
        context = cv2.resize(
            rgba,
            (context_width, context_height),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_NEAREST,
        )
        prompt = canonical_json_bytes({
            "ambiguity": ambiguity.reason,
            "contextPixelSha256": sha256(context.tobytes()).hexdigest(),
            "cropBounds": list(ambiguity.crop_bounds),
            "cropPixelSha256": sha256(crop.tobytes()).hexdigest(),
            "instruction": "correct only the compact fields for this one observed grip",
            "targetHint": target.as_wire_document(),
        })
        semantic_request = SemanticVisionRequest(
            registered_pixel_sha256=sha256(rgba.tobytes()).hexdigest(),
            prompt_bytes=prompt,
            provider_id=self.provider_id,
            model_id=self.model_id,
            request_kind="region-escalation",
        )
        return RegionEscalationRequest(
            semantic_request=semantic_request,
            target_hint=target,
            crop_bounds=ambiguity.crop_bounds,
            crop_rgba=crop,
            board_context_rgba=context,
        )


def _replace_hint(
    response: SemanticVisionResponse,
    correction: CompactHoldHint,
) -> SemanticVisionResponse:
    hints = [correction if hint.hint_key == correction.hint_key else hint for hint in response.hints]
    return parse_compact_semantic_response(
        canonical_json_bytes({"h": [hint.as_wire_document() for hint in hints]})
    )
