"""Resolve generated artifacts inside an explicitly owned workspace root."""

from __future__ import annotations

import os
from pathlib import Path


def default_workspace_root() -> Path:
    """Return the configured output root, defaulting to the repo-local context area."""
    configured = os.environ.get("HANGBOARD_WORKSPACE_ROOT")
    return Path(configured) if configured else Path(".context/hangboard-onboarding")


def resolve_workspace_path(path: Path, workspace_root: Path) -> Path:
    """Resolve *path* and reject attempts to escape *workspace_root*."""
    root = workspace_root.resolve(strict=False)
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"generated output must stay inside workspace root: {root}") from error
    return resolved
