"""Offline semantic and artwork parity report for a canonical board package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from hashlib import sha256
import json
from pathlib import Path

import numpy as np

from .board_catalog import load_board_package
from .workspace_paths import default_workspace_root, resolve_workspace_path


HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS = 32
HIGHLIGHT_PIXEL_DIFF_SENTINEL = -1


def build_metolius_benchmark_report(
    package_root: Path,
    output_path: Path,
    *,
    workspace_root: Path,
    cache_root: Path | None = None,
) -> dict[str, object]:
    """Validate canonical semantic/artwork parity and write a stable report."""
    del cache_root
    package = load_board_package(Path(package_root))
    owned_root = Path(workspace_root).resolve(strict=False)
    output = resolve_workspace_path(Path(output_path), owned_root)
    output.parent.mkdir(parents=True, exist_ok=True)

    hold_ids = {hold.id for hold in package.board.holds}
    semantic_ids = {
        hold_id
        for targets in package.semantics.semantic_holds.values()
        for hold_id in targets
    }
    artwork_ids = {piece.hold_id for piece in package.artwork.hold_pieces}
    semantic_exact = semantic_ids == hold_ids
    artwork_exact = artwork_ids == hold_ids
    report: dict[str, object] = {
        "boardId": package.board.id,
        "packageSha256": _package_hash(package.root),
        "parity": {
            "exact": semantic_exact and artwork_exact,
            "semantics": {
                "exact": semantic_exact,
                "missingHoldIds": sorted(hold_ids - semantic_ids),
                "unknownHoldIds": sorted(semantic_ids - hold_ids),
            },
            "artwork": {
                "exact": artwork_exact,
                "missingHoldIds": sorted(hold_ids - artwork_ids),
                "unknownHoldIds": sorted(artwork_ids - hold_ids),
            },
        },
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _package_hash(root: Path) -> str:
    digest = sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = path.relative_to(root).as_posix().encode()
            digest.update(relative)
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _highlight_pixels_equivalent(
    accepted_pixels: np.ndarray, replayed_pixels: np.ndarray
) -> bool:
    metrics = _highlight_pixel_diff_metrics(accepted_pixels, replayed_pixels)
    return (
        metrics["differingPixelCount"] != HIGHLIGHT_PIXEL_DIFF_SENTINEL
        and metrics["differingPixelCount"]
        <= HIGHLIGHT_PIXEL_EQUIVALENCE_MAX_CHANGED_PIXELS
        and metrics["maxAbsChannelDifference"] <= 1
    )


def _highlight_pixel_diff_metrics(
    accepted_pixels: np.ndarray, replayed_pixels: np.ndarray
) -> dict[str, int]:
    if (
        accepted_pixels.shape != replayed_pixels.shape
        or accepted_pixels.ndim != 3
        or accepted_pixels.shape[-1] != 4
    ):
        return {
            "differingPixelCount": HIGHLIGHT_PIXEL_DIFF_SENTINEL,
            "maxAbsChannelDifference": HIGHLIGHT_PIXEL_DIFF_SENTINEL,
        }
    differences = np.abs(
        accepted_pixels.astype(np.int16) - replayed_pixels.astype(np.int16)
    )
    return {
        "differingPixelCount": int(np.any(differences != 0, axis=-1).sum()),
        "maxAbsChannelDifference": int(differences.max(initial=0)),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate canonical hangboard semantic and artwork parity",
    )
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=default_workspace_root(),
        help="owned root for generated artifacts",
    )
    arguments = parser.parse_args(argv)
    report = build_metolius_benchmark_report(
        arguments.package,
        arguments.output,
        workspace_root=arguments.workspace_root,
    )
    if not report["parity"]["exact"]:
        raise SystemExit(
            "canonical package parity failed: "
            + json.dumps(report["parity"], sort_keys=True, separators=(",", ":"))
        )
    print(arguments.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
