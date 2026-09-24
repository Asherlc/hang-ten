"""Genuine native metolius-prime-rib checks, run through FreeCAD as a subprocess.

Skipped, not silently passed, when a FreeCAD toolchain is not present. The
pinned macOS build is the default; HANGTEN_FREECAD_CMD points at another
``freecadcmd`` (for example a conda-forge FreeCAD 1.1.3 on Linux).
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
FREECAD_CMD = Path(
    os.environ.get(
        "HANGTEN_FREECAD_CMD", "/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd"
    )
)
EXTRA_PATH = os.environ.get("HANGTEN_CAD_PYTHONPATH")
PACKAGE = "metolius-prime-rib"
SOURCE = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"

requires_freecad = pytest.mark.skipif(
    not FREECAD_CMD.is_file() or not EXTRA_PATH,
    reason="FreeCAD toolchain or HANGTEN_CAD_PYTHONPATH is unavailable",
)


def run_under_freecad(script: Path, *arguments: str, wrapper_dir: Path | None = None):
    directory = wrapper_dir or Path(tempfile.mkdtemp(prefix="hangten-fc-"))
    directory.mkdir(parents=True, exist_ok=True)
    wrapper = directory / "wrap.py"
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
def test_native_source_checks_pass():
    result = run_under_freecad(
        TOOLS / "tests" / "prime_rib_native_source_checks.py", str(SOURCE)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all native source checks passed" in result.stdout


@requires_freecad
def test_compiler_check_mode_partitions_curved_holds(tmp_path):
    report = tmp_path / "report.json"
    result = run_under_freecad(
        TOOLS / "compile_board.py",
        "--package",
        PACKAGE,
        "--check",
        "--report",
        str(report),
        wrapper_dir=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(report.read_text())
    assert payload["sourceUnchanged"] is True
    assert payload["published"] is False
    assert payload["schemaVersion"] == 1
    assert payload["nodes"] == [
        "body_mesh_001",
        "edge_15_mesh_001",
        "edge_23_mesh_001",
        "edge_38_mesh_001",
    ]
    assert payload["measuredRegionDepthsMM"] == {
        "edge-15": 15.0,
        "edge-23": 23.0,
        "edge-38": 38.1,
    }


@requires_freecad
def test_body_does_not_duplicate_curved_hold_surfaces(tmp_path):
    """HangTenCurvedRegionPartition must hand every curved hold triangle to its region.

    Without it the centroid rule leaves chord triangles of the arcs and Beziers in
    the body, which then z-fights with the region's own surface.
    """
    import sys

    import numpy as np

    sys.path.insert(0, str(TOOLS))
    from usdz_writer import read_usdz

    result = run_under_freecad(
        TOOLS / "compile_board.py",
        "--package", PACKAGE,
        "--source", str(SOURCE),
        "--assets", str(tmp_path / "assets"),
        wrapper_dir=tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    nodes = read_usdz(tmp_path / "assets" / "primary.usdz")["nodes"]

    def native(node):
        points = np.asarray(node["points_m"], dtype=float) * 1000.0
        return np.c_[points[:, 0], -points[:, 2], points[:, 1]], np.asarray(node["triangles"])

    body_points, body_triangles = native(nodes["body_mesh_001"])
    centroids = body_points[body_triangles].mean(axis=1)
    middle = np.abs(centroids[:, 0]) < 250.0
    for node_id in ("edge_15_mesh_001", "edge_23_mesh_001", "edge_38_mesh_001"):
        points, _ = native(nodes[node_id])
        low, high = points.min(axis=0), points.max(axis=0)
        inside = (
            middle
            & (centroids[:, 1] >= low[1] - 1e-3) & (centroids[:, 1] <= high[1] + 1e-3)
            & (centroids[:, 2] >= low[2] - 1e-3) & (centroids[:, 2] <= high[2] + 1e-3)
        )
        assert not inside.any(), f"body duplicates {int(inside.sum())} triangles of {node_id}"
