"""Offline cache replay and parity report for the accepted Metolius run."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from hashlib import sha256
import json
from pathlib import Path
from types import SimpleNamespace
from time import perf_counter
import tempfile

import numpy as np
from PIL import Image

from . import generic_stage3, generic_stage4
from .generic_stage2 import CachedSemanticProposalProvider, run_generic_stage2
from .semantic_cache import SemanticCache, SemanticCacheKey
from .semantic_metrics import (
    LocalProcessingMetrics,
    ModelProcessingMetrics,
    SemanticRunMetrics,
    UnmeasuredBaselineTokensError,
    benchmark_semantic_runs,
)
from .semantic_refinement import (
    ReviewedRefinementBridge,
    ReviewedRefinementRegistration,
    compact_response_from_reviewed_proposal,
)
from .semantic_vision import (
    ModelInvocation,
    ProviderInvocation,
    SemanticVisionRequest,
    canonical_json_bytes,
)
from .workspace_paths import default_workspace_root, resolve_workspace_path


ACCEPTED_RUN_ID = "30c65a90865de3c7de6e8e27a061056c4ef59e2d7a700e1406e3ae272e83e0b6"
ACCEPTED_PIXEL_SHA256 = "15aa858cd35d8e6d0496ba46ef6dc3f99866ddaa831755f91294e504ca763e2a"
ACCEPTED_LABEL_SHA256 = "9ec737eb0340f03cf7680b272ecfa89fde3551df558e6ebdd515104240123d12"
ACCEPTED_REGIONS_FILE_SHA256 = "ed34ff7a360f22e84e60c767b44f3451100ea2547a4fdf80900fffc80168ed49"
ACCEPTED_STAGE3_FILE_SHA256 = "8e4bb7db411494e6a1459c03fe7c6fa1d3c614a00132b2f53547265b882debb6"

PROVIDER_ID = "accepted-review"
MODEL_ID = "metolius-accepted-unmeasured-v1"
REQUEST_KIND = "full-board"
COMPACT_PROMPT_BYTES = canonical_json_bytes({
    "anchorGrid": [20, 8],
    "fields": ["hintKey", "pieceIndex", "gripType", "visualMode", "anchorCell"],
    "instruction": "return one batched observation for every physical grip",
    "omit": ["explanations", "contours", "boxes", "dimensions", "pixelGeometry"],
})


class _ForbiddenLiveClient:
    """A cache-only sentinel: any transport attempt is a benchmark failure."""

    def __init__(self) -> None:
        self.calls = 0

    def invoke(self, _request: SemanticVisionRequest) -> ProviderInvocation:
        self.calls += 1
        raise RuntimeError("cache-only benchmark attempted a live semantic call")


def build_metolius_benchmark_report(
    accepted_run: Path,
    output_path: Path,
    *,
    workspace_root: Path,
    cache_root: Path | None = None,
) -> dict[str, object]:
    """Seed accepted compact evidence, replay offline, and write a sorted report."""
    accepted = Path(accepted_run).resolve()
    owned_root = Path(workspace_root).resolve(strict=False)
    output = resolve_workspace_path(Path(output_path), owned_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    cache = SemanticCache(
        resolve_workspace_path(Path(cache_root), owned_root)
        if cache_root is not None
        else output.parent / "semantic-cache"
    )

    run_document = _json(accepted / "run.json")
    if run_document.get("runIdentitySha256") != ACCEPTED_RUN_ID:
        raise ValueError("benchmark input is not the accepted Metolius run")
    proposal_path = accepted / "inputs/stage-2-semantic-proposal.json"
    proposal_bytes = proposal_path.read_bytes()
    proposal = _json(proposal_path)
    rgba_path = accepted / "stages/01/attempt-0001/stage-1-auto-rgba.png"
    with Image.open(rgba_path) as image:
        rgba = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    if _hash_bytes(rgba.tobytes()) != ACCEPTED_PIXEL_SHA256:
        raise ValueError("accepted Metolius registered pixels changed")

    accepted_stage2_root = accepted / "stages/02/attempt-0001"
    accepted_labels_path = accepted_stage2_root / "stage-2-labels.png"
    accepted_regions_path = accepted_stage2_root / "stage-2-regions.json"
    with Image.open(accepted_labels_path) as image:
        accepted_labels = np.asarray(image, dtype=np.uint16)
    if _hash_bytes(accepted_labels.tobytes()) != ACCEPTED_LABEL_SHA256:
        raise ValueError("accepted Metolius label pixels changed")
    if _hash_file(accepted_regions_path) != ACCEPTED_REGIONS_FILE_SHA256:
        raise ValueError("accepted Metolius regions changed")

    response = compact_response_from_reviewed_proposal(proposal)
    registration = ReviewedRefinementRegistration(
        registered_pixel_sha256=ACCEPTED_PIXEL_SHA256,
        compact_response=response,
        reviewed_proposal=proposal,
        accepted_label_sha256=ACCEPTED_LABEL_SHA256,
        accepted_regions_file_sha256=ACCEPTED_REGIONS_FILE_SHA256,
    )
    bridge = ReviewedRefinementBridge((registration,))
    semantic_request = SemanticVisionRequest(
        registered_pixel_sha256=ACCEPTED_PIXEL_SHA256,
        prompt_bytes=COMPACT_PROMPT_BYTES,
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        request_kind=REQUEST_KIND,
    )
    key = SemanticCacheKey.from_request(semantic_request)
    cache_preexisted = cache.envelope_path(key).exists()
    cache.store(
        key,
        response,
        ModelInvocation(
            input_tokens=None,
            output_tokens=None,
            total_tokens=None,
            attempts=1,
            retries=0,
            wall_milliseconds=0,
            details={"measurement": "unmeasured", "source": "accepted-reviewed-proposal"},
        ),
    )

    client = _ForbiddenLiveClient()
    provider = CachedSemanticProposalProvider(
        cache=cache,
        client=client,
        proposal=proposal,
        refiner=bridge,
        prompt_bytes=COMPACT_PROMPT_BYTES,
        provider_id=PROVIDER_ID,
        model_id=MODEL_ID,
        request_kind=REQUEST_KIND,
        cache_only=True,
    )
    started = perf_counter()
    with tempfile.TemporaryDirectory(
        prefix="hangboard-semantic-replay-", dir=output.parent
    ) as temporary:
        replay_root = Path(temporary) / "stage-2"
        context = SimpleNamespace(root=accepted, manifest=run_document)
        run_generic_stage2(context, replay_root, provider=provider)
        report = _report(
            accepted,
            replay_root,
            rgba,
            accepted_labels,
            proposal_bytes,
            response.raw_bytes,
            semantic_request,
            client.calls,
            cache_preexisted,
            cache.envelope_path(key),
            0,
        )
        report["localProcessing"]["wallMilliseconds"] = int(
            round((perf_counter() - started) * 1000)
        )
    output.write_bytes((json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    return report


def _report(
    accepted: Path,
    replay_root: Path,
    rgba: np.ndarray,
    accepted_labels: np.ndarray,
    proposal_bytes: bytes,
    compact_bytes: bytes,
    request: SemanticVisionRequest,
    client_calls: int,
    cache_preexisted: bool,
    cache_path: Path,
    local_milliseconds: int,
) -> dict[str, object]:
    with Image.open(replay_root / "stage-2-labels.png") as image:
        replay_labels = np.asarray(image, dtype=np.uint16)
    accepted_regions_path = accepted / "stages/02/attempt-0001/stage-2-regions.json"
    replay_regions_path = replay_root / "stage-2-regions.json"
    accepted_regions = _json(accepted_regions_path)["regions"]
    replay_regions = _json(replay_regions_path)["regions"]
    response_exact = (replay_root / "stage-2-semantic-response.json").read_bytes() == compact_bytes

    stage3_path = accepted / "stages/03/attempt-0001/stage-3-vector-regions.json"
    if _hash_file(stage3_path) != ACCEPTED_STAGE3_FILE_SHA256:
        raise ValueError("accepted Metolius Stage 3 vector evidence changed")
    accepted_stage3 = _json(stage3_path)
    replay_stage3 = generic_stage3._vector_document(
        rgba,
        replay_labels,
        replay_regions,
        {"stage2Acceptance": accepted_stage3["inputAcceptance"]},
        generic_stage3.GenericStage3Profile(),
    )
    accepted_geometry_hash = _geometry_hash(accepted_stage3)
    replay_geometry_hash = _geometry_hash(replay_stage3)

    silhouettes, regions = generic_stage4._geometry(
        replay_stage3, replay_labels.shape[1], replay_labels.shape[0]
    )
    normal, coverages = generic_stage4._render(
        rgba,
        silhouettes,
        regions,
        ACCEPTED_PIXEL_SHA256,
        generic_stage4.GenericStage4Profile(),
    )
    scenarios = generic_stage4._scenarios(regions, coverages)
    replay_highlights = {
        name: generic_stage4._highlight(normal, coverages, selected)
        for name, selected in scenarios.items()
    }
    accepted_highlight_hashes: dict[str, str] = {}
    replay_highlight_hashes: dict[str, str] = {}
    highlight_exact: dict[str, bool] = {}
    for name, replayed in sorted(replay_highlights.items()):
        path = accepted / f"stages/04/attempt-0001/stage-4-highlight-{name}.png"
        with Image.open(path) as image:
            accepted_pixels = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        accepted_hash = _hash_bytes(accepted_pixels.tobytes())
        replay_hash = _hash_bytes(replayed.tobytes())
        accepted_highlight_hashes[name] = accepted_hash
        replay_highlight_hashes[name] = replay_hash
        highlight_exact[name] = np.array_equal(accepted_pixels, replayed)

    baseline = SemanticRunMetrics(
        model=(ModelProcessingMetrics(
            provider_id="unknown",
            model_id="unknown",
            request_kind=REQUEST_KIND,
            model_calls=1,
            total_tokens=None,
            wall_milliseconds=0,
        ),),
        local=LocalProcessingMetrics("historical-unmeasured", 0),
    )
    replay = SemanticRunMetrics(
        model=(ModelProcessingMetrics(
            provider_id=PROVIDER_ID,
            model_id=MODEL_ID,
            request_kind=REQUEST_KIND,
            model_calls=0,
            total_tokens=0,
            wall_milliseconds=0,
            cache_hit=True,
        ),),
        local=LocalProcessingMetrics("stage2-stage4-cache-replay", local_milliseconds),
    )
    summary = benchmark_semantic_runs((baseline,), (replay,))
    percentage_reduction: float | None
    percentage_reason: str | None
    try:
        percentage_reduction = summary.percentage_reduction
        percentage_reason = None
    except UnmeasuredBaselineTokensError:
        percentage_reduction = None
        percentage_reason = (
            "historical baseline model tokens were not measured; serialized byte sizes "
            "are a non-token proxy and cannot establish token reduction"
        )

    stage2 = {
        "acceptedLabelPixelSha256": _hash_bytes(accepted_labels.tobytes()),
        "acceptedRegionsFileSha256": _hash_file(accepted_regions_path),
        "labelInventory": sorted(int(value) for value in np.unique(replay_labels) if value),
        "labelsExact": np.array_equal(accepted_labels, replay_labels),
        "regionsExact": accepted_regions == replay_regions,
        "replayLabelPixelSha256": _hash_bytes(replay_labels.tobytes()),
        "replayRegionsFileSha256": _hash_file(replay_regions_path),
    }
    stage3 = {
        "acceptedGeometrySha256": accepted_geometry_hash,
        "geometryExact": accepted_geometry_hash == replay_geometry_hash,
        "replayGeometrySha256": replay_geometry_hash,
    }
    stage4 = {
        "acceptedHighlightPixelSha256": accepted_highlight_hashes,
        "highlightPixelsExact": highlight_exact,
        "replayHighlightPixelSha256": replay_highlight_hashes,
    }
    exact = (
        client_calls == 0
        and response_exact
        and stage2["labelsExact"]
        and stage2["regionsExact"]
        and stage3["geometryExact"]
        and all(highlight_exact.values())
    )
    return {
        "acceptedRun": str(accepted),
        "cache": {
            "cacheOnly": True,
            "envelopePath": str(cache_path),
            "entryPreexisted": cache_preexisted,
            "identitySha256": SemanticCacheKey.from_request(request).digest,
            "responseBytesExact": response_exact,
        },
        "localProcessing": {
            "operation": "stage2-stage4-cache-replay",
            "wallMilliseconds": local_milliseconds,
        },
        "model": {
            "cacheReplay": {
                "cacheHit": True,
                "calls": client_calls,
                "inputTokens": 0,
                "outputTokens": 0,
                "retries": 0,
                "totalTokens": 0,
                "wallMilliseconds": 0,
            },
            "historicalBaseline": {
                "calls": None,
                "inputTokens": None,
                "modelId": None,
                "outputTokens": None,
                "retries": None,
                "totalTokens": summary.baseline_median_tokens,
                "wallMilliseconds": None,
            },
            "percentageTokenReduction": percentage_reduction,
            "percentageTokenReductionReason": percentage_reason,
        },
        "nonTokenByteProxy": {
            "compactResponseBytes": len(compact_bytes),
            "fullProposalBytes": len(proposal_bytes),
            "label": "Serialized response byte counts only; not token measurements",
        },
        "parity": {"exact": bool(exact), "stage2": stage2, "stage3": stage3, "stage4": stage4},
        "requestIdentity": {
            "modelId": request.model_id,
            "promptSha256": request.prompt_sha256,
            "providerId": request.provider_id,
            "registeredPixelSha256": request.registered_pixel_sha256,
            "requestKind": request.request_kind,
            "schemaVersion": request.schema_version,
        },
        "schemaVersion": 1,
    }


def _geometry_hash(document: dict[str, object]) -> str:
    return _hash_bytes(canonical_json_bytes({
        "regions": document["regions"],
        "silhouettePaths": document["silhouettePaths"],
    }))


def _json(path: Path) -> dict[str, object]:
    document = json.loads(path.read_bytes())
    if not isinstance(document, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return document


def _hash_bytes(value: bytes) -> str:
    return sha256(value).hexdigest()


def _hash_file(path: Path) -> str:
    return _hash_bytes(path.read_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Replay accepted Metolius compact semantics without live model calls",
    )
    parser.add_argument("--accepted-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=default_workspace_root(),
        help=(
            "owned root for generated artifacts "
            "(default: $HANGBOARD_WORKSPACE_ROOT or .context/hangboard-onboarding)"
        ),
    )
    arguments = parser.parse_args(argv)
    report = build_metolius_benchmark_report(
        arguments.accepted_run,
        arguments.output,
        workspace_root=arguments.workspace_root,
        cache_root=arguments.cache_dir,
    )
    if not report["parity"]["exact"]:
        raise SystemExit("semantic replay parity failed")
    print(arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
