from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from hangboard_vectorizer.models import ConversionError
from hangboard_vectorizer.semantic_cache import SemanticCache
from hangboard_vectorizer.semantic_refinement import (
    RegionAmbiguity,
    ReviewedRefinementBridge,
    ReviewedRefinementRegistration,
    SemanticRefinement,
    TargetedEscalationCoordinator,
    compact_response_from_reviewed_proposal,
)
from hangboard_vectorizer.semantic_vision import (
    ModelInvocation,
    ProviderInvocation,
    SemanticVisionRequest,
    SemanticVisionResponse,
    canonical_json_bytes,
    parse_compact_semantic_response,
)


ACCEPTED_PIXEL_SHA256 = "15aa858cd35d8e6d0496ba46ef6dc3f99866ddaa831755f91294e504ca763e2a"
ACCEPTED_LABEL_SHA256 = "9ec737eb0340f03cf7680b272ecfa89fde3551df558e6ebdd515104240123d12"
ACCEPTED_REGIONS_FILE_SHA256 = "ed34ff7a360f22e84e60c767b44f3451100ea2547a4fdf80900fffc80168ed49"


def test_reviewed_metolius_compact_hints_reproduce_accepted_stage2_exactly() -> None:
    accepted = _accepted_run()
    proposal = json.loads((accepted / "inputs/stage-2-semantic-proposal.json").read_text())
    response = compact_response_from_reviewed_proposal(proposal)

    assert [
        (hint.hint_key, hint.grip_type, hint.visual_mode, hint.anchor)
        for hint in response.hints
    ] == [
        ("grip-001", "jug", "surface", (1, 0)),
        ("grip-002", "sloper", "surface", (4, 0)),
        ("grip-003", "sloper", "surface", (10, 0)),
        ("grip-004", "sloper", "surface", (15, 0)),
        ("grip-005", "jug", "surface", (18, 0)),
        ("grip-006", "edge", "surface", (1, 2)),
        ("grip-007", "pocket", "aperture", (5, 3)),
        ("grip-008", "pocket", "aperture", (7, 3)),
        ("grip-009", "pocket", "aperture", (10, 3)),
        ("grip-010", "pocket", "aperture", (12, 3)),
        ("grip-011", "pocket", "aperture", (14, 3)),
        ("grip-012", "edge", "surface", (18, 2)),
        ("grip-013", "edge", "surface", (2, 5)),
        ("grip-014", "pocket", "aperture", (5, 6)),
        ("grip-015", "pocket", "aperture", (7, 6)),
        ("grip-016", "pocket", "aperture", (10, 6)),
        ("grip-017", "pocket", "aperture", (12, 6)),
        ("grip-018", "pocket", "aperture", (14, 6)),
        ("grip-019", "edge", "surface", (17, 5)),
    ]
    assert [sum(hint.grip_type == kind for hint in response.hints) for kind in (
        "jug", "sloper", "edge", "pocket",
    )] == [2, 3, 4, 10]

    stage1_path = accepted / "stages/01/attempt-0001/stage-1-auto-rgba.png"
    rgba = np.asarray(Image.open(stage1_path).convert("RGBA"), dtype=np.uint8)
    registration = ReviewedRefinementRegistration(
        registered_pixel_sha256=ACCEPTED_PIXEL_SHA256,
        compact_response=response,
        reviewed_proposal=proposal,
        accepted_label_sha256=ACCEPTED_LABEL_SHA256,
        accepted_regions_file_sha256=ACCEPTED_REGIONS_FILE_SHA256,
    )
    result = ReviewedRefinementBridge((registration,)).refine(rgba, response)

    accepted_labels = np.asarray(
        Image.open(accepted / "stages/02/attempt-0001/stage-2-labels.png"),
        dtype=np.uint16,
    )
    accepted_regions = json.loads(
        (accepted / "stages/02/attempt-0001/stage-2-regions.json").read_text()
    )["regions"]
    assert result.labels.tobytes() == accepted_labels.tobytes()
    assert sha256(result.labels.tobytes()).hexdigest() == ACCEPTED_LABEL_SHA256
    assert list(result.regions) == accepted_regions


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("k", "grip-099"),
        ("t", "pocket"),
        ("m", "aperture"),
        ("a", [2, 0]),
    ),
)
def test_reviewed_bridge_rejects_each_changed_compact_hint_field(
    field: str, value: object,
) -> None:
    rgba, proposal, response, registration = _tiny_reviewed_registration()
    wire = json.loads(response.raw_bytes)
    wire["h"][0][field] = value
    changed = parse_compact_semantic_response(canonical_json_bytes(wire))

    with pytest.raises(ValueError, match="reviewed compact response"):
        ReviewedRefinementBridge((registration,)).refine(rgba, changed)


def test_successful_local_refinement_makes_zero_escalation_calls(tmp_path: Path) -> None:
    rgba = np.full((32, 48, 4), 255, dtype=np.uint8)
    response = _response(anchor=(3, 2))
    wanted = SemanticRefinement(np.ones((32, 48), dtype=np.uint16), ({"id": 1},))
    local = _FixedRefiner(wanted)
    client = _EscalationClient(_response(anchor=(4, 2)))

    result = TargetedEscalationCoordinator(
        local_refiner=local,
        stronger_client=client,
        cache=SemanticCache(tmp_path / "cache"),
        provider_id="fixture-provider",
        model_id="fixture-strong-v1",
    ).refine(rgba, response)

    assert result == wanted
    assert client.requests == []


def test_one_region_ambiguity_makes_one_crop_call_and_reruns_once(tmp_path: Path) -> None:
    rgba = np.zeros((40, 60, 4), dtype=np.uint8)
    rgba[..., :3] = np.arange(60, dtype=np.uint8)[None, :, None]
    rgba[..., 3] = 255
    response = _response(anchor=(3, 2))
    local = _AmbiguousThenCorrectedRefiner()
    client = _EscalationClient(_response(anchor=(4, 2)))
    coordinator = TargetedEscalationCoordinator(
        local_refiner=local,
        stronger_client=client,
        cache=SemanticCache(tmp_path / "cache"),
        provider_id="fixture-provider",
        model_id="fixture-strong-v1",
        context_max_side=24,
    )

    result = coordinator.refine(rgba, response)

    assert result.regions == ({"correctedAnchor": [4, 2]},)
    assert local.calls == 2
    assert len(client.requests) == 1
    request = client.requests[0]
    assert request.semantic_request.request_kind == "region-escalation"
    assert request.target_hint.hint_key == "grip-001"
    assert request.crop_bounds == (10, 8, 30, 28)
    assert request.crop_rgba.tobytes() == rgba[8:28, 10:30].tobytes()
    assert max(request.board_context_rgba.shape[:2]) == 24


def test_global_validation_failure_never_escalates(tmp_path: Path) -> None:
    rgba = np.full((32, 48, 4), 255, dtype=np.uint8)
    client = _EscalationClient(_response(anchor=(4, 2)))
    coordinator = TargetedEscalationCoordinator(
        local_refiner=_InvalidGlobalRefiner(),
        stronger_client=client,
        cache=SemanticCache(tmp_path / "cache"),
        provider_id="fixture-provider",
        model_id="fixture-strong-v1",
    )

    with pytest.raises(ConversionError, match="overlap topology failed"):
        coordinator.refine(rgba, _response(anchor=(3, 2)))
    assert client.requests == []


def test_malformed_escalation_fails_closed_without_second_local_run(tmp_path: Path) -> None:
    rgba = np.full((32, 48, 4), 255, dtype=np.uint8)
    local = _AlwaysAmbiguousRefiner()
    client = _MalformedEscalationClient()
    coordinator = TargetedEscalationCoordinator(
        local_refiner=local,
        stronger_client=client,
        cache=SemanticCache(tmp_path / "cache"),
        provider_id="fixture-provider",
        model_id="fixture-strong-v1",
    )

    with pytest.raises(ValueError, match="unknown or missing fields"):
        coordinator.refine(rgba, _response(anchor=(3, 2)))
    assert local.calls == 1
    assert len(client.requests) == 1


def _accepted_run() -> Path:
    checkout = Path(__file__).resolve().parents[1]
    repository = checkout.parent.parent if checkout.parent.name == ".worktrees" else checkout
    path = repository / "work/real-metolius-compact-ii/onboarding-visual-test-v3"
    if not path.exists():
        pytest.skip("accepted Metolius visual baseline is not available")
    return path


def _tiny_reviewed_registration() -> tuple[
    np.ndarray, dict[str, object], SemanticVisionResponse, ReviewedRefinementRegistration,
]:
    rgba = np.full((24, 40, 4), 255, dtype=np.uint8)
    proposal: dict[str, object] = {
        "canvas": {"height": 24, "width": 40},
        "regions": [{
            "anchor": [8, 8],
            "geometry": {"mode": "surface", "polygon": [[2, 2], [16, 2], [16, 16], [2, 16]]},
            "id": 1,
            "key": "reviewed-left",
            "metadata": {},
            "type": "jug",
        }],
    }
    response = compact_response_from_reviewed_proposal(proposal)
    from hangboard_vectorizer.generic_stage2 import rasterize_semantic_proposal
    labels, regions = rasterize_semantic_proposal(rgba, proposal)
    regions_document = {
        "canvas": {"height": 24, "width": 40},
        "labelEncoding": "uint16-region-id",
        "regions": regions,
        "stage": 2,
    }
    regions_bytes = (json.dumps(regions_document, indent=2, sort_keys=True) + "\n").encode()
    registration = ReviewedRefinementRegistration(
        registered_pixel_sha256=sha256(rgba.tobytes()).hexdigest(),
        compact_response=response,
        reviewed_proposal=proposal,
        accepted_label_sha256=sha256(labels.tobytes()).hexdigest(),
        accepted_regions_file_sha256=sha256(regions_bytes).hexdigest(),
    )
    return rgba, proposal, response, registration


def _response(*, anchor: tuple[int, int]) -> SemanticVisionResponse:
    return parse_compact_semantic_response(canonical_json_bytes({"h": [{
        "a": list(anchor), "k": "grip-001", "m": "surface", "p": 0, "t": "jug",
    }]}))


@dataclass
class _FixedRefiner:
    result: SemanticRefinement

    def refine(
        self, registered_rgba: np.ndarray, response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        return self.result


@dataclass
class _AmbiguousThenCorrectedRefiner:
    calls: int = 0

    def refine(
        self, registered_rgba: np.ndarray, response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        self.calls += 1
        if self.calls == 1:
            raise RegionAmbiguity("grip-001", "two observed mouths", (10, 8, 30, 28))
        return SemanticRefinement(
            np.ones(registered_rgba.shape[:2], dtype=np.uint16),
            ({"correctedAnchor": list(response.hints[0].anchor)},),
        )


@dataclass
class _InvalidGlobalRefiner:
    def refine(
        self, registered_rgba: np.ndarray, response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        raise ConversionError("overlap topology failed")


@dataclass
class _AlwaysAmbiguousRefiner:
    calls: int = 0

    def refine(
        self, registered_rgba: np.ndarray, response: SemanticVisionResponse,
    ) -> SemanticRefinement:
        self.calls += 1
        raise RegionAmbiguity("grip-001", "uncertain seam", (4, 4, 20, 20))


@dataclass
class _EscalationClient:
    response: SemanticVisionResponse
    requests: list[object] | None = None

    def __post_init__(self) -> None:
        self.requests = []

    def invoke(self, request: object) -> ProviderInvocation:
        assert self.requests is not None
        self.requests.append(request)
        return ProviderInvocation(
            response=self.response,
            invocation=ModelInvocation(13, 5, 18, 1, 0, 7),
        )


@dataclass
class _MalformedEscalationClient:
    requests: list[object] | None = None

    def __post_init__(self) -> None:
        self.requests = []

    def invoke(self, request: object) -> ProviderInvocation:
        assert self.requests is not None
        self.requests.append(request)
        raw = canonical_json_bytes({"h": [{
            "a": [4, 2], "box": [1, 2, 3, 4], "k": "grip-001",
            "m": "surface", "p": 0, "t": "jug",
        }]})
        forged = SemanticVisionResponse(
            hints=_response(anchor=(4, 2)).hints,
            raw_bytes=raw,
            response_sha256=sha256(raw).hexdigest(),
        )
        return ProviderInvocation(
            response=forged,
            invocation=ModelInvocation(13, 5, 18, 1, 0, 7),
        )
