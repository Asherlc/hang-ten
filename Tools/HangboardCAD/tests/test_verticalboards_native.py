"""Native regression checks for the three manufacturer-authored YY VerticalBoards.

Use the pinned FreeCAD interpreter, never cached B-rep data under host Python.
Every edit and wrapper is isolated in workspace-owned scratch and removed after
its test. No runtime assets are rebuilt by this module.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name("verticalboards_native_source_checks.py")
FREECAD_CMD = Path(os.environ.get(
    "HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
))
EXTRA_PATH = os.environ.get("HANGTEN_CAD_PYTHONPATH", "")
PXR_AVAILABLE = any(
    (Path(directory) / "pxr" / "__init__.py").is_file()
    for directory in EXTRA_PATH.split(os.pathsep) if directory
)

requires_native_toolchain = pytest.mark.skipif(
    not FREECAD_CMD.is_file() or not PXR_AVAILABLE,
    reason="pinned FreeCAD or pxr in HANGTEN_CAD_PYTHONPATH is unavailable",
)


@requires_native_toolchain
@pytest.mark.parametrize("slug", [
    "yy-verticalboard-first",
    "yy-verticalboard-light",
    "yy-verticalboard-one",
])
def test_verticalboard_native_source_and_persisted_edit(slug):
    """Run native recompute and persisted depth-edit checks in disposable workspace-owned scratch."""
    source = REPOSITORY / "Hangboards" / f"{slug}.FCStd"
    context = REPOSITORY / ".context"
    context.mkdir(exist_ok=True)
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
    with tempfile.TemporaryDirectory(prefix=f"{owner}-verticalboards-", dir=context) as temp:
        scratch = Path(temp)
        environment = dict(os.environ)
        environment["HANGTEN_CAD_PYTHONPATH"] = EXTRA_PATH
        environment["TMPDIR"] = str(scratch)
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "Tools/HangboardCAD/run_freecad.py"),
             "--freecad", str(FREECAD_CMD), str(SCRIPT), str(source), str(scratch)],
            cwd=REPOSITORY,
            env=environment,
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert f"all {slug} native source checks passed" in result.stdout
    # Verify the exact workspace-owned directory was deleted after all subprocess
    # outputs (including saved edit files) were cleaned by TemporaryDirectory.
    assert not scratch.exists(), "workspace-owned native-check scratch was not removed"
