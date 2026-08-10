#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path


def load_board_catalog_module(repo_root: Path):
    module_path = (
        repo_root
        / "Tools"
        / "HangboardOnboarding"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    spec = importlib.util.spec_from_file_location("board_catalog_export", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load board catalog module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the checked-in Swift board catalog.")
    parser.add_argument("--check", action="store_true", help="fail if the generated Swift is stale")
    parser.add_argument("--catalog", type=Path, help="catalog JSON to export")
    parser.add_argument("--output", type=Path, help="Swift output path")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    module = load_board_catalog_module(repo_root)
    catalog_path = args.catalog or repo_root / "Hangboards" / "catalog.json"
    output_path = args.output or repo_root / "HangTen" / "Models" / "GeneratedBoardCatalog.swift"

    try:
        module.export_swift_catalog(catalog_path, output_path, check=args.check)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
