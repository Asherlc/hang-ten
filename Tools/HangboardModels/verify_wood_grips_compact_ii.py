#!/usr/bin/env python3
"""Verify the compiler-produced Metolius Wood Grips Compact II package.

Compact II has no reviewed source render rig. This adapter delegates package,
reimport, descriptor, material, and topology checks to the shared verifier.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from model_verification import (  # noqa: E402
    MaterialPolicy, ModelVerificationConfig, VerificationReport,
    verify_model_package,
)

ROOT = Path(__file__).resolve().parents[2]
BOARD_JSON = ROOT / "Hangboards/metolius-wood-grips-compact-ii/board.json"
TRIANGLE_CEILING = 150_000
PACKAGE_ASSETS = frozenset({"assets/primary.usdz", "assets/primary.model.json"})


def compact_ii_config(board_json: Path | None = None) -> ModelVerificationConfig:
    """Return the fixed shared-verifier configuration for Compact II."""
    board = Path(board_json or BOARD_JSON)
    document = json.loads(board.read_text(encoding="utf-8"))
    ids = tuple(item["id"] for item in document["holds"])
    if len(ids) != 19 or len(set(ids)) != 19:
        raise ValueError("Compact II logical inventory must contain exactly 19 hold IDs")
    return ModelVerificationConfig(
        board_id="metolius-wood-grips-compact-ii", board_json=board,
        package_relative_assets=PACKAGE_ASSETS, expected_hold_ids=ids,
        triangle_ceiling=TRIANGLE_CEILING,
        required_roles=frozenset({"body", "hold"}),
        material_policy=MaterialPolicy.canonical_wood(),
    )


def compact_report(
    core: VerificationReport, *, expected_hold_ids: tuple[str, ...], renders_skipped: bool
) -> dict[str, object]:
    """Flatten the shared report while retaining Compact's durable fields."""
    checks = dict(core.checks)
    ids = tuple(checks["logicalHoldIDs"])
    expected = set(expected_hold_ids)
    if len(expected) != 19 or tuple(expected_hold_ids) != tuple(ids):
        raise ValueError("actual USDZ did not preserve all 19 Compact II hold IDs")
    mesh_count = len(checks["sourcePieceCorrespondence"])
    report = {
        "boardID": core.board_id, **checks,
        "modelSHA256": checks["modelSHA256"], "descriptorSHA256": checks["descriptorSHA256"],
        "assets": sorted(PACKAGE_ASSETS),
        "exactDescriptorForActualUSDZ": True, "explicitTriangles": True,
        "hold_ids_preserved": len(expected & set(ids)), "hardware_mesh_count": 0,
        "triangleCeiling": checks["triangleCeiling"],
        "texturedMeshCount": mesh_count, "reviewViews": [],
        "rendersSkipped": renders_skipped,
    }
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--format", choices=("usdz",), action="append")
    parser.add_argument("--skip-renders", action="store_true")
    raw = argv if argv is not None else (
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
    args = parser.parse_args(raw)
    if args.format not in (None, ["usdz"]):
        raise ValueError("only the compiler-produced USDZ format is supported")
    if not args.skip_renders:
        raise ValueError("Compact actual-export rendering awaits a reviewed source rig; use --skip-renders")
    package = args.output.resolve()
    config = compact_ii_config()
    core = verify_model_package(package, config, render=False)
    report = compact_report(core, expected_hold_ids=config.expected_hold_ids, renders_skipped=True)
    report_path = package.parent / "export-verification.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("COMPACT_EXPORT_VERIFIED", json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
