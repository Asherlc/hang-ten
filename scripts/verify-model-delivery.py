#!/usr/bin/env python3
"""Verify exact committed model bytes before making a download. Never re-export."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

LOCK_PATH = "docs/source-audits/2026-09-22-model-delivery-lock.json"
SUFFIXES = ("assets/primary.model.json", "assets/primary.usdz", "board.json")


def checksum_manifest(root: Path, packages: list[str]) -> str:
    if (not isinstance(packages, list) or not packages
            or any(not isinstance(p, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", p)
                   for p in packages) or len(packages) != len(set(packages))):
        raise ValueError("invalid or duplicate package names")
    root = root.resolve()
    lines = []
    for relative in sorted(f"Hangboards/{p}/{s}" for p in packages for s in SUFFIXES):
        path = root / relative
        if (not path.is_file() or any(p.is_symlink() for p in (path, *path.parents))
                or not path.resolve().is_relative_to(root)):
            raise ValueError(f"expected regular file: {relative}")
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{digest}  {relative}\n")
    return "".join(lines)


def verify(root: Path, lock: dict) -> dict:
    if lock.get("schemaVersion") != 1:
        raise ValueError("unsupported delivery lock")
    packages = lock.get("modelPackages")
    text = checksum_manifest(root, packages)
    expected = {f"Hangboards/{p}/assets/primary.usdz" for p in packages}
    actual = {p.relative_to(root).as_posix()
              for p in (root / "Hangboards").glob("*/assets/*.usdz")}
    if actual != expected:
        raise ValueError("model inventory differs from delivery lock")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != lock.get("sha256Manifest"):
        raise ValueError("model/descriptor/metadata checksum mismatch")
    return {"passed": True, "models": len(packages), "files": len(packages) * 3,
            "sha256Manifest": digest, "assetCommit": lock.get("assetCommit"),
            "scope": "exact-file identity; not native visual or application validation"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    lock = json.loads((args.lock or root / LOCK_PATH).read_text())
    result = verify(root, lock)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
