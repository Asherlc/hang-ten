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

# Keep the historical command-line surface importable by report-only tests.
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("output", nargs="?", type=Path,
                    default=ROOT / ".context" / f"{ROOT.name}-wood-grips-compact-ii")
parser.add_argument("--format", choices=("usdz",), action="append")
parser.add_argument("--skip-renders", action="store_true")
args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


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


def package_paths(package: Path) -> tuple[Path, Path]:
    """Return the two compiler-owned package assets after exact inventory check."""
    root = Path(package).resolve()
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"package directory must be a regular directory: {root}")
    expected_assets = {"assets/primary.usdz", "assets/primary.model.json"}
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and not p.is_symlink()}
    if actual != expected_assets:
        raise ValueError(f"compiler package assets must equal {sorted(expected_assets)}")
    return root / "assets/primary.usdz", root / "assets/primary.model.json"


def compact_report(core: VerificationReport, *, renders_skipped: bool) -> dict[str, object]:
    """Flatten the shared report while retaining Compact's durable fields."""
    checks = dict(core.checks)
    ids = checks["logicalHoldIDs"]
    expected = set(ids)
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
    if report["hold_ids_preserved"] != 19:
        raise ValueError("actual USDZ did not preserve all 19 Compact II hold IDs")
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
    package_paths(package)
    core = verify_model_package(package, compact_ii_config(), render=False)
    report = compact_report(core, renders_skipped=True)
    report_path = package.parent / "export-verification.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("COMPACT_EXPORT_VERIFIED", json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
