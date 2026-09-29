"""Integration checks for the native Metolius Foundry package."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest


REPOSITORY = Path(__file__).resolve().parents[3]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
FREECAD_CMD = Path(
    os.environ.get(
        "HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
    )
)
EXTRA_PATH = os.environ.get("HANGTEN_CAD_PYTHONPATH")
PACKAGE = "metolius-foundry"
SOURCE = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
ASSET = REPOSITORY / "Hangboards" / PACKAGE / "assets" / "primary.usdz"

requires_freecad = pytest.mark.skipif(
    not FREECAD_CMD.is_file() or not EXTRA_PATH,
    reason="FreeCAD toolchain or HANGTEN_CAD_PYTHONPATH is unavailable",
)


def run_under_freecad(script: Path, *arguments: str):
    context = REPOSITORY / ".context"
    context.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hangten-foundry-fc-", dir=context) as temp:
        wrapper = Path(temp) / "wrap.py"
        wrapper.write_text(
            "import sys, traceback\n"
            f"path = {str(script)!r}\n"
            f"sys.argv = [path] + {list(arguments)!r}\n"
            "try:\n"
            "    exec(compile(open(path).read(), path, 'exec'), "
            "{'__name__': '__main__', '__file__': path})\n"
            "except SystemExit:\n"
            "    raise\n"
            "except BaseException:\n"
            "    traceback.print_exc()\n"
            "    raise SystemExit(3)\n"
            "finally:\n"
            "    sys.stdout.flush()\n"
            "    sys.stderr.flush()\n"
        )
        env = dict(os.environ)
        env["HANGTEN_CAD_PYTHONPATH"] = EXTRA_PATH
        return subprocess.run(
            [str(FREECAD_CMD), str(wrapper)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(REPOSITORY),
        )


@requires_freecad
def test_foundry_native_source_checks_pass():
    result = run_under_freecad(
        TOOLS / "tests" / "foundry_native_source_checks.py", str(SOURCE)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all Foundry native source checks passed" in result.stdout


def test_contact_meshes_exclude_the_inaccessible_mounting_plane():
    import sys

    sys.path.insert(0, str(TOOLS))
    from usdz_writer import read_usdz

    nodes = read_usdz(ASSET)["nodes"]
    for node_id, node in sorted(nodes.items()):
        if node_id == "body_board_001":
            continue
        points = np.asarray(node["points_m"], dtype=float) * 1000.0
        triangles = np.asarray(node["triangles"], dtype=int)
        # USD (x, y, z) maps back to native (x, -z, y), so native Y=0 is USD Z=0.
        rear = np.all(np.abs(points[triangles, 2]) < 1e-6, axis=1)
        assert not rear.any(), f"{node_id} exports {int(rear.sum())} inaccessible rear triangles"
