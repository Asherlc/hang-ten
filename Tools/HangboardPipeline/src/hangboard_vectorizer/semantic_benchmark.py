"""Offline semantic parity report for a canonical board package."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from hashlib import sha256
import json
from pathlib import Path

from .board_catalog import load_board_package
from .workspace_paths import default_workspace_root, resolve_workspace_path


def build_metolius_benchmark_report(
    package_root: Path,
    output_path: Path,
    *,
    workspace_root: Path,
    cache_root: Path | None = None,
) -> dict[str, object]:
    """Validate canonical semantic parity and write a stable report."""
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
    semantic_exact = semantic_ids == hold_ids
    report: dict[str, object] = {
        "boardId": package.board.id,
        "packageSha256": _package_hash(package.root),
        "parity": {
            "exact": semantic_exact,
            "semantics": {
                "exact": semantic_exact,
                "missingHoldIds": sorted(hold_ids - semantic_ids),
                "unknownHoldIds": sorted(semantic_ids - hold_ids),
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate canonical hangboard semantic parity",
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
