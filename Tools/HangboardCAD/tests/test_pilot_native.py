"""Genuine native pilot checks, run through FreeCAD as a subprocess.

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
EXTRA_PATH = REPOSITORY / ".context" / "organic-shark" / "fcpy"
PACKAGE = "lattice-triple-rung"
SOURCE = REPOSITORY / "ModelSources" / f"{PACKAGE}.FCStd"
ASSET = REPOSITORY / "Hangboards" / PACKAGE / "assets" / "primary.usdz"

requires_freecad = pytest.mark.skipif(
    not FREECAD_CMD.is_file(), reason="pinned FreeCAD toolchain is not installed"
)


def run_under_freecad(script: Path, *arguments: str, wrapper_dir: Path | None = None):
    """Run a script under FreeCAD, forwarding its own arguments.

    FreeCAD's launcher consumes unrecognised options before the script ever sees
    them, so the arguments are embedded in a generated wrapper instead.
    """
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
    env["HANGTEN_CAD_PYTHONPATH"] = str(EXTRA_PATH)
    return subprocess.run(
        [str(FREECAD_CMD), str(wrapper)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(REPOSITORY),
    )


@requires_freecad
def test_native_source_checks_pass():
    result = run_under_freecad(TOOLS / "tests" / "native_source_checks.py", str(SOURCE))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "all native source checks passed" in result.stdout


@requires_freecad
def test_compiler_check_mode_reports_a_consistent_package(tmp_path):
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
    assert payload["schemaVersion"] == 1
    assert sorted(payload["contacts"]) == ["edge-10", "edge-20", "edge-45"]
    assert payload["modelSHA256"] and len(payload["modelSHA256"]) == 64


@pytest.mark.skipif(not ASSET.is_file(), reason="pilot asset is not built")
def test_pilot_asset_matches_the_approved_reference_geometry(tmp_path):
    """Compare against the reference resolved from Git, not a copied artifact."""
    sys.path.insert(0, str(TOOLS))
    import reference as reference_module

    try:
        resolved, digest = reference_module.load_reference(
            PACKAGE, "primary.usdz", tmp_path
        )
    except (subprocess.CalledProcessError, ValueError) as error:
        pytest.skip(f"pre-migration reference is not resolvable from Git: {error}")
    assert len(digest) == 64
    result = subprocess.run(
        [sys.executable, str(TOOLS / "tests" / "compare_exports.py"),
         str(resolved), str(ASSET), "--limit-mm", "0.5"],
        capture_output=True, text=True, cwd=str(REPOSITORY),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "sampled comparison passed" in result.stdout
