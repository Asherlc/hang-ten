"""Native wrapper argument, dependency-path and exit-status contracts."""

from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_freecad


@pytest.fixture
def freecad_launcher(tmp_path):
    launcher = tmp_path / "freecadcmd"
    launcher.write_text(
        f"#!{sys.executable}\n"
        "import os, runpy, sys\n"
        "from pathlib import Path\n"
        "if 'HANGTEN_TEST_WRAPPER_RECORD' in os.environ:\n"
        "    Path(os.environ['HANGTEN_TEST_WRAPPER_RECORD']).write_text(sys.argv[1])\n"
        "runpy.run_path(sys.argv[1], run_name='__main__')\n"
    )
    launcher.chmod(0o755)
    return launcher


def test_cli_uses_the_configured_pinned_freecad(tmp_path, monkeypatch, freecad_launcher):
    monkeypatch.setattr(run_freecad, "DEFAULT_FREECAD", tmp_path / "unconfigured-freecad")
    monkeypatch.setenv("HANGTEN_FREECAD_CMD", str(freecad_launcher))
    script = tmp_path / "script.py"
    script.write_text("raise SystemExit(7)\n")
    assert run_freecad.main([str(script)]) == 7


@pytest.mark.parametrize("body,expected", [
    ("print('native success')\n", 0),
    ("print('native failure')\nraise SystemExit(7)\n", 7),
    ("raise RuntimeError('native failure')\n", 3),
])
def test_native_exit_status_reaches_the_caller(tmp_path, freecad_launcher, body, expected):
    script = tmp_path / "script.py"
    script.write_text(body)
    assert run_freecad.run(script, [], freecad_launcher, "") == expected


def test_script_receives_native_dependencies_and_verbatim_arguments(tmp_path, freecad_launcher, capsys):
    dependencies = tmp_path / "native-dependencies"
    dependencies.mkdir()
    (dependencies / "native_dependency.py").write_text("value = 'pinned dependency'\n")
    script = tmp_path / "script.py"
    script.write_text(
        "import os, sys\n"
        "sys.path[:0] = os.environ['HANGTEN_CAD_PYTHONPATH'].split(os.pathsep)\n"
        "import native_dependency\n"
        "print(native_dependency.value, sys.argv[1:])\n"
    )
    assert run_freecad.run(script, ["--flag", "value", "--other"], freecad_launcher, str(dependencies)) == 0
    assert capsys.readouterr().out == "pinned dependency ['--flag', 'value', '--other']\n"


@pytest.mark.parametrize("temporary_directory", [None, "owned", "outside", "symlink"])
def test_native_wrapper_stays_in_owned_workspace_and_is_deleted(
        tmp_path, monkeypatch, freecad_launcher, temporary_directory):
    workspace = tmp_path / "fixture-workspace"
    workspace.mkdir()
    scratch = workspace / ".context"
    monkeypatch.setenv("PASEO_WORKTREE_PATH", str(workspace))
    monkeypatch.delenv("TMPDIR", raising=False)
    if temporary_directory is not None:
        if temporary_directory == "owned":
            scratch = workspace / ".context/explicit-temp"
            scratch.mkdir(parents=True)
            override = scratch
        else:
            override = tmp_path / "outside-workspace"
            override.mkdir()
            if temporary_directory == "symlink":
                link = workspace / "external-temp"
                link.symlink_to(override, target_is_directory=True)
                override = link
        monkeypatch.setenv("TMPDIR", str(override))
    record = tmp_path / "wrapper-path"
    monkeypatch.setenv("HANGTEN_TEST_WRAPPER_RECORD", str(record))
    script = tmp_path / "script.py"
    script.write_text("raise SystemExit(7)\n")
    assert run_freecad.run(script, [], freecad_launcher, "") == 7
    wrapper = Path(record.read_text())
    assert wrapper.parent.parent == scratch
    assert wrapper.parent.name.startswith("fixture-workspace-freecad-")
    assert not wrapper.parent.exists()


@pytest.mark.parametrize("require_native", [False, True])
def test_missing_native_toolchain_respects_ci_lane(tmp_path, require_native):
    """Host CI may skip native work; its dedicated regression lane must fail."""
    root = Path(__file__).resolve().parents[3]
    report = tmp_path / "native-lane.xml"
    environment = dict(os.environ, CI="true", HANGTEN_FREECAD_CMD=str(tmp_path / "missing-freecad"))
    environment.pop("HANGTEN_REQUIRE_NATIVE_CAD", None)
    if require_native:
        environment["HANGTEN_REQUIRE_NATIVE_CAD"] = "true"
    case = root / "Tools/HangboardCAD/tests/test_confirmed_cord_diameter.py"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", f"{case}::test_mini_bar_native_passages_fit_seven_mm_without_changing_board_scale",
         "-q", f"--junitxml={report}"],
        cwd=root, env=environment, capture_output=True, text=True, timeout=30,
    )
    test = next(ET.parse(report).getroot().iter("testcase"))
    assert result.returncode == (1 if require_native else 0), result.stdout + result.stderr
    assert (test.find("skipped") is not None) == (not require_native)
    assert (test.find("failure") is not None) == require_native
