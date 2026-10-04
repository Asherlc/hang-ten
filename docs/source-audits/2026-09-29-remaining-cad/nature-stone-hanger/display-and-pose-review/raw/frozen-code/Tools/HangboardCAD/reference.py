"""Resolve the pre-migration reference asset from Git.

The reference is a runtime asset that the compiler overwrites, so it must be
read from Git at the recorded pre-migration commit rather than from the live
runtime path or from a copied file left lying around. Nothing here is a build
input: the compiler never calls this module.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

# Merge base of the migration branch with its parent: the last commit before
# this migration replaced any published bytes.
REFERENCE_COMMIT = "6b828e156d4e14ec4a8aa0e3b8f17212336be7bc"
REFERENCE_SUFFIXES = ("primary.usdz", "primary.model.json")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _stored(commit: str, path: str, root: Path) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout


def load_reference(package: str, suffix: str, scratch: Path, commit: str = REFERENCE_COMMIT) -> tuple[Path, str]:
    """Materialise one reference file from Git and return its path and SHA-256.

    The reference assets are Git LFS tracked, so the stored blob is a pointer;
    the smudge filter resolves it and the resolved bytes are checked against the
    object id the pointer declares.
    """
    if suffix not in REFERENCE_SUFFIXES:
        raise ValueError(f"unsupported reference suffix: {suffix}")
    root = repository_root()
    relative = f"Hangboards/{package}/assets/{suffix}"
    override = os.environ.get("HANGTEN_REFERENCE_DIR")
    if override:
        path = Path(override) / suffix
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    stored = _stored(commit, relative, root)
    resolved = subprocess.run(
        ["git", "lfs", "smudge"], input=stored, capture_output=True, check=True
    ).stdout
    if resolved.startswith(b"version https://git-lfs.github.com/spec/v1"):
        raise ValueError("Git LFS smudge did not resolve the reference object")
    declared = None
    for line in stored.decode("utf-8", "replace").splitlines():
        if line.startswith("oid sha256:"):
            declared = line.split(":", 1)[1].strip()
    digest = hashlib.sha256(resolved).hexdigest()
    if declared is not None and declared != digest:
        raise ValueError("resolved reference does not match its Git LFS object id")

    scratch.mkdir(parents=True, exist_ok=True)
    path = scratch / f"{package}-{suffix}"
    path.write_bytes(resolved)
    return path, digest
