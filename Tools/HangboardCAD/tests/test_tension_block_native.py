"""Reopen the retained Block source and exercise its live contact bindings."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pytest


REPOSITORY = Path(__file__).resolve().parents[3]
TOOLS = REPOSITORY / "Tools/HangboardCAD"
SOURCE = REPOSITORY / "Hangboards/tension-block.FCStd"
FREECAD = Path(os.environ.get(
    "HANGTEN_FREECAD_CMD",
    "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
))


@pytest.mark.skipif(
    not FREECAD.is_file()
    and os.environ.get("HANGTEN_REQUIRE_NATIVE_CAD", "").lower() != "true",
    reason="native FreeCAD unavailable outside the required native lane",
)
def test_recess_edits_update_the_solid_and_bound_contact_faces():
    """A saved face copy must not survive as stale geometry after a depth edit."""
    workspace = Path(os.environ.get("PASEO_WORKTREE_PATH", str(REPOSITORY))).resolve()
    scratch_root = workspace / ".context"
    scratch_root.mkdir(parents=True, exist_ok=True)
    source_digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    with tempfile.TemporaryDirectory(
        prefix=f"{workspace.name}-tension-block-native-", dir=scratch_root,
    ) as directory:
        scratch = Path(directory)
        (scratch / "owner").write_text(workspace.name + "\n")
        copied_source = scratch / SOURCE.name
        report = scratch / "native-check-result.json"
        shutil.copyfile(SOURCE, copied_source)
        environment = dict(os.environ, TMPDIR=str(scratch))
        result = subprocess.run(
            [sys.executable, str(TOOLS / "run_freecad.py"), "--freecad", str(FREECAD),
             str(TOOLS / "tests/tension_block_native_source_checks.py"),
             str(copied_source), str(report)],
            cwd=REPOSITORY, env=environment, capture_output=True, text=True, timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        # FreeCAD's progress console can consume script stdout on Linux. Require
        # an explicit receipt written only after every native assertion passes.
        assert report.is_file(), result.stdout + result.stderr
        assert json.loads(report.read_text()) == {
            "status": "passed",
            "sourceSHA256": source_digest,
            "editedTools": ["Edge20Tool", "MonoTool"],
        }
        assert hashlib.sha256(copied_source.read_bytes()).hexdigest() == source_digest
    assert not scratch.exists()
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_digest
