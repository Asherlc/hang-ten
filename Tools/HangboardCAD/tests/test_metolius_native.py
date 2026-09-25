"""Genuine native metolius-rock-rings-3d checks, run through FreeCAD.

These are skipped, not silently passed, when the pinned FreeCAD toolchain is not
present on the machine.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
TOOLS = REPOSITORY / "Tools" / "HangboardCAD"
FREECAD = Path("/Applications/FreeCAD.app/Contents/Resources")
FREECAD_CMD = FREECAD / "bin" / "freecadcmd"
EXTRA_PATH = os.environ.get("HANGTEN_CAD_PYTHONPATH")
PACKAGE = "metolius-rock-rings-3d"
SOURCE = REPOSITORY / "Hangboards" / PACKAGE / f"{PACKAGE}.FCStd"
ASSET = REPOSITORY / "Hangboards" / PACKAGE / "assets" / "primary.usdz"

requires_freecad = pytest.mark.skipif(
    not FREECAD_CMD.is_file() or not EXTRA_PATH,
    reason="pinned FreeCAD toolchain or HANGTEN_CAD_PYTHONPATH is unavailable",
)


def run_under_freecad(script: Path, *arguments: str, wrapper_dir: Path | None = None):
    import tempfile

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
        TOOLS / "tests" / "metolius_native_source_checks.py", str(SOURCE)
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all native source checks passed" in result.stdout


@requires_freecad
def test_compiler_check_mode_reports_a_v2_package(tmp_path):
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
    import json

    payload = json.loads(report.read_text())
    assert payload["sourceUnchanged"] is True
    assert payload["published"] is False
    assert payload["schemaVersion"] == 2
    assert sorted(payload["contacts"]) == ["jug", "pocket-25", "pocket-32", "pocket-40"]
    assert payload["nodes"] == [
        "lateral_window_001",
        "ring_body_001",
        "roof_exit_001",
        "unit_jug_001",
        "unit_pocket_25_001",
        "unit_pocket_32_001",
        "unit_pocket_40_001",
    ]
    assert payload["measuredRegionDepthsMM"]["pocket-40"] == 40.0
    assert payload["measuredRegionDepthsMM"]["pocket-32"] == 32.0
    assert payload["measuredRegionDepthsMM"]["pocket-25"] == 25.0


# NOTE: there is deliberately no committed compare_exports guard for this board.
# The vector source fits the reference's measured stations to 0.012 mm, but it
# deliberately differs elsewhere. The pockets are lofted smoothly between
# stations (up to 0.9 mm from the reference's facets), and the jug is the
# photographed crown hump rather than the reference's scoop (up to 21 mm). The
# comparison is run manually and reported; see
# docs/source-audits/2026-09-25-metolius-rock-rings-3d-vector-provenance.md.
