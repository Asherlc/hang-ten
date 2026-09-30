"""Physical and persisted-edit regression for the authoritative Evo CAD source."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
FREECAD = Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"))


@pytest.mark.skipif(not FREECAD.is_file(), reason="pinned FreeCAD is unavailable")
def test_evo_native_recompute_and_persisted_pocket_edits():
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).name
    scratch_root = REPOSITORY / ".context" / f"{owner}-evo-tests"
    scratch_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch_root, prefix="native-") as directory:
        environment = dict(os.environ, TMPDIR=directory)
        result = subprocess.run(
            [sys.executable, str(REPOSITORY / "Tools/HangboardCAD/run_freecad.py"),
             "--freecad", str(FREECAD),
             str(REPOSITORY / "Tools/HangboardCAD/tests/yy_evo_native_source_checks.py"), directory],
            cwd=REPOSITORY, env=environment, text=True, capture_output=True, timeout=240,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all Evo native source checks passed" in result.stdout
