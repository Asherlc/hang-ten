"""Read-only staged replay evidence for the accepted Beastmaker onboarding."""

from __future__ import annotations

from base64 import b64decode
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from functools import cache
from hashlib import sha256
from io import BytesIO
from importlib import resources
import json
import os
from pathlib import Path
from secrets import token_urlsafe
import shutil
import subprocess
from typing import Any
import xml.etree.ElementTree as ET

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .beastmaker_v14_paths import (
    ACCEPTED_V14_PATHS,
    ACCEPTED_V14_PATHS_SHA256,
    accepted_v14_paths_sha256,
)
from .cli import main as cli_main
from .display_paths import DisplayPath, flatten_display_path, parse_display_path
from .image_io import load_image
from .photo_cleanup import PhotoCleanup, clean_beastmaker_photo
from .product_render import load_render_asset
from .templates import ProductTemplate, get_product_template


_SOURCE_SHAPE = (318, 1080, 3)
_SOURCE_RGB_SHA256 = "e1429eefc16670169b032545fe1093272ca0fb9b5fdb67d7a85b1289b9f19dd3"
_SOURCE_CROP = (35, 30, 1041, 289)
_CANONICAL_SIZE = (1000, 259)
_SVG_NS = "{http://www.w3.org/2000/svg}"
_BACKGROUND = (248, 247, 244)
_PACKAGED_RASTER_SHA256 = "4bd615d34bf60d083d4bb7da945cdbe23a59858a430d268d25c2c67308f23627"
_V14_STAGE3_SVG_SHA256 = "8346788e3b7e8d8f7b034d19e647a07eaac3e567854a8b66ca013a2413b508ba"
# Retained for callers that imported the older symbol; V14 supersedes V5.
_V5_STAGE3_SVG_SHA256 = _V14_STAGE3_SVG_SHA256
_CAPTURE_SIZE = (2800, 1000)
_CAPTURE_SCALE = 2.8
_CAPTURE_OFFSET_Y = (_CAPTURE_SIZE[1] - _CANONICAL_SIZE[1] * _CAPTURE_SCALE) / 2
_CAPTURE_BACKGROUND = (255, 255, 255)
_HIGHLIGHT_COLOR = np.array((255, 90, 31), dtype=np.float64)
_HIGHLIGHT_OPACITY = 0.48
_MIXED_HARD_EDGE_PATH_IDS = frozenset(
    {"jug-left", "jug-right", "sloper-35-left", "sloper-35-right"}
)
_HIGHLIGHT_SCENARIOS: Mapping[str, tuple[str, ...]] = {
    "jugs": ("jug-left", "jug-right"),
    "slopers": ("sloper-35-left", "sloper-35-right", "sloper-center"),
    "symmetric-pockets": ("pocket-middle-outer-left", "pocket-middle-outer-right"),
    "mixed-grips": (
        "jug-left",
        "sloper-center",
        "pocket-top-right",
        "pocket-middle-center",
        "pocket-bottom-mid-left",
        "pocket-bottom-mid-right",
    ),
    "all-22": tuple(ACCEPTED_V14_PATHS),
}
_FULL_SUITE_PROVENANCE = {
    "command": "rtk python -m pytest -q --junitxml stage-5-full-suite.xml",
}

_V14_ACCEPTED_EVIDENCE_RESOURCE = "beastmaker-v14-accepted-evidence.json"
_V3_PATH_OVERRIDES = {
    # These are deliberately explicit review-candidate paths, not detector
    # output. Both outer top pockets move up one canonical pixel as a mirrored
    # pair while retaining their exact widths, radii, and IDs.
    "pocket-top-outer-left": "M 56 72 L 158 72 Q 172 72 172 86 L 172 89 Q 172 103 158 103 L 56 103 Q 42 103 42 89 L 42 86 Q 42 72 56 72 Z",
    "pocket-top-outer-right": "M 944 72 L 842 72 Q 828 72 828 86 L 828 89 Q 828 103 842 103 L 944 103 Q 958 103 958 89 L 958 86 Q 958 72 944 72 Z",
}
_V4_PATH_OVERRIDES = {
    # The Stage 1 cavity mouths are visibly taller than the reviewed v3 pair.
    # These explicit curves lift the upper lip 12 px and the lower lip 3 px.
    "pocket-top-outer-left": "M 56 60 L 158 60 Q 172 60 172 74 L 172 83 Q 172 100 158 100 L 56 100 Q 42 100 42 83 L 42 74 Q 42 60 56 60 Z",
    "pocket-top-outer-right": "M 944 60 L 842 60 Q 828 60 828 74 L 828 83 Q 828 100 842 100 L 944 100 Q 958 100 958 83 L 958 74 Q 958 60 944 60 Z",
    # Shift the inner pair outward equally, retaining the center-pocket gaps.
    "pocket-middle-inner-left": "M 314 126 L 388 126 Q 402 126 402 140 L 402 148 Q 402 162 388 162 L 314 162 Q 300 162 300 148 L 300 140 Q 300 126 314 126 Z",
    "pocket-middle-inner-right": "M 612 126 L 686 126 Q 700 126 700 140 L 700 148 Q 700 162 686 162 L 612 162 Q 598 162 598 148 L 598 140 Q 598 126 612 126 Z",
}
_V5_PATH_OVERRIDES = {
    # V4's approved outer-top pair remains untouched. This matched inner pair
    # moves another 6 px outward and 3 px upward to the visible cavity mouths.
    "pocket-middle-inner-left": "M 308 123 L 382 123 Q 396 123 396 137 L 396 145 Q 396 159 382 159 L 308 159 Q 294 159 294 145 L 294 137 Q 294 123 308 123 Z",
    "pocket-middle-inner-right": "M 618 123 L 692 123 Q 706 123 706 137 L 706 145 Q 706 159 692 159 L 618 159 Q 604 159 604 145 L 604 137 Q 604 123 618 123 Z",
}
_FINAL_V5_CHANGED_IDS = frozenset(
    {
        "pocket-top-outer-left",
        "pocket-top-outer-right",
        "pocket-middle-inner-left",
        "pocket-middle-inner-right",
    }
)
_FINAL_V5_PATH_OVERRIDES = {
    "pocket-top-outer-left": _V4_PATH_OVERRIDES["pocket-top-outer-left"],
    "pocket-top-outer-right": _V4_PATH_OVERRIDES["pocket-top-outer-right"],
    **_V5_PATH_OVERRIDES,
}


@dataclass(frozen=True, slots=True)
class ReplaySummary:
    """Paths and immutable evidence collected through the first visual gate."""

    artifact_root: Path
    metrics: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class FullSuiteVerification:
    """Machine-readable full-suite result created for one final replay run."""

    command: str
    exit_status: int
    passed_count: int
    revision: str


@dataclass(frozen=True, slots=True)
class RepositoryState:
    """Clean repository identity recorded with a production suite result."""

    revision: str
    tree: str
    status: str


def discover_beastmaker_golden_root(*, required: bool = False) -> Path | None:
    """Find untracked Beastmaker goldens from a main checkout or linked worktree.

    ``HANGBOARD_REPLAY_GOLDEN_ROOT`` is an explicit request: an invalid value
    raises rather than silently skipping high-value golden tests.
    """
    configured = os.environ.get("HANGBOARD_REPLAY_GOLDEN_ROOT")
    if configured is not None:
        root = Path(configured).expanduser().resolve()
        if _is_golden_root(root):
            return root
        raise FileNotFoundError(f"configured Beastmaker golden root is incomplete: {root}")
    starts = (Path.cwd().resolve(), Path(__file__).resolve())
    seen: set[Path] = set()
    for start in starts:
        for parent in (start, *start.parents):
            root = parent / "work" / "real-beastmaker"
            if root in seen:
                continue
            seen.add(root)
            if _is_golden_root(root):
                return root
    if required:
        raise FileNotFoundError("could not find Beastmaker replay golden artifacts")
    return None


def final_v5_template() -> ProductTemplate:
    """Backward-compatible name for the superseding V14 package contract."""
    return final_v14_template()


def final_v5_candidate_document() -> dict[str, object]:
    """Backward-compatible V14 package contract serialization."""
    return final_v14_candidate_document()


def final_v14_template() -> ProductTemplate:
    """Return the packaged template only when it matches the reviewed V14 contract."""
    candidate = get_product_template("beastmaker-1000")
    _validate_candidate_topology(candidate)
    _assert_final_v14_paths(candidate)
    return candidate


def final_v14_candidate_document() -> dict[str, object]:
    """Serialize the exact reviewed V14 path contract and package parity."""
    candidate = final_v14_template()
    return {
        "acceptedPackagePathIds": list(ACCEPTED_V14_PATHS),
        "acceptedPathsSha256": ACCEPTED_V14_PATHS_SHA256,
        "packagedPathParity": True,
        "paths": [
            {
                "id": region.id,
                "type": region.type,
                "displayPath": region.display_path.data if region.display_path else None,
            }
            for region in candidate.regions
        ],
    }


def run_replay_first_gate(source_path: Path, artifact_root: Path) -> ReplaySummary:
    """Write Stage 0--2 evidence without modifying a golden or package resource.

    ``artifact_root`` must be a new versioned directory below the caller's
    replay root. Refusing an existing directory makes accidental replacement
    of a reviewed replay attempt impossible.
    """
    source_path = source_path.resolve()
    artifact_root = artifact_root.resolve()
    source_rgb = _load_registered_source(source_path)
    if artifact_root.exists():
        raise FileExistsError(f"replay artifact root already exists: {artifact_root}")
    artifact_root.mkdir(parents=True)

    golden_root = source_path.parent
    template = get_product_template("beastmaker-1000")
    _write_stage_zero(source_rgb, template, artifact_root)

    automated = clean_beastmaker_photo(source_rgb)
    manual_rgba = _load_rgba(golden_root / "photo-proof-fix1-v3.png")
    manual_review = _load_rgb(golden_root / "photo-proof-fix1-v3-review.png")
    package_png = _package_asset_path(template)
    packaged_rgba = _load_rgba(package_png)
    _require_same_shape(automated.rgba, manual_rgba, "automated/manual cleanup")
    _require_same_shape(automated.rgba, packaged_rgba, "automated/packaged raster")

    automated_rgba_path = artifact_root / "stage-1-auto-rgba.png"
    automated_review_path = artifact_root / "stage-1-auto-review.png"
    manual_rgba_path = golden_root / "photo-proof-fix1-v3.png"
    manual_review_path = golden_root / "photo-proof-fix1-v3-review.png"
    rgba_file_reproduced = _write_reproduced_png(
        automated_rgba_path, automated.rgba, manual_rgba_path, mode="RGBA"
    )
    review_file_reproduced = _write_reproduced_png(
        automated_review_path, automated.review_rgb, manual_review_path, mode="RGB"
    )
    comparison = _side_by_side(automated.review_rgb, manual_review)
    _save_png(artifact_root / "stage-1-auto-vs-manual.png", comparison)
    _save_png(
        artifact_root / "stage-1-diff-heatmap.png",
        _difference_heatmap(automated.rgba, manual_rgba),
    )
    metrics = _comparison_metrics(
        automated.rgba,
        manual_rgba,
        packaged_rgba,
        automated_review=automated.review_rgb,
        manual_review=manual_review,
        file_paths={
            "automatedRgba": automated_rgba_path,
            "manualRgba": manual_rgba_path,
            "packagedRgba": package_png,
            "automatedReview": automated_review_path,
            "manualReview": manual_review_path,
        },
        encodedFromGolden={
            "automatedRgba": rgba_file_reproduced,
            "automatedReview": review_file_reproduced,
        },
    )
    _write_json(artifact_root / "stage-1-metrics.json", metrics)

    topology = _validate_and_record_topology(template, golden_root)
    _write_json(artifact_root / "stage-2-topology.json", topology)
    _save_png(
        artifact_root / "stage-2-auto-regions-labeled.png",
        _labeled_regions(automated.rgba, template),
    )
    return ReplaySummary(artifact_root=artifact_root, metrics=metrics)


def run_replay_final(
    source_path: Path,
    artifact_root: Path,
    *,
    full_suite_runner: Callable[[Path, Path], FullSuiteVerification] | None = None,
) -> ReplaySummary:
    """Write post-approval SVG, interaction, and immutable evidence artifacts."""
    source_path = source_path.resolve()
    artifact_root = artifact_root.resolve()
    source_rgb = _load_registered_source(source_path)
    if artifact_root.exists():
        raise FileExistsError(f"replay artifact root already exists: {artifact_root}")
    golden_root = source_path.parent
    template = final_v14_template()
    package_png = _package_asset_path(template)
    if _file_sha256(package_png) != _PACKAGED_RASTER_SHA256:
        raise ValueError("packaged Beastmaker raster SHA-256 changed")
    repository_root = Path(__file__).resolve().parents[2]
    repository_state = (
        _repository_state(repository_root)
        if full_suite_runner is not None
        else _require_clean_repository(repository_root)
    )

    artifact_root.mkdir(parents=True)
    svg_path = artifact_root / "stage-3-product.svg"
    manifest_path = artifact_root / "stage-3-manifest.json"
    exit_code = cli_main(
        (
            str(source_path),
            "--product",
            template.product_id,
            "--output",
            str(svg_path),
            "--manifest",
            str(manifest_path),
            "--workspace-root",
            str(artifact_root),
        )
    )
    if exit_code != 0:
        raise RuntimeError(f"production Beastmaker conversion failed with exit code {exit_code}")
    if _file_sha256(svg_path) != _V14_STAGE3_SVG_SHA256:
        raise ValueError("Stage 3 V14 SVG SHA-256 drifted from the approved production output")

    normal_path = artifact_root / "stage-3-normal.png"
    normal_golden = golden_root / "product-render-proof-task4-normal.png"
    normal = _composite_stage3_normal(svg_path)
    accepted_normal = _load_rgb(normal_golden)
    _save_png(normal_path, normal)
    numbered_map_path = artifact_root / "stage-3-numbered-hold-map.png"
    _save_png(numbered_map_path, _numbered_hold_map(normal, template))
    parity = _stage_three_parity(
        template, svg_path, manifest_path, normal, accepted_normal, package_png
    )
    _write_json(artifact_root / "stage-3-parity.json", parity)

    accepted_evidence = load_v14_accepted_evidence()
    traceability = v14_candidate_traceability(template, accepted_evidence)
    highlight_metrics = _write_highlight_replay(
        template, svg_path, normal, accepted_normal, golden_root, artifact_root,
        accepted_evidence,
    )
    _write_json(artifact_root / "stage-4-highlights.json", highlight_metrics)

    cleanup = clean_beastmaker_photo(source_rgb)
    manual_rgba = _load_rgba(golden_root / "photo-proof-fix1-v3.png")
    packaged_rgba = _load_rgba(package_png)
    cleanup_metrics = _comparison_metrics(
        cleanup.rgba,
        manual_rgba,
        packaged_rgba,
        automated_review=cleanup.review_rgb,
        manual_review=_load_rgb(golden_root / "photo-proof-fix1-v3-review.png"),
    )
    result_path = artifact_root / "stage-5-full-suite.xml"
    invocation = (
        {"mode": "injected"}
        if full_suite_runner is not None
        else {
            "mode": "fresh",
            "nonce": token_urlsafe(16),
            "startedAt": datetime.now(timezone.utc).isoformat(),
        }
    )
    verification = (full_suite_runner or _run_full_suite)(repository_root, result_path)
    final_repository_state = (
        _repository_state(repository_root)
        if full_suite_runner is not None
        else _require_clean_repository(repository_root)
    )
    if final_repository_state != repository_state:
        raise ValueError("repository changed while running the full pytest suite")
    _validate_full_suite_verification(
        verification, result_path, repository_state.revision
    )
    summary = {
        "source": {
            "rgbSha256": sha256(source_rgb.tobytes()).hexdigest(),
            "shape": list(source_rgb.shape),
        },
        "cleanup": cleanup_metrics,
        "template": {
            "sha256": _file_sha256(_package_template_path(template)),
            "acceptedV14PathIds": list(ACCEPTED_V14_PATHS),
            "acceptedV14PathsSha256": ACCEPTED_V14_PATHS_SHA256,
            "regionCount": len(template.regions),
            "typeCounts": dict(sorted(Counter(region.type for region in template.regions).items())),
            "centerSloperCount": sum(region.id == "sloper-center" for region in template.regions),
        },
        "svg": {
            "sha256": _file_sha256(svg_path),
            "acceptedSupersededSha256": _file_sha256(
                golden_root / "product-render-proof-task4.svg"
            ),
            "parityPassed": parity["passed"],
        },
        "manifest": {"sha256": _file_sha256(manifest_path)},
        "normal": {
            "sha256": _file_sha256(normal_path),
            "numberedHoldMapSha256": _file_sha256(numbered_map_path),
            **parity["normalCapture"],
        },
        "highlights": highlight_metrics,
        "candidateTraceability": traceability,
        "acceptedEvidence": {
            "candidatePathsSha256": accepted_evidence["evidence"]["candidatePathsSha256"],
            "approvedNormalSha256": accepted_evidence["evidence"]["approvedNormalSha256"],
        },
        "packagedRaster": {
            "sha256": _file_sha256(package_png),
            "expectedSha256": _PACKAGED_RASTER_SHA256,
            "unchanged": _file_sha256(package_png) == _PACKAGED_RASTER_SHA256,
        },
        "acceptedSvg": {
            "sha256": _file_sha256(golden_root / "product-render-proof-task4.svg"),
            "superseded": True,
        },
        "gates": {
            "stage3Parity": parity["passed"],
            "stage4Highlights": highlight_metrics["passed"],
            "packagedRasterUnchanged": _file_sha256(package_png) == _PACKAGED_RASTER_SHA256,
            "normalExercisesGeneratedSvg": parity["normalCapture"]["generatedFromSvg"],
        },
        "verification": {
            "fullSuite": {
                **_FULL_SUITE_PROVENANCE,
                "exitStatus": verification.exit_status,
                "passedCount": verification.passed_count,
                "revision": verification.revision,
                "tree": repository_state.tree,
                "worktreeStatus": repository_state.status,
                "invocation": invocation,
            }
        },
    }
    _write_json(artifact_root / "stage-5-summary.json", summary)
    return ReplaySummary(artifact_root=artifact_root, metrics=summary)


def run_replay_v3_topology_refinement(
    stage_one_rgba_path: Path, artifact_root: Path
) -> ReplaySummary:
    """Write a non-packaged Stage 2 candidate that preserves the v2 evidence.

    The candidate is intentionally limited to a reviewed mirrored adjustment
    for the two outer top pockets. The other 20 paths remain byte-for-byte
    template paths, which makes the delta and its topology impact explicit.
    """
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"replay artifact root already exists: {artifact_root}")
    rgba = _load_rgba(stage_one_rgba_path.resolve())
    template = get_product_template("beastmaker-1000")
    candidate = _v3_candidate_template(template)
    artifact_root.mkdir(parents=True)
    _save_png(
        artifact_root / "stage-2-auto-regions-labeled.png",
        _labeled_regions(rgba, candidate, title="Stage 2 — v3 candidate selectable-region trace (22 regions)"),
    )
    _save_png(
        artifact_root / "stage-2-v2-v3-geometry-delta.png",
        _geometry_delta(rgba, template, candidate),
    )
    metrics = _candidate_metrics(rgba, template, candidate)
    _write_json(artifact_root / "stage-2-refinement-metrics.json", metrics)
    _write_json(
        artifact_root / "stage-2-candidate-topology.json",
        {
            "orderedIds": [region.id for region in candidate.regions],
            "typeCounts": dict(sorted(Counter(region.type for region in candidate.regions).items())),
            "sloperIds": [region.id for region in candidate.regions if region.type == "sloper"],
            "changedIds": sorted(_V3_PATH_OVERRIDES),
            "paths": [
                {"id": region.id, "type": region.type, "displayPath": region.display_path.data if region.display_path else None}
                for region in candidate.regions
            ],
        },
    )
    return ReplaySummary(artifact_root=artifact_root, metrics=metrics)


def run_replay_v4_topology_refinement(
    stage_one_rgba_path: Path, artifact_root: Path
) -> ReplaySummary:
    """Write the next explicit Stage 2 candidate without replacing v2 or v3."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"replay artifact root already exists: {artifact_root}")
    rgba = _load_rgba(stage_one_rgba_path.resolve())
    v2 = get_product_template("beastmaker-1000")
    v3 = _v3_candidate_template(v2)
    v4 = _template_with_path_overrides(v3, _V4_PATH_OVERRIDES, "replayV4")
    _validate_candidate_topology(v4)
    topology = _candidate_overlap_metrics(v4)
    if topology["unexpectedOverlapPixels"] != 0:
        raise ValueError("v4 candidate paths overlap")
    artifact_root.mkdir(parents=True)
    _save_png(
        artifact_root / "stage-2-auto-regions-labeled.png",
        _labeled_regions(rgba, v4, title="Stage 2 — v4 candidate selectable-region trace (22 regions)"),
    )
    _save_png(
        artifact_root / "stage-2-v3-v4-geometry-delta.png",
        _four_region_closeups(rgba, v3, v4, include_old=True),
    )
    _save_png(
        artifact_root / "stage-2-cavity-fit-closeups.png",
        _four_region_closeups(rgba, v3, v4, include_old=False),
    )
    metrics = _v4_metrics(rgba, v2, v3, v4, topology)
    _write_json(artifact_root / "stage-2-refinement-metrics.json", metrics)
    _write_json(
        artifact_root / "stage-2-candidate-topology.json",
        {
            "orderedIds": [region.id for region in v4.regions],
            "typeCounts": dict(sorted(Counter(region.type for region in v4.regions).items())),
            "sloperIds": [region.id for region in v4.regions if region.type == "sloper"],
            "changedIdsFromV2": sorted(_V4_PATH_OVERRIDES),
            "unchangedPathCountFromV2": 18,
            **topology,
        },
    )
    return ReplaySummary(artifact_root=artifact_root, metrics=metrics)


def run_replay_v5_topology_refinement(
    stage_one_rgba_path: Path, artifact_root: Path
) -> ReplaySummary:
    """Write the focused inner-pair V5 candidate without replacing V2--V4."""
    artifact_root = artifact_root.resolve()
    if artifact_root.exists():
        raise FileExistsError(f"replay artifact root already exists: {artifact_root}")
    rgba = _load_rgba(stage_one_rgba_path.resolve())
    v2 = get_product_template("beastmaker-1000")
    v3 = _v3_candidate_template(v2)
    v4 = _template_with_path_overrides(v3, _V4_PATH_OVERRIDES, "replayV4")
    v5 = final_v5_template()
    _validate_candidate_topology(v5)
    topology = _candidate_overlap_metrics(v5)
    if topology["unexpectedOverlapPixels"] != 0:
        raise ValueError("v5 candidate paths overlap")
    artifact_root.mkdir(parents=True)
    _save_png(
        artifact_root / "stage-2-auto-regions-labeled.png",
        _labeled_regions(rgba, v5, title="Stage 2 — v5 candidate selectable-region trace (22 regions)"),
    )
    _save_png(
        artifact_root / "stage-2-v4-v5-geometry-delta.png",
        _inner_pair_closeups(rgba, v4, v5, include_old=True),
    )
    _save_png(
        artifact_root / "stage-2-cavity-fit-closeups.png",
        _inner_pair_closeups(rgba, v4, v5, include_old=False),
    )
    metrics = _v5_metrics(rgba, v4, v5, topology)
    _write_json(artifact_root / "stage-2-refinement-metrics.json", metrics)
    _write_json(
        artifact_root / "stage-2-candidate-topology.json",
        {
            **final_v5_candidate_document(),
            "orderedIds": [region.id for region in v5.regions],
            "typeCounts": dict(sorted(Counter(region.type for region in v5.regions).items())),
            "sloperIds": [region.id for region in v5.regions if region.type == "sloper"],
            "changedIdsFromV4": sorted(_V5_PATH_OVERRIDES),
            "unchangedPathCountFromV4": 20,
            **topology,
        },
    )
    return ReplaySummary(artifact_root=artifact_root, metrics=metrics)


def _run_full_suite(repository_root: Path, result_path: Path) -> FullSuiteVerification:
    """Execute the real suite and retain its JUnit output inside this replay."""
    if shutil.which("rtk") is None:
        raise RuntimeError(
            "full pytest suite requires the 'rtk' executable on PATH; "
            "install rtk or provide full_suite_runner"
        )
    command = (
        "rtk",
        "python",
        "-m",
        "pytest",
        "-q",
        "--junitxml",
        str(result_path),
    )
    try:
        completed = subprocess.run(command, cwd=repository_root, check=False, timeout=120)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("full pytest suite exceeded the 120-second timeout") from error
    if not result_path.is_file():
        raise RuntimeError("full pytest suite did not produce its JUnit result")
    passed_count = _junit_passed_count(result_path)
    return FullSuiteVerification(
        command=_FULL_SUITE_PROVENANCE["command"],
        exit_status=completed.returncode,
        passed_count=passed_count,
        revision=_current_revision(repository_root),
    )


def _validate_full_suite_verification(
    verification: FullSuiteVerification, result_path: Path, revision: str
) -> None:
    if verification.command != _FULL_SUITE_PROVENANCE["command"]:
        raise ValueError("full-suite verification command is not the canonical pytest command")
    if verification.exit_status != 0:
        raise ValueError("full-suite verification did not pass")
    if verification.revision != revision:
        raise ValueError("full-suite verification revision is stale")
    if not result_path.is_file():
        raise ValueError("full-suite verification must provide a fresh JUnit result")
    passed_count = _junit_passed_count(result_path)
    if passed_count != verification.passed_count or passed_count <= 0:
        raise ValueError("full-suite verification passed count does not match JUnit result")


def _require_clean_repository(repository_root: Path) -> RepositoryState:
    state = _repository_state(repository_root)
    if state.status != "clean":
        raise ValueError("full replay requires a clean Git worktree")
    return state


def _repository_state(repository_root: Path) -> RepositoryState:
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    tree = subprocess.run(
        ("git", "write-tree"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not tree:
        raise RuntimeError("could not determine replay tree identity")
    return RepositoryState(
        revision=_current_revision(repository_root),
        tree=tree,
        status="clean" if not status else "dirty",
    )


def _junit_passed_count(result_path: Path) -> int:
    root = ET.parse(result_path).getroot()
    suites = [root] if root.tag == "testsuite" else root.findall("testsuite")
    if not suites:
        raise ValueError("full-suite JUnit result contains no test suites")
    tests = failures = errors = skipped = 0
    for suite in suites:
        try:
            tests += int(suite.attrib.get("tests", "0"))
            failures += int(suite.attrib.get("failures", "0"))
            errors += int(suite.attrib.get("errors", "0"))
            skipped += int(suite.attrib.get("skipped", "0"))
        except ValueError as error:
            raise ValueError("full-suite JUnit result contains invalid counters") from error
    return tests - failures - errors - skipped


def _current_revision(repository_root: Path) -> str:
    completed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=repository_root,
        check=True,
        capture_output=True,
        text=True,
    )
    revision = completed.stdout.strip()
    if not revision:
        raise RuntimeError("could not determine replay revision")
    return revision


def _stage_three_image(root: ET.Element) -> tuple[ET.Element, dict[str, object]]:
    view_box = _svg_numbers(root.attrib.get("viewBox"), "SVG viewBox", 4)
    if view_box != (0.0, 0.0, *_CANONICAL_SIZE):
        raise ValueError("Stage 3 SVG viewBox must equal the canonical product canvas")
    root_preserve = root.attrib.get("preserveAspectRatio", "xMidYMid meet")
    if root_preserve != "xMidYMid meet":
        raise ValueError("Stage 3 SVG must use the browser meet transform")
    images = root.findall(f"{_SVG_NS}image")
    if len(images) != 1:
        raise ValueError("Stage 3 SVG must contain one embedded product raster")
    image = images[0]
    image_bounds = tuple(
        _svg_number(image.attrib.get(attribute), f"SVG image {attribute}")
        for attribute in ("x", "y", "width", "height")
    )
    if image_bounds != (0.0, 0.0, *_CANONICAL_SIZE):
        raise ValueError("Stage 3 SVG image bounds must cover the canonical canvas")
    image_preserve = image.attrib.get("preserveAspectRatio")
    if image_preserve != "none":
        raise ValueError("Stage 3 SVG image must preserve the exact raster placement")
    href = image.attrib.get("href", "")
    prefix = "data:image/png;base64,"
    if not href.startswith(prefix):
        raise ValueError("Stage 3 SVG image must embed a PNG data URL")
    try:
        png_bytes = b64decode(href[len(prefix):], validate=True)
    except ValueError as error:
        raise ValueError("Stage 3 SVG image has invalid PNG data") from error
    return image, {
        "viewBox": view_box,
        "rootPreserveAspectRatio": root_preserve,
        "imageBounds": image_bounds,
        "imagePreserveAspectRatio": image_preserve,
        "pngBytes": png_bytes,
    }


def _svg_number(value: str | None, field: str) -> float:
    if value is None:
        raise ValueError(f"{field} is required")
    try:
        number = float(value)
    except ValueError as error:
        raise ValueError(f"{field} must be numeric") from error
    if not np.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def _svg_numbers(value: str | None, field: str, count: int) -> tuple[float, ...]:
    if value is None:
        raise ValueError(f"{field} is required")
    numbers = tuple(_svg_number(item, field) for item in value.replace(",", " ").split())
    if len(numbers) != count:
        raise ValueError(f"{field} must contain {count} values")
    return numbers


def _composite_stage3_normal(svg_path: Path) -> np.ndarray:
    root = ET.parse(svg_path).getroot()
    _, geometry = _stage_three_image(root)
    view_x, view_y, view_width, view_height = geometry["viewBox"]
    image_x, image_y, image_width, image_height = geometry["imageBounds"]
    with Image.open(BytesIO(geometry["pngBytes"])) as image:
        image.load()
        rgba = image.convert("RGBA")
    if rgba.size != (int(view_width), int(view_height)):
        raise ValueError("Stage 3 embedded raster dimensions must equal the viewBox")

    scale = min(_CAPTURE_SIZE[0] / view_width, _CAPTURE_SIZE[1] / view_height)
    offset_x = (_CAPTURE_SIZE[0] - view_width * scale) / 2 - view_x * scale
    offset_y = (_CAPTURE_SIZE[1] - view_height * scale) / 2 - view_y * scale
    destination = (
        offset_x + image_x * scale,
        offset_y + image_y * scale,
        image_width * scale,
        image_height * scale,
    )
    left, top, width, height = destination
    resized = rgba.resize((round(width), int(np.ceil(height))), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", _CAPTURE_SIZE, (*_CAPTURE_BACKGROUND, 255))
    canvas.alpha_composite(resized, (round(left), round(top)))
    return np.asarray(canvas.convert("RGB"))


def _normal_capture_metrics(
    generated: np.ndarray, accepted: np.ndarray, geometry: Mapping[str, object]
) -> dict[str, object]:
    if generated.shape != accepted.shape:
        raise ValueError("generated and accepted normal captures must share a canvas")
    error = np.abs(generated.astype(np.int16) - accepted.astype(np.int16))
    generated_mask = np.max(
        np.abs(generated.astype(np.int16) - np.asarray(_CAPTURE_BACKGROUND, dtype=np.int16)),
        axis=2,
    ) > 2
    accepted_mask = np.max(
        np.abs(accepted.astype(np.int16) - np.asarray(_CAPTURE_BACKGROUND, dtype=np.int16)),
        axis=2,
    ) > 2
    intersection = int(np.count_nonzero(generated_mask & accepted_mask))
    union = int(np.count_nonzero(generated_mask | accepted_mask))
    generated_bounds = _mask_bounds(generated_mask)
    accepted_bounds = _mask_bounds(accepted_mask)
    return {
        "generatedFromSvg": True,
        "expectedCanvas": list(_CAPTURE_SIZE),
        "canonicalToCapture": {
            "scale": _CAPTURE_SCALE,
            "offsetX": 0.0,
            "offsetY": _CAPTURE_OFFSET_Y,
        },
        "parsedSvg": {
            "viewBox": list(geometry["viewBox"]),
            "imageBounds": list(geometry["imageBounds"]),
            "rootPreserveAspectRatio": geometry["rootPreserveAspectRatio"],
            "imagePreserveAspectRatio": geometry["imagePreserveAspectRatio"],
        },
        "rgbMaeAgainstAccepted": float(error.mean()),
        "rgbMaxAbsErrorAgainstAccepted": int(error.max()),
        "productMaskIouWithAccepted": float(intersection / union) if union else 1.0,
        "generatedProductBounds": generated_bounds,
        "acceptedProductBounds": accepted_bounds,
        "layoutBoundsExact": generated_bounds == accepted_bounds,
    }


def _mask_bounds(mask: np.ndarray) -> list[int] | None:
    points = cv2.findNonZero(mask.astype(np.uint8))
    if points is None:
        return None
    x, y, width, height = cv2.boundingRect(points)
    return [int(x), int(y), int(width), int(height)]


def _stage_three_parity(
    template: ProductTemplate,
    svg_path: Path,
    manifest_path: Path,
    normal: np.ndarray,
    accepted_normal: np.ndarray,
    package_png: Path,
) -> dict[str, object]:
    root = ET.parse(svg_path).getroot()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image, image_geometry = _stage_three_image(root)
    images = root.findall(f"{_SVG_NS}image")
    paths = root.findall(f"{_SVG_NS}path")
    grip_paths = [path for path in paths if path.attrib.get("class") == "grip-region"]
    opening_paths = [path for path in paths if path.attrib.get("class") == "opening"]
    decorative_paths = [
        path
        for path in paths
        if path.attrib.get("class", "").startswith("grip-decoration")
    ]
    if len(images) != 1 or image.attrib.get("class") != "product-render":
        raise ValueError("stage 3 SVG must contain one embedded product raster")
    if image_geometry["pngBytes"] != load_render_asset(template):
        raise ValueError("stage 3 SVG does not embed exact packaged raster bytes")

    expected_ids = [region.id for region in template.regions]
    expected_types = [region.type for region in template.regions]
    svg_ids = [path.attrib["id"] for path in grip_paths]
    manifest_ids = [region["id"] for region in manifest["regions"]]
    manifest_types = [region["type"] for region in manifest["regions"]]
    root_children = list(root)
    image_index = root_children.index(image)
    first_grip_index = min(root_children.index(path) for path in grip_paths)
    path_parity = all(
        path.attrib.get("d") == region.display_path.data
        for path, region in zip(grip_paths, template.regions, strict=True)
        if region.display_path is not None
    )
    normal_capture = _normal_capture_metrics(normal, accepted_normal, image_geometry)
    passed = (
        image_index < first_grip_index
        and svg_ids == expected_ids
        and manifest_ids == expected_ids
        and [path.attrib["data-type"] for path in grip_paths] == expected_types
        and manifest_types == expected_types
        and len(grip_paths) == 22
        and Counter(expected_types) == {"pocket": 17, "sloper": 3, "jug": 2}
        and svg_ids.count("sloper-center") == 1
        and not opening_paths
        and not decorative_paths
        and path_parity
        and normal.shape == (_CAPTURE_SIZE[1], _CAPTURE_SIZE[0], 3)
        and normal_capture["layoutBoundsExact"]
        and normal_capture["productMaskIouWithAccepted"] >= 0.995
        and normal_capture["rgbMaeAgainstAccepted"] <= 4.0
    )
    if not passed:
        raise ValueError("stage 3 SVG/manifest parity gate failed")
    return {
        "passed": passed,
        "embeddedRasterCount": len(images),
        "embeddedPackagedBytesExact": True,
        "imageBeforeOverlay": image_index < first_grip_index,
        "orderedSvgIds": svg_ids,
        "orderedManifestIds": manifest_ids,
        "regionPathCount": len(grip_paths),
        "typeCounts": dict(sorted(Counter(expected_types).items())),
        "centerSloperCount": svg_ids.count("sloper-center"),
        "openingPathCount": len(opening_paths),
        "decorativePathCount": len(decorative_paths),
        "svgManifestIdParity": svg_ids == manifest_ids,
        "svgPathParityWithPackage": path_parity,
        "normalCaptureCanvas": list(normal.shape[:2][::-1]),
        "normalCapture": normal_capture,
    }


def _write_highlight_replay(
    template: ProductTemplate,
    svg_path: Path,
    normal: np.ndarray,
    accepted_normal: np.ndarray,
    golden_root: Path,
    artifact_root: Path,
    accepted_evidence: Mapping[str, Any],
) -> dict[str, object]:
    svg_paths = _svg_grip_paths(svg_path)
    expected_ids = tuple(region.id for region in template.regions)
    if tuple(svg_paths) != expected_ids:
        raise ValueError("highlight replay requires the ordered Stage 3 SVG paths")
    all_masks = {
        region_id: _capture_path_mask(path, normal.shape[:2])
        for region_id, path in svg_paths.items()
    }
    validate_v14_accepted_masks(all_masks, accepted_evidence)
    if _array_sha256(normal) != accepted_evidence["evidence"]["approvedNormalSha256"]:
        raise ValueError("normal capture drifted from independent accepted evidence")
    scenarios: dict[str, object] = {}
    for name, selected_ids in _HIGHLIGHT_SCENARIOS.items():
        if any(region_id not in svg_paths for region_id in selected_ids):
            raise ValueError(f"highlight scenario {name!r} refers to a missing path")
        selected_mask = np.zeros(normal.shape[:2], dtype=bool)
        for region_id in selected_ids:
            selected_mask |= all_masks[region_id]
        highlighted = _composite_highlight(normal, selected_mask)
        output_path = artifact_root / f"stage-4-highlight-{name}.png"
        _save_png(output_path, highlighted)
        approved = accepted_evidence["scenarios"].get(name)
        if not isinstance(approved, Mapping):
            raise ValueError(f"independent accepted evidence lacks scenario {name!r}")
        if tuple(approved["activeIds"]) != selected_ids:
            raise ValueError(f"independent accepted evidence scenario {name!r} IDs drifted")
        approved_mask_sha = approved["approvedMaskSha256"]
        approved_highlight_sha = approved["approvedHighlightSha256"]
        if _array_sha256(selected_mask) != approved_mask_sha:
            raise ValueError(f"stage 4 {name} mask drifted from independent accepted evidence")
        actual_mask = _changed_mask(normal, highlighted)
        unrelated_mask = np.zeros(normal.shape[:2], dtype=bool)
        for region_id, mask in all_masks.items():
            if region_id not in selected_ids:
                unrelated_mask |= mask
        unrelated_mask &= ~selected_mask
        intersection = int(np.count_nonzero(actual_mask & selected_mask))
        union = int(np.count_nonzero(actual_mask | selected_mask))
        selected_iou = float(intersection / union) if union else 1.0
        outside_selected = int(np.count_nonzero(actual_mask & ~selected_mask))
        unrelated_changed = int(np.count_nonzero(actual_mask & unrelated_mask))
        requested_once = all(tuple(svg_paths).count(region_id) == 1 for region_id in selected_ids)
        scenario = {
            "activeIds": list(selected_ids),
            "requestedIdsExistOnce": requested_once,
            "generatedPngSha256": _file_sha256(output_path),
            "acceptedPngSha256": approved_highlight_sha,
            "approvedMaskSha256": approved_mask_sha,
            "approvedMaskSha256Matched": _array_sha256(selected_mask) == approved_mask_sha,
            "approvedHighlightSha256Matched": _array_sha256(highlighted) == approved_highlight_sha,
            "changedPixelCount": int(np.count_nonzero(actual_mask)),
            "changedPixelsOutsideSelectedMasks": outside_selected,
            "changedPixelsInsideUnrelatedMasks": unrelated_changed,
            "acceptedChangedPixelCount": int(np.count_nonzero(selected_mask)),
            "selectedMaskIouWithAccepted": selected_iou,
            "acceptedMaskIouThreshold": 0.995,
            "acceptedMaskIouPassed": selected_iou >= 0.995,
        }
        if not (
            requested_once
            and outside_selected == 0
            and unrelated_changed == 0
            and selected_iou >= 0.995
            and _array_sha256(highlighted) == approved_highlight_sha
        ):
            raise ValueError(f"stage 4 highlight gate failed for {name}")
        scenarios[name] = scenario
    return {"passed": True, "scenarios": scenarios}


@cache
def load_v14_accepted_evidence() -> Mapping[str, Any]:
    """Load the reviewed candidate evidence without consulting current package paths."""
    document = json.loads(
        resources.files("hangboard_vectorizer.evidence")
        .joinpath(_V14_ACCEPTED_EVIDENCE_RESOURCE)
        .read_text(encoding="utf-8")
    )
    if not isinstance(document, dict) or document.get("schemaVersion") != 1:
        raise ValueError("independent accepted evidence has an unsupported schema")
    if not isinstance(document.get("candidatePaths"), dict):
        raise ValueError("independent accepted evidence lacks candidate paths")
    if not isinstance(document.get("regions"), dict) or not isinstance(document.get("scenarios"), dict):
        raise ValueError("independent accepted evidence lacks masks")
    candidate_paths = document["candidatePaths"]
    if accepted_v14_paths_sha256(candidate_paths) != document["evidence"]["candidatePathsSha256"]:
        raise ValueError("independent accepted evidence candidate paths drifted")
    return document


def validate_v14_accepted_masks(
    masks: Mapping[str, np.ndarray], evidence: Mapping[str, Any]
) -> None:
    """Reject a current Stage 4 mask unless it matches the immutable approval fixture."""
    approved_regions = evidence["regions"]
    if set(masks) != set(approved_regions):
        raise ValueError("independent accepted evidence region inventory drifted")
    for region_id, mask in masks.items():
        approved = approved_regions[region_id]
        if _array_sha256(mask) != approved["approvedMaskSha256"]:
            raise ValueError(f"{region_id} drifted from independent accepted evidence")
        if int(np.count_nonzero(mask)) != approved["approvedMaskPixels"]:
            raise ValueError(f"{region_id} area drifted from independent accepted evidence")


def v14_candidate_traceability(
    template: ProductTemplate, evidence: Mapping[str, Any]
) -> dict[str, object]:
    """Measure promoted compact paths against the reviewed dense candidate map."""
    candidate_paths = evidence["candidatePaths"]
    current_paths = {
        region.id: region.display_path
        for region in template.regions
        if region.display_path is not None
    }
    if set(current_paths) != set(candidate_paths):
        raise ValueError("candidate traceability region inventory drifted")
    tolerances = evidence["traceabilityTolerances"]
    regions: dict[str, object] = {}
    for region_id, current_path in current_paths.items():
        candidate_data = candidate_paths[region_id]
        candidate_path = parse_display_path(
            candidate_data, f"acceptedEvidence.{region_id}", *_CANONICAL_SIZE,
            allow_linear_segments=True,
        )
        if candidate_path is None:
            raise ValueError(f"accepted evidence path {region_id!r} is empty")
        candidate_mask = _capture_path_mask(candidate_path, _CAPTURE_SIZE[::-1])
        current_mask = _capture_path_mask(current_path, _CAPTURE_SIZE[::-1])
        approved = evidence["regions"][region_id]
        if _array_sha256(candidate_mask) != approved["candidateMaskSha256"]:
            raise ValueError(f"accepted evidence candidate mask {region_id!r} drifted")
        intersection = int(np.count_nonzero(candidate_mask & current_mask))
        union = int(np.count_nonzero(candidate_mask | current_mask))
        candidate_pixels = int(np.count_nonzero(candidate_mask))
        current_pixels = int(np.count_nonzero(current_mask))
        candidate_centroid = np.argwhere(candidate_mask).mean(axis=0)
        current_centroid = np.argwhere(current_mask).mean(axis=0)
        iou = float(intersection / union) if union else 1.0
        area_delta = abs(current_pixels - candidate_pixels) / candidate_pixels
        centroid_delta = float(np.linalg.norm(current_centroid - candidate_centroid))
        passed = (
            iou >= tolerances["minMaskIou"]
            and area_delta <= tolerances["maxAreaRelativeDelta"]
            and centroid_delta <= tolerances["maxCentroidDistancePx"]
        )
        if not passed:
            raise ValueError(f"candidate traceability failed for {region_id}")
        regions[region_id] = {
            "candidateMaskSha256": _array_sha256(candidate_mask),
            "currentMaskSha256": _array_sha256(current_mask),
            "maskIou": iou,
            "areaRelativeDelta": area_delta,
            "centroidDistancePx": centroid_delta,
            "passed": passed,
        }
    return {"passed": True, "tolerances": dict(tolerances), "regions": regions}


def _svg_grip_paths(svg_path: Path) -> dict[str, DisplayPath]:
    root = ET.parse(svg_path).getroot()
    result: dict[str, DisplayPath] = {}
    for element in root.findall(f"{_SVG_NS}path[@class='grip-region']"):
        region_id = element.attrib["id"]
        if region_id in result:
            raise ValueError(f"Stage 3 SVG duplicates grip path {region_id!r}")
        path = parse_display_path(
            element.attrib["d"],
            f"stage3.{region_id}",
            _CANONICAL_SIZE[0],
            _CANONICAL_SIZE[1],
            allow_linear_segments=region_id in _MIXED_HARD_EDGE_PATH_IDS,
        )
        if path is None:
            raise ValueError(f"Stage 3 SVG path {region_id!r} is empty")
        result[region_id] = path
    return result


def _capture_path_mask(path: DisplayPath, shape: tuple[int, int]) -> np.ndarray:
    contour = flatten_display_path(path, scale=_CAPTURE_SCALE)
    contour[:, 1] += _CAPTURE_OFFSET_Y
    raster = np.zeros(shape, dtype=np.uint8)
    cv2.fillPoly(raster, [np.rint(contour).astype(np.int32)], 1)
    return raster.astype(bool)


def _composite_highlight(normal: np.ndarray, selected_mask: np.ndarray) -> np.ndarray:
    highlighted = normal.astype(np.float64, copy=True)
    highlighted[selected_mask] = (
        highlighted[selected_mask] * (1.0 - _HIGHLIGHT_OPACITY)
        + _HIGHLIGHT_COLOR * _HIGHLIGHT_OPACITY
    )
    return np.rint(highlighted).astype(np.uint8)


def _changed_mask(normal: np.ndarray, image: np.ndarray) -> np.ndarray:
    if image.shape != normal.shape:
        raise ValueError("highlight comparison canvases must have identical dimensions")
    return np.max(np.abs(image.astype(np.int16) - normal.astype(np.int16)), axis=2) > 15


def _load_registered_source(source_path: Path) -> np.ndarray:
    rgb = load_image(str(source_path)).rgb
    if rgb.shape != _SOURCE_SHAPE:
        raise ValueError("Beastmaker replay source must decode as 1080 x 318 RGB")
    fingerprint = sha256(rgb.tobytes()).hexdigest()
    if fingerprint != _SOURCE_RGB_SHA256:
        raise ValueError("Beastmaker replay source fingerprint does not match source.jpg")
    return rgb


def _write_stage_zero(
    source_rgb: np.ndarray, template: ProductTemplate, artifact_root: Path
) -> None:
    left, top, right, bottom = _SOURCE_CROP
    crop = source_rgb[top:bottom, left:right]
    _save_png(artifact_root / "stage-0-crop.png", crop)
    canonical = cv2.resize(crop, _CANONICAL_SIZE, interpolation=cv2.INTER_LANCZOS4)
    overlay = canonical.copy()
    assert template.display_outline_path is not None
    contour = np.rint(flatten_display_path(template.display_outline_path)).astype(np.int32)
    cv2.polylines(overlay, [contour], True, (44, 150, 77), 2, lineType=cv2.LINE_AA)
    cv2.rectangle(overlay, (0, 0), (999, 258), (24, 89, 171), 1, cv2.LINE_AA)
    _save_png(artifact_root / "stage-0-alignment.png", overlay)
    _write_json(
        artifact_root / "stage-0-evidence.json",
        {
            "sourceRgbSha256": sha256(source_rgb.tobytes()).hexdigest(),
            "sourceShape": list(source_rgb.shape),
            "registeredCrop": {"left": left, "top": top, "right": right, "bottom": bottom},
            "cropShape": list(crop.shape),
            "canonicalSize": list(_CANONICAL_SIZE),
            "productId": template.product_id,
        },
    )


def _comparison_metrics(
    automated: np.ndarray,
    manual: np.ndarray,
    packaged: np.ndarray,
    *,
    automated_review: np.ndarray | None = None,
    manual_review: np.ndarray | None = None,
    file_paths: Mapping[str, Path] | None = None,
    encodedFromGolden: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    alpha_auto = automated[..., 3] >= 128
    alpha_manual = manual[..., 3] >= 128
    alpha_intersection = int(np.count_nonzero(alpha_auto & alpha_manual))
    alpha_union = int(np.count_nonzero(alpha_auto | alpha_manual))
    rgb_error = np.abs(automated[..., :3].astype(np.int16) - manual[..., :3].astype(np.int16))
    alpha_error = np.abs(automated[..., 3].astype(np.int16) - manual[..., 3].astype(np.int16))
    metrics: dict[str, object] = {
        "automatedRgbaPixelSha256": _array_sha256(automated),
        "manualRgbaPixelSha256": _array_sha256(manual),
        "packagedRgbaPixelSha256": _array_sha256(packaged),
        # Retained for the original Stage 1 evidence schema. These are pixel
        # hashes, never PNG-file hashes; the explicit fields above remove any
        # ambiguity for later consumers.
        "automatedRgbaSha256": _array_sha256(automated),
        "manualRgbaSha256": _array_sha256(manual),
        "packagedRgbaSha256": _array_sha256(packaged),
        "automatedEqualsManual": bool(np.array_equal(automated, manual)),
        "automatedEqualsPackaged": bool(np.array_equal(automated, packaged)),
        "manualEqualsPackaged": bool(np.array_equal(manual, packaged)),
        "shape": list(automated.shape),
        "rgbMae": float(rgb_error.mean()),
        "rgbMaxAbsError": int(rgb_error.max()),
        "alphaMae": float(alpha_error.mean()),
        "alphaMaxAbsError": int(alpha_error.max()),
        "alphaIoU": float(alpha_intersection / alpha_union) if alpha_union else 1.0,
        "routedEdgeDisplacementPx": _edge_displacement(automated, manual),
        "automatedTransparentRgbZero": _transparent_rgb_is_zero(automated),
        "manualTransparentRgbZero": _transparent_rgb_is_zero(manual),
        "packagedTransparentRgbZero": _transparent_rgb_is_zero(packaged),
    }
    if automated_review is not None or manual_review is not None:
        if automated_review is None or manual_review is None:
            raise ValueError("automated and manual review canvases must be supplied together")
        _require_same_shape(automated_review, manual_review, "automated/manual review")
        review_error = np.abs(
            automated_review.astype(np.int16) - manual_review.astype(np.int16)
        )
        metrics.update(
            {
                "automatedReviewPixelSha256": _array_sha256(automated_review),
                "manualReviewPixelSha256": _array_sha256(manual_review),
                "automatedReviewEqualsManual": bool(
                    np.array_equal(automated_review, manual_review)
                ),
                "reviewRgbMae": float(review_error.mean()),
                "reviewRgbMaxAbsError": int(review_error.max()),
            }
        )
    if file_paths is not None:
        metrics["pngFileSha256"] = {
            name: _file_sha256(path) for name, path in sorted(file_paths.items())
        }
        metrics["pngFileEquality"] = {
            "automatedRgbaEqualsManual": _file_sha256(file_paths["automatedRgba"])
            == _file_sha256(file_paths["manualRgba"]),
            "automatedRgbaEqualsPackaged": _file_sha256(file_paths["automatedRgba"])
            == _file_sha256(file_paths["packagedRgba"]),
            "automatedReviewEqualsManual": _file_sha256(file_paths["automatedReview"])
            == _file_sha256(file_paths["manualReview"]),
        }
    if encodedFromGolden is not None:
        metrics["copiedAcceptedPngBytes"] = dict(sorted(encodedFromGolden.items()))
    return metrics


def _edge_displacement(first: np.ndarray, second: np.ndarray) -> float:
    """Symmetric pixel distance of silhouette and routed luminance edges."""
    def edges(rgba: np.ndarray) -> np.ndarray:
        rgb = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)
        edge = cv2.Canny(rgb, 24, 72) > 0
        alpha_edge = cv2.Canny(rgba[..., 3], 12, 36) > 0
        return edge | alpha_edge

    first_edges = edges(first)
    second_edges = edges(second)
    if np.array_equal(first_edges, second_edges):
        return 0.0
    def directed(source: np.ndarray, target: np.ndarray) -> float:
        if not np.any(source) or not np.any(target):
            return float("inf")
        distance = cv2.distanceTransform((~target).astype(np.uint8), cv2.DIST_L2, 5)
        return float(distance[source].max())
    return max(directed(first_edges, second_edges), directed(second_edges, first_edges))


def _validate_and_record_topology(template: ProductTemplate, golden_root: Path) -> dict[str, object]:
    product_document = json.loads(
        _package_template_path(template).read_text(encoding="utf-8")
    )
    accepted_svg = ET.parse(golden_root / "product-render-proof-task4.svg").getroot()
    accepted_manifest = json.loads(
        (golden_root / "product-render-proof-task4.json").read_text(encoding="utf-8")
    )
    paths = accepted_svg.findall(f".//{_SVG_NS}path[@class='grip-region']")
    raw_regions = product_document["regions"]
    expected_ids = tuple(region.id for region in template.regions)
    expected_types = tuple(region.type for region in template.regions)
    svg_ids = tuple(path.attrib["id"] for path in paths)
    manifest_ids = tuple(region["id"] for region in accepted_manifest["regions"])
    if len(expected_ids) != 22 or Counter(expected_types) != {"pocket": 17, "sloper": 3, "jug": 2}:
        raise ValueError("Beastmaker template must contain the canonical 17/3/2 inventory")
    if tuple(region.id for region in template.regions if region.type == "sloper") != (
        "sloper-35-left", "sloper-35-right", "sloper-center"
    ):
        raise ValueError("Beastmaker replay requires one continuous center sloper")
    if svg_ids != expected_ids or manifest_ids != expected_ids:
        raise ValueError("accepted SVG or manifest does not preserve ordered Beastmaker IDs")
    comparisons: list[dict[str, object]] = []
    for region, raw, path, manifest_region in zip(
        template.regions, raw_regions, paths, accepted_manifest["regions"], strict=True
    ):
        assert region.display_path is not None
        if raw["id"] != region.id or raw["type"] != region.type:
            raise ValueError(f"packaged template mismatch for {region.id}")
        if raw["displayPath"] != region.display_path.data:
            raise ValueError(f"packaged path mismatch for {region.id}")
        if manifest_region["type"] != region.type:
            raise ValueError(f"accepted manifest type mismatch for {region.id}")
        coordinates = np.asarray(region.display_path.coordinates, dtype=np.float64)
        if not ((coordinates[:, 0] >= 0).all() and (coordinates[:, 0] <= template.canonical_width).all() and (coordinates[:, 1] >= 0).all() and (coordinates[:, 1] <= template.canonical_height).all()):
            raise ValueError(f"display path leaves canonical frame for {region.id}")
        comparisons.append({"id": region.id, "type": region.type, "displayPath": region.display_path.data})
    return {
        "orderedIds": list(expected_ids),
        "orderedTypes": list(expected_types),
        "typeCounts": dict(sorted(Counter(expected_types).items())),
        "sloperIds": ["sloper-35-left", "sloper-35-right", "sloper-center"],
        "exactPathParity": True,
        "acceptedSvgPathParity": all(
            path.attrib["d"] == region.display_path.data
            for path, region in zip(paths, template.regions, strict=True)
            if region.display_path is not None
        ),
        "svgManifestIdParity": True,
        "regions": comparisons,
    }


def _numbered_hold_map(normal: np.ndarray, template: ProductTemplate) -> np.ndarray:
    """Overlay the ordered selectable regions on the production normal capture."""
    image = Image.fromarray(normal, mode="RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    draw.rounded_rectangle((20, 16, 385, 50), radius=8, fill=(255, 255, 255, 220))
    draw.text((32, 27), "V14 numbered selectable-hold map", fill=(34, 34, 34), font=font)
    colors = _region_colors(len(template.regions))
    for index, (region, color) in enumerate(zip(template.regions, colors, strict=True), start=1):
        assert region.display_path is not None
        contour = flatten_display_path(region.display_path)
        contour[:, 0] *= _CAPTURE_SCALE
        contour[:, 1] = contour[:, 1] * _CAPTURE_SCALE + _CAPTURE_OFFSET_Y
        points = [(float(x), float(y)) for x, y in contour]
        draw.polygon(points, fill=(*color, 82))
        draw.line(points, fill=(*color, 235), width=3, joint="curve")
        centroid = np.mean(contour[:-1], axis=0)
        _badge(draw, (float(centroid[0]), float(centroid[1])), str(index), color, font)
    return np.asarray(image)


def _labeled_regions(
    rgba: np.ndarray, template: ProductTemplate, *, title: str = "Stage 2 — automated selectable-region trace (22 regions)"
) -> np.ndarray:
    background = np.full((455, 1660, 3), _BACKGROUND, dtype=np.uint8)
    image = Image.fromarray(background)
    draw = ImageDraw.Draw(image, "RGBA")
    font = ImageFont.load_default()
    bold = ImageFont.load_default()
    draw.text((30, 18), title, fill=(34, 34, 34), font=bold)
    product = Image.fromarray(rgba, mode="RGBA")
    image.paste(product, (30, 76), product)
    colors = _region_colors(len(template.regions))
    for index, (region, color) in enumerate(zip(template.regions, colors, strict=True), start=1):
        assert region.display_path is not None
        contour = flatten_display_path(region.display_path)
        points = [(float(x) + 30.0, float(y) + 76.0) for x, y in contour]
        draw.polygon(points, fill=(*color, 94))
        draw.line(points, fill=(*color, 235), width=2, joint="curve")
        centroid = np.mean(contour[:-1], axis=0)
        _badge(draw, (float(centroid[0]) + 30.0, float(centroid[1]) + 76.0), str(index), color, font)
    draw.rectangle((28, 74, 1031, 336), outline=(110, 110, 110, 180), width=1)
    draw.text((30, 354), "Translucent color = hit region; number maps to the legend.", fill=(68, 68, 68), font=font)
    for index, (region, color) in enumerate(zip(template.regions, colors, strict=True), start=1):
        column = 0 if index <= 11 else 1
        row = (index - 1) % 11
        x = 1070 + column * 285
        y = 70 + row * 28
        draw.rounded_rectangle((x, y, x + 18, y + 18), radius=4, fill=(*color, 220))
        draw.text((x + 26, y + 3), f"{index:02d}  {region.id}", fill=(36, 36, 36), font=font)
    return np.asarray(image.convert("RGB"))


def _v3_candidate_template(template: ProductTemplate) -> ProductTemplate:
    candidate = _template_with_path_overrides(template, _V3_PATH_OVERRIDES, "replayV3")
    _validate_candidate_topology(candidate)
    return candidate


def _template_with_path_overrides(
    template: ProductTemplate, overrides: Mapping[str, str], field_prefix: str
) -> ProductTemplate:
    regions = []
    for region in template.regions:
        override = overrides.get(region.id)
        if override is None:
            regions.append(region)
            continue
        regions.append(
            replace(
                region,
                display_path=parse_display_path(
                    override,
                    f"{field_prefix}.{region.id}.displayPath",
                    template.canonical_width,
                    template.canonical_height,
                ),
            )
        )
    return replace(template, regions=tuple(regions))


def _validate_candidate_topology(template: ProductTemplate) -> None:
    if len(template.regions) != 22:
        raise ValueError("candidate must retain 22 regions")
    if Counter(region.type for region in template.regions) != {"pocket": 17, "sloper": 3, "jug": 2}:
        raise ValueError("candidate must retain the canonical 17/3/2 inventory")
    slopers = tuple(region.id for region in template.regions if region.type == "sloper")
    if slopers != ("sloper-35-left", "sloper-35-right", "sloper-center"):
        raise ValueError("candidate must retain one continuous center sloper")
    left = next(region for region in template.regions if region.id == "pocket-top-outer-left")
    right = next(region for region in template.regions if region.id == "pocket-top-outer-right")
    assert left.display_path is not None and right.display_path is not None
    left_coordinates = np.asarray(left.display_path.coordinates)
    right_coordinates = np.asarray(right.display_path.coordinates)
    if not np.array_equal(left_coordinates[:, 1], right_coordinates[:, 1]):
        raise ValueError("candidate outer top pockets must remain level")
    if not np.allclose(left_coordinates[:, 0] + right_coordinates[:, 0], template.canonical_width):
        raise ValueError("candidate outer top pockets must remain mirrored")


def _assert_final_v14_paths(candidate: ProductTemplate) -> None:
    candidate_paths = {
        region.id: region.display_path.data if region.display_path else None
        for region in candidate.regions
    }
    if candidate_paths != dict(ACCEPTED_V14_PATHS):
        raise ValueError("packaged template must retain the exact accepted V14 paths")
    if accepted_v14_paths_sha256({key: value for key, value in candidate_paths.items() if value is not None}) != ACCEPTED_V14_PATHS_SHA256:
        raise ValueError("packaged template V14 path hash drifted from the accepted contract")


def _candidate_metrics(
    rgba: np.ndarray, original: ProductTemplate, candidate: ProductTemplate
) -> dict[str, object]:
    edge_distance = _routed_edge_distance(rgba)
    changes: list[dict[str, object]] = []
    for before, after in zip(original.regions, candidate.regions, strict=True):
        assert before.display_path is not None and after.display_path is not None
        before_score = _path_edge_distance(before.display_path, edge_distance)
        after_score = _path_edge_distance(after.display_path, edge_distance)
        before_coordinates = np.asarray(before.display_path.coordinates)
        after_coordinates = np.asarray(after.display_path.coordinates)
        shifts = after_coordinates[:, 1] - before_coordinates[:, 1]
        changes.append(
            {
                "id": before.id,
                "verticalShiftPx": float(np.mean(shifts)),
                "maxVerticalShiftPx": float(np.max(np.abs(shifts))),
                "v2MeanEdgeDistancePx": before_score,
                "v3MeanEdgeDistancePx": after_score,
                "edgeAlignmentImprovementPx": before_score - after_score,
                "pathChanged": before.display_path.data != after.display_path.data,
            }
        )
    return {
        "method": "deterministic explicit candidate paths scored against Stage 1 Canny routed-edge distance",
        "changedIds": sorted(_V3_PATH_OVERRIDES),
        "regions": changes,
    }


def _candidate_overlap_metrics(template: ProductTemplate) -> dict[str, object]:
    masks: list[tuple[str, np.ndarray]] = []
    for region in template.regions:
        assert region.display_path is not None
        mask = np.zeros((template.canonical_height, template.canonical_width), dtype=np.uint8)
        contour = np.rint(flatten_display_path(region.display_path)).astype(np.int32)
        cv2.fillPoly(mask, [contour], 1)
        masks.append((region.id, mask))
    expected_shared_boundaries = {
        frozenset(("sloper-35-left", "sloper-center")),
        frozenset(("sloper-35-right", "sloper-center")),
    }
    unexpected = 0
    allowed = 0
    for index, (left_id, left_mask) in enumerate(masks):
        for right_id, right_mask in masks[index + 1:]:
            pixels = int(np.count_nonzero((left_mask > 0) & (right_mask > 0)))
            if not pixels:
                continue
            if frozenset((left_id, right_id)) in expected_shared_boundaries:
                allowed += pixels
            else:
                unexpected += pixels
    return {
        "unexpectedOverlapPixels": unexpected,
        "allowedSharedSloperBoundaryPixels": allowed,
        "allPathsInBounds": True,
    }


def _v4_metrics(
    rgba: np.ndarray,
    v2: ProductTemplate,
    v3: ProductTemplate,
    v4: ProductTemplate,
    topology: Mapping[str, object],
) -> dict[str, object]:
    edge_distance = _routed_edge_distance(rgba)
    changes: list[dict[str, object]] = []
    for before, after in zip(v3.regions, v4.regions, strict=True):
        assert before.display_path is not None and after.display_path is not None
        before_coordinates = np.asarray(before.display_path.coordinates)
        after_coordinates = np.asarray(after.display_path.coordinates)
        delta = after_coordinates - before_coordinates
        if before.id not in _V4_PATH_OVERRIDES:
            continue
        changes.append(
            {
                "id": before.id,
                "v3DisplayPath": before.display_path.data,
                "v4DisplayPath": after.display_path.data,
                "v3Coordinates": before_coordinates.tolist(),
                "v4Coordinates": after_coordinates.tolist(),
                "meanShiftPx": {"x": float(delta[:, 0].mean()), "y": float(delta[:, 1].mean())},
                "maxAbsoluteShiftPx": {"x": float(np.abs(delta[:, 0]).max()), "y": float(np.abs(delta[:, 1]).max())},
                "v3LocalEdgeDistancePx": _path_edge_distance(before.display_path, edge_distance),
                "v4LocalEdgeDistancePx": _path_edge_distance(after.display_path, edge_distance),
            }
        )
    by_id = {region.id: region for region in v4.regions}
    def bounds(region_id: str) -> tuple[float, float, float, float]:
        path = by_id[region_id].display_path
        assert path is not None
        points = np.asarray(path.coordinates)
        return (float(points[:, 0].min()), float(points[:, 1].min()), float(points[:, 0].max()), float(points[:, 1].max()))
    center = bounds("pocket-middle-center")
    left = bounds("pocket-middle-inner-left")
    right = bounds("pocket-middle-inner-right")
    return {
        "method": "explicit deterministic review paths fitted against visible Stage 1 cavity mouths and lips; Canny distance is diagnostic only",
        "changedIdsFromV2": sorted(_V4_PATH_OVERRIDES),
        "unchangedPathCountFromV2": sum(
            before.display_path.data == after.display_path.data
            for before, after in zip(v2.regions, v4.regions, strict=True)
        ),
        "regions": changes,
        "innerPairGapToCenterPx": {
            "left": center[0] - left[2],
            "right": right[0] - center[2],
            "difference": abs((center[0] - left[2]) - (right[0] - center[2])),
        },
        **topology,
    }


def _v5_metrics(
    rgba: np.ndarray, v4: ProductTemplate, v5: ProductTemplate, topology: Mapping[str, object]
) -> dict[str, object]:
    edge_distance = _routed_edge_distance(rgba)
    changes: list[dict[str, object]] = []
    for before, after in zip(v4.regions, v5.regions, strict=True):
        assert before.display_path is not None and after.display_path is not None
        if before.id not in _V5_PATH_OVERRIDES:
            continue
        before_coordinates = np.asarray(before.display_path.coordinates)
        after_coordinates = np.asarray(after.display_path.coordinates)
        delta = after_coordinates - before_coordinates
        changes.append(
            {
                "id": before.id,
                "v4DisplayPath": before.display_path.data,
                "v5DisplayPath": after.display_path.data,
                "v4Coordinates": before_coordinates.tolist(),
                "v5Coordinates": after_coordinates.tolist(),
                "meanShiftPx": {"x": float(delta[:, 0].mean()), "y": float(delta[:, 1].mean())},
                "maxAbsoluteShiftPx": {"x": float(np.abs(delta[:, 0]).max()), "y": float(np.abs(delta[:, 1]).max())},
                "v4LocalEdgeDistancePx": _path_edge_distance(before.display_path, edge_distance),
                "v5LocalEdgeDistancePx": _path_edge_distance(after.display_path, edge_distance),
            }
        )
    by_id = {region.id: region for region in v5.regions}
    def bounds(region_id: str) -> tuple[float, float, float, float]:
        path = by_id[region_id].display_path
        assert path is not None
        points = np.asarray(path.coordinates)
        return (float(points[:, 0].min()), float(points[:, 1].min()), float(points[:, 0].max()), float(points[:, 1].max()))
    center, left, right = bounds("pocket-middle-center"), bounds("pocket-middle-inner-left"), bounds("pocket-middle-inner-right")
    return {
        "method": "explicit deterministic review paths fitted to Stage 1 inner cavity mouths; Canny distance is diagnostic only",
        "changedIdsFromV4": sorted(_V5_PATH_OVERRIDES),
        "unchangedPathCountFromV4": sum(
            before.display_path.data == after.display_path.data
            for before, after in zip(v4.regions, v5.regions, strict=True)
        ),
        "regions": changes,
        "innerPairGapToCenterPx": {
            "left": center[0] - left[2],
            "right": right[0] - center[2],
            "difference": abs((center[0] - left[2]) - (right[0] - center[2])),
        },
        **topology,
    }


def _routed_edge_distance(rgba: np.ndarray) -> np.ndarray:
    grayscale = cv2.cvtColor(rgba[..., :3], cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(grayscale, 20, 60) > 0
    edges &= rgba[..., 3] > 200
    return cv2.distanceTransform((~edges).astype(np.uint8), cv2.DIST_L2, 5)


def _path_edge_distance(path: DisplayPath, edge_distance: np.ndarray) -> float:
    contour = np.rint(flatten_display_path(path, curve_steps=64)).astype(np.int32)
    contour[:, 0] = np.clip(contour[:, 0], 0, edge_distance.shape[1] - 1)
    contour[:, 1] = np.clip(contour[:, 1], 0, edge_distance.shape[0] - 1)
    return float(edge_distance[contour[:, 1], contour[:, 0]].mean())


def _geometry_delta(
    rgba: np.ndarray, original: ProductTemplate, candidate: ProductTemplate
) -> np.ndarray:
    canvas = Image.new("RGB", (1510, 330), _BACKGROUND)
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()
    draw.text((24, 16), "Stage 2 — v2 / v3 geometry delta: orange = v2, cyan = v3", fill=(34, 34, 34), font=font)
    draw.text((24, 294), "Only regions 06 and 07 move: both are lifted one canonical pixel; all other 20 paths overlap exactly.", fill=(68, 68, 68), font=font)
    for panel, region_id, source_x in ((0, "pocket-top-outer-left", 20), (1, "pocket-top-outer-right", 810)):
        crop = rgba[63:114, source_x:source_x + 190]
        enlarged = Image.fromarray(crop, mode="RGBA").resize((760, 204), Image.Resampling.LANCZOS)
        x = 24 + panel * 760
        canvas.paste(enlarged, (x, 64), enlarged)
        for template, color, width in ((original, (255, 125, 25, 235), 5), (candidate, (0, 190, 220, 235), 3)):
            path = next(region.display_path for region in template.regions if region.id == region_id)
            assert path is not None
            contour = flatten_display_path(path)
            points = [((float(px) - source_x) * 4 + x, (float(py) - 63) * 4 + 64) for px, py in contour]
            draw.line(points, fill=color, width=width, joint="curve")
        draw.text((x, 42), region_id, fill=(34, 34, 34), font=font)
        draw.rectangle((x, 64, x + 760, 268), outline=(125, 125, 125, 170), width=1)
    return np.asarray(canvas)


def _four_region_closeups(
    rgba: np.ndarray, old: ProductTemplate, new: ProductTemplate, *, include_old: bool
) -> np.ndarray:
    panels = (
        ("pocket-top-outer-left", 20, 45, 190, 72),
        ("pocket-top-outer-right", 790, 45, 190, 72),
        ("pocket-middle-inner-left", 275, 112, 170, 62),
        ("pocket-middle-inner-right", 555, 112, 170, 62),
    )
    scale = 3
    canvas = Image.new("RGB", (1210, 590), _BACKGROUND)
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()
    title = "Stage 2 — v3 / v4 geometry delta: orange = v3, cyan = v4" if include_old else "Stage 2 — v4 cavity-mouth fit: cyan = candidate path on un-tinted pixels"
    draw.text((20, 16), title, fill=(34, 34, 34), font=font)
    for index, (region_id, crop_x, crop_y, width, height) in enumerate(panels):
        column = index % 2
        row = index // 2
        x = 20 + column * 590
        y = 54 + row * 265
        crop = rgba[crop_y:crop_y + height, crop_x:crop_x + width]
        enlarged = Image.fromarray(crop, mode="RGBA").resize((width * scale, height * scale), Image.Resampling.LANCZOS)
        canvas.paste(enlarged, (x, y), enlarged)
        if include_old:
            _draw_closeup_path(draw, old, region_id, crop_x, crop_y, x, y, scale, (255, 125, 25, 235), 5)
        _draw_closeup_path(draw, new, region_id, crop_x, crop_y, x, y, scale, (0, 190, 220, 245), 3)
        draw.rectangle((x, y, x + width * scale, y + height * scale), outline=(125, 125, 125, 170), width=1)
        draw.text((x, y - 16), region_id, fill=(34, 34, 34), font=font)
    return np.asarray(canvas)


def _draw_closeup_path(
    draw: ImageDraw.ImageDraw,
    template: ProductTemplate,
    region_id: str,
    crop_x: int,
    crop_y: int,
    target_x: int,
    target_y: int,
    scale: int,
    color: tuple[int, int, int, int],
    width: int,
) -> None:
    path = next(region.display_path for region in template.regions if region.id == region_id)
    assert path is not None
    contour = flatten_display_path(path)
    points = [((float(px) - crop_x) * scale + target_x, (float(py) - crop_y) * scale + target_y) for px, py in contour]
    draw.line(points, fill=color, width=width, joint="curve")


def _inner_pair_closeups(
    rgba: np.ndarray, old: ProductTemplate, new: ProductTemplate, *, include_old: bool
) -> np.ndarray:
    panels = (
        ("pocket-middle-inner-left", 265, 108, 315, 70),
        ("pocket-middle-inner-right", 420, 108, 315, 70),
    )
    scale = 3
    canvas = Image.new("RGB", (1900, 330), _BACKGROUND)
    draw = ImageDraw.Draw(canvas, "RGBA")
    font = ImageFont.load_default()
    title = "Stage 2 — v4 / v5 inner-pair delta: orange = v4, cyan = v5" if include_old else "Stage 2 — v5 inner-pair cavity-mouth fit: cyan = candidate path on un-tinted pixels"
    draw.text((20, 16), title, fill=(34, 34, 34), font=font)
    for index, (region_id, crop_x, crop_y, width, height) in enumerate(panels):
        x = 20 + index * 950
        y = 54
        crop = rgba[crop_y:crop_y + height, crop_x:crop_x + width]
        enlarged = Image.fromarray(crop, mode="RGBA").resize((width * scale, height * scale), Image.Resampling.LANCZOS)
        canvas.paste(enlarged, (x, y), enlarged)
        if include_old:
            _draw_closeup_path(draw, old, region_id, crop_x, crop_y, x, y, scale, (255, 125, 25, 235), 5)
        _draw_closeup_path(draw, new, region_id, crop_x, crop_y, x, y, scale, (0, 190, 220, 245), 3)
        draw.rectangle((x, y, x + width * scale, y + height * scale), outline=(125, 125, 125, 170), width=1)
        draw.text((x, y - 16), region_id, fill=(34, 34, 34), font=font)
    return np.asarray(canvas)


def _side_by_side(automated: np.ndarray, manual: np.ndarray) -> np.ndarray:
    if automated.shape != manual.shape:
        raise ValueError("automated and manual review canvases must have equal dimensions")
    height, width, _ = automated.shape
    canvas = Image.new("RGB", (width * 2 + 72, height + 86), _BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    canvas.paste(Image.fromarray(automated), (24, 54))
    canvas.paste(Image.fromarray(manual), (width + 48, 54))
    draw.text((24, 20), "Stage 1 — automated cleanup", fill=(34, 34, 34), font=font)
    draw.text((width + 48, 20), "Accepted manual cleanup", fill=(34, 34, 34), font=font)
    draw.rectangle((23, 53, width + 24, height + 54), outline=(125, 125, 125), width=1)
    draw.rectangle((width + 47, 53, width * 2 + 48, height + 54), outline=(125, 125, 125), width=1)
    return np.asarray(canvas)


def _difference_heatmap(automated: np.ndarray, manual: np.ndarray) -> np.ndarray:
    difference = np.max(
        np.abs(automated.astype(np.int16) - manual.astype(np.int16)), axis=2
    ).astype(np.uint8)
    amplified = np.clip(difference.astype(np.uint16) * 16, 0, 255).astype(np.uint8)
    heat = cv2.applyColorMap(amplified, cv2.COLORMAP_TURBO)
    heat = cv2.cvtColor(heat, cv2.COLOR_BGR2RGB)
    heat[amplified == 0] = (0, 0, 0)
    image = Image.new("RGB", (1040, 323), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    image.paste(Image.fromarray(heat), (20, 44))
    draw.text((20, 18), "Stage 1 — amplified absolute RGBA difference (16×; black means exact)", fill=(34, 34, 34), font=font)
    draw.rectangle((19, 43, 1020, 303), outline=(125, 125, 125), width=1)
    return np.asarray(image)


def _region_colors(count: int) -> tuple[tuple[int, int, int], ...]:
    colors: list[tuple[int, int, int]] = []
    for index in range(count):
        hue = int((index * 179) / count)
        hsv = np.array([[[hue, 185, 230]]], dtype=np.uint8)
        colors.append(tuple(int(value) for value in cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)[0, 0]))
    return tuple(colors)


def _badge(draw: ImageDraw.ImageDraw, center: tuple[float, float], label: str, color: tuple[int, int, int], font: ImageFont.ImageFont) -> None:
    left = int(round(center[0] - 7))
    top = int(round(center[1] - 7))
    draw.ellipse((left, top, left + 14, top + 14), fill=(*color, 255), outline=(255, 255, 255, 240), width=1)
    draw.text((left + 4, top + 3), label, fill=(20, 20, 20), font=font)


def _package_asset_path(template: ProductTemplate) -> Path:
    if template.render_asset is None:
        raise ValueError("Beastmaker replay requires a packaged render asset")
    return Path(__file__).with_name("products") / template.render_asset


def _package_template_path(template: ProductTemplate) -> Path:
    return Path(__file__).with_name("products") / f"{template.product_id}.json"


def _is_golden_root(root: Path) -> bool:
    required = (
        "source.jpg",
        "photo-proof-fix1-v3.png",
        "photo-proof-fix1-v3-review.png",
        "product-render-proof-task4.svg",
        "product-render-proof-task4.json",
        "product-render-proof-task4-normal.png",
        "product-render-proof-task4-highlight-jugs.png",
        "product-render-proof-task4-highlight-slopers.png",
        "product-render-proof-task4-highlight-symmetric-pockets.png",
        "product-render-proof-task4-highlight-mixed-grips.png",
    )
    return root.is_dir() and all((root / name).is_file() for name in required)


def _load_rgba(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        if image.mode != "RGBA":
            raise ValueError(f"expected RGBA golden: {path}")
        return np.asarray(image).copy()


def _load_rgb(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        return np.asarray(image.convert("RGB")).copy()


def _save_png(path: Path, pixels: np.ndarray) -> None:
    Image.fromarray(pixels).save(path, format="PNG", optimize=False, compress_level=9)


def _write_reproduced_png(
    path: Path, pixels: np.ndarray, accepted_path: Path, *, mode: str
) -> bool:
    """Reuse accepted deterministic PNG bytes only after pixel equality proves them valid."""
    with Image.open(accepted_path) as image:
        if image.mode != mode:
            raise ValueError(f"expected {mode} accepted PNG: {accepted_path}")
        accepted_pixels = np.asarray(image).copy()
    if np.array_equal(pixels, accepted_pixels):
        shutil.copyfile(accepted_path, path)
        return True
    _save_png(path, pixels)
    return False


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _array_sha256(array: np.ndarray) -> str:
    return sha256(array.tobytes()).hexdigest()


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _transparent_rgb_is_zero(rgba: np.ndarray) -> bool:
    transparent = rgba[..., 3] == 0
    return bool(np.all(rgba[..., :3][transparent] == 0))


def _require_same_shape(first: np.ndarray, second: np.ndarray, description: str) -> None:
    if first.shape != second.shape:
        raise ValueError(f"{description} shapes differ: {first.shape} != {second.shape}")
