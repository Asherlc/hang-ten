from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType, SimpleNamespace

import numpy as np
from PIL import Image

import hangboard_vectorizer.generic_stage2 as generic_stage2
from hangboard_vectorizer.generic_stage2 import (
    CachedSemanticProposalProvider,
    FileSemanticProposalProvider,
    SemanticProposalCapture,
    run_generic_stage2,
)
from hangboard_vectorizer.semantic_cache import CacheTelemetry, SemanticCache, SemanticCacheKey
from hangboard_vectorizer.semantic_refinement import (
    ReviewedRefinementBridge,
    ReviewedRefinementRegistration,
    compact_response_from_reviewed_proposal,
)
from hangboard_vectorizer.semantic_vision import ModelInvocation, ProviderInvocation


def test_stage2_captures_once_and_refines_the_same_proposal_twice(
    tmp_path: Path, monkeypatch,
) -> None:
    context, proposal = _context_and_proposal(tmp_path)

    class CountingProvider:
        calls = 0

        def capture(self, _request):
            self.calls += 1
            return SemanticProposalCapture(
                proposal=proposal,
                raw_bytes=_canonical_bytes(proposal),
                content_type="application/json",
                identity={"provider": "counting"},
            )

    provider = CountingProvider()
    original = generic_stage2.rasterize_semantic_proposal
    local_results: list[tuple[bytes, list[dict[str, object]]]] = []

    def observe_local_work(*args, **kwargs):
        result = original(*args, **kwargs)
        local_results.append((result[0].tobytes(), result[1]))
        return result

    monkeypatch.setattr(generic_stage2, "rasterize_semantic_proposal", observe_local_work)
    run_generic_stage2(context, tmp_path / "stage-2", provider=provider)

    assert provider.calls == 1
    assert len(local_results) == 2
    assert local_results[0] == local_results[1]


def test_file_provider_keeps_the_existing_candidate_artifacts_and_proposal_binding(
    tmp_path: Path,
) -> None:
    context, proposal = _context_and_proposal(tmp_path)
    proposal_path = context.root / "inputs/stage-2-semantic-proposal.json"
    proposal_path.write_bytes(_canonical_bytes(proposal))

    root = tmp_path / "stage-2"
    run_generic_stage2(context, root, provider=FileSemanticProposalProvider())

    capture = json.loads((root / "stage-2-semantic-capture.json").read_text())
    candidate = json.loads((root / "stage-2-candidate.json").read_text())
    hashes = json.loads((root / "candidate-hashes.json").read_text())
    proposal_hash = sha256(proposal_path.read_bytes()).hexdigest()

    assert set(hashes) == {
        "stage-2-candidate.json",
        "stage-2-labels.png",
        "stage-2-regions.json",
        "stage-2-review.png",
        "stage-2-semantic-capture.json",
    }
    assert capture["proposal"] == {
        "path": "inputs/stage-2-semantic-proposal.json",
        "provider": "file",
        "sha256": proposal_hash,
    }
    assert candidate["proposalSha256"] == proposal_hash
    assert not (root / "stage-2-semantic-response.json").exists()
    assert not (root / "stage-2-semantic-evidence.json").exists()


def test_capture_telemetry_is_excluded_from_deterministic_candidate_identity(tmp_path: Path) -> None:
    context, proposal = _context_and_proposal(tmp_path)
    raw_bytes = b'{"h":[]}'

    def provider(*, hit: bool, wall_milliseconds: int):
        class CompactProvider:
            def capture(self, _request):
                return SemanticProposalCapture(
                    proposal=proposal,
                    raw_bytes=raw_bytes,
                    content_type="application/json",
                    identity={"modelId": "fake-model-v1", "provider": "fake-vision"},
                    invocation=ModelInvocation(
                        input_tokens=3,
                        output_tokens=2,
                        total_tokens=5,
                        attempts=1,
                        retries=0,
                        wall_milliseconds=wall_milliseconds,
                    ),
                    cache=CacheTelemetry(hit=hit, model_calls=0 if hit else 1),
                )

        return CompactProvider()

    first, second = tmp_path / "first", tmp_path / "second"
    run_generic_stage2(context, first, provider=provider(hit=False, wall_milliseconds=17))
    run_generic_stage2(context, second, provider=provider(hit=True, wall_milliseconds=0))

    assert _candidate_bytes(first) == _candidate_bytes(second)
    assert (first / "stage-2-semantic-response.json").read_bytes() == raw_bytes
    assert (second / "stage-2-semantic-response.json").read_bytes() == raw_bytes
    first_evidence = json.loads((first / "stage-2-semantic-evidence.json").read_text())
    second_evidence = json.loads((second / "stage-2-semantic-evidence.json").read_text())
    assert first_evidence["response"]["sha256"] == sha256(raw_bytes).hexdigest()
    assert second_evidence["response"]["sha256"] == sha256(raw_bytes).hexdigest()
    assert first_evidence["cache"] != second_evidence["cache"]
    assert first_evidence["invocation"] != second_evidence["invocation"]


def test_cached_compact_provider_replays_through_reviewed_bridge_with_zero_client_calls(
    tmp_path: Path,
) -> None:
    context, proposal = _context_and_proposal(tmp_path)
    rgba = np.asarray(Image.open(context.root / "inputs/stage-1-rgba.png"), dtype=np.uint8)
    response = compact_response_from_reviewed_proposal(proposal)
    labels, regions = generic_stage2.rasterize_semantic_proposal(rgba, proposal)
    regions_bytes = (json.dumps({
        "canvas": {"height": 48, "width": 64},
        "labelEncoding": "uint16-region-id",
        "regions": regions,
        "stage": 2,
    }, indent=2, sort_keys=True) + "\n").encode()
    bridge = ReviewedRefinementBridge((ReviewedRefinementRegistration(
        registered_pixel_sha256=sha256(rgba.tobytes()).hexdigest(),
        compact_response=response,
        reviewed_proposal=proposal,
        accepted_label_sha256=sha256(labels.tobytes()).hexdigest(),
        accepted_regions_file_sha256=sha256(regions_bytes).hexdigest(),
    ),))
    cache = SemanticCache(tmp_path / "semantic-cache")
    prompt = b"return one batched five-field compact inventory"
    provider_id = "accepted-review"
    model_id = "accepted-compact-v1"
    semantic_request = generic_stage2.SemanticVisionRequest(
        registered_pixel_sha256=sha256(rgba.tobytes()).hexdigest(),
        prompt_bytes=prompt,
        provider_id=provider_id,
        model_id=model_id,
        request_kind="full-board",
    )
    cache.store(
        SemanticCacheKey.from_request(semantic_request),
        response,
        ModelInvocation(None, None, None, 1, 0, 0, {"source": "accepted-review"}),
    )

    class ForbiddenClient:
        calls = 0

        def invoke(self, _request) -> ProviderInvocation:
            self.calls += 1
            raise AssertionError("cache replay invoked the semantic client")

    client = ForbiddenClient()
    provider = CachedSemanticProposalProvider(
        cache=cache,
        client=client,
        proposal=proposal,
        refiner=bridge,
        prompt_bytes=prompt,
        provider_id=provider_id,
        model_id=model_id,
        cache_only=True,
    )
    output = tmp_path / "compact-stage-2"

    run_generic_stage2(context, output, provider=provider)

    replayed = np.asarray(Image.open(output / "stage-2-labels.png"), dtype=np.uint16)
    assert client.calls == 0
    assert replayed.tobytes() == labels.tobytes()
    assert json.loads((output / "stage-2-regions.json").read_text())["regions"] == regions
    assert (output / "stage-2-semantic-response.json").read_bytes() == response.raw_bytes
    evidence = json.loads((output / "stage-2-semantic-evidence.json").read_text())
    assert evidence["cache"] == {"hit": True, "modelCalls": 0}
    assert evidence["invocation"] is None


def _context_and_proposal(tmp_path: Path) -> tuple[SimpleNamespace, dict[str, object]]:
    root = tmp_path / "run"
    root.mkdir()
    inputs = root / "inputs"
    inputs.mkdir()
    rgba = np.full((48, 64, 4), 255, dtype=np.uint8)
    raster_path = inputs / "stage-1-rgba.png"
    Image.fromarray(rgba, "RGBA").save(raster_path, format="PNG", optimize=False, compress_level=9)
    raster_hash = sha256(raster_path.read_bytes()).hexdigest()
    acceptance = {
        "registered": {
            "fileSha256": raster_hash,
            "path": "inputs/stage-1-rgba.png",
            "pixelSha256": sha256(rgba.tobytes()).hexdigest(),
        },
        "runIdentitySha256": "run-identity",
        "stage": 1,
    }
    acceptance_path = inputs / "stage-1-acceptance.json"
    acceptance_path.write_text(json.dumps(acceptance, sort_keys=True) + "\n")
    acceptance_hash = sha256(acceptance_path.read_bytes()).hexdigest()
    proposal = {
        "canvas": {"height": 48, "width": 64},
        "inputAcceptanceSha256": acceptance_hash,
        "inputRasterSha256": raster_hash,
        "productKey": "example-board",
        "provider": "file",
        "regions": [
            {
                "anchor": [24, 24],
                "geometry": {
                    "mode": "surface",
                    "polygon": [[12, 12], [36, 12], [36, 36], [12, 36]],
                },
                "id": 1,
                "key": "grip-001",
                "metadata": {},
                "type": "edge",
            }
        ],
        "schemaVersion": 1,
    }
    context = SimpleNamespace(
        root=root,
        manifest=MappingProxyType(
            {
                "product": {"key": "example-board"},
                "runIdentitySha256": "run-identity",
                "stages": [
                    {"stage": 0},
                    {
                        "acceptancePath": "inputs/stage-1-acceptance.json",
                        "acceptanceSha256": acceptance_hash,
                        "stage": 1,
                        "status": "approved",
                    },
                ],
            }
        ),
    )
    return context, proposal


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _candidate_bytes(root: Path) -> dict[str, bytes]:
    hashes = json.loads((root / "candidate-hashes.json").read_text())
    return {name: (root / name).read_bytes() for name in hashes}
