"""Exercise opt-in normals against actual native FreeCAD surfaces."""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[3]
FREECAD = Path(os.environ.get(
    "HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd",
))


@pytest.mark.skipif(
    not FREECAD.is_file() or not os.environ.get("HANGTEN_CAD_PYTHONPATH"),
    reason="native FreeCAD/OpenUSD toolchain unavailable",
)
def test_native_uv_node_normals():
    context = ROOT / ".context" / ROOT.name
    context.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="uv-normal-tests-", dir=context) as temp:
        env = dict(os.environ, TMPDIR=temp, XDG_CACHE_HOME=temp)
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "Tools/HangboardCAD/run_freecad.py"),
             "--freecad", str(FREECAD), "--extra-python-path", env["HANGTEN_CAD_PYTHONPATH"],
             str(Path(__file__).with_name("uv_node_normal_checks.py"))],
            cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=120)
        finally:
            # The wrapper could exit before its child. Always clean this
            # exact owned group before deleting its scratch directory.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    assert process.returncode == 0, stdout + stderr
