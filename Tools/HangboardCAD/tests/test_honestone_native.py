"""Native Honestone geometry regression, requiring the installed FreeCAD CLI."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[3]
FREECAD = Path(os.environ.get("HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"))


@pytest.mark.skipif(not FREECAD.is_file(), reason="FreeCAD is unavailable")
def test_honestone_recomputes_and_persists_physical_depth_edit():
    owner = Path(os.environ.get("PASEO_WORKTREE_PATH", str(ROOT))).name
    context = ROOT / ".context" / f"{owner}-honestone-native-tests"
    context.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-check-", dir=context) as scratch:
        environment = dict(os.environ, TMPDIR=scratch)
        result = subprocess.run(
            [sys.executable, str(ROOT / "Tools/HangboardCAD/run_freecad.py"),
             "--freecad", str(FREECAD),
             str(ROOT / "Tools/HangboardCAD/tests/honestone_native_source_checks.py"),
             str(ROOT / "Hangboards/tension-honestone.FCStd"), scratch],
            cwd=ROOT, env=environment, capture_output=True, text=True, timeout=300,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all Honestone native source checks passed" in result.stdout
