"""Exercise native library provisioning after the validated cache decision."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("cache_hit", [True, False])
def test_native_library_setup_follows_validated_cache_result(tmp_path, cache_hit):
    workspace = tmp_path / "mad-tiger-ci-dependency-fixture"
    (workspace / "Tools/HangboardCAD").mkdir(parents=True)
    (workspace / "scripts").mkdir()
    probe = workspace / "Tools/HangboardCAD/prepare_assets.py"
    probe.write_text(
        "import os,sys\nfrom pathlib import Path\n"
        "assert '--cache-only' in sys.argv\n"
        "with Path(os.environ['HANGTEN_TEST_SETUP_EVENTS']).open('a') as events:\n"
        "    events.write('validated cache probe\\n')\n"
        f"raise SystemExit({0 if cache_hit else 1})\n"
    )
    events = workspace / "setup-events.txt"
    binaries = workspace / "binaries"
    binaries.mkdir()
    sudo = binaries / "sudo"
    sudo.write_text(
        "#!/usr/bin/env bash\n"
        "printf 'sudo %s\\n' \"$*\" >> \"$HANGTEN_TEST_SETUP_EVENTS\"\n"
    )
    sudo.chmod(0o755)
    source = ROOT / "scripts/install-cad-ci-dependencies.sh"
    command = workspace / "scripts/install-cad-ci-dependencies.sh"
    command.write_bytes(source.read_bytes())
    environment = dict(os.environ, PATH=f"{binaries}{os.pathsep}{os.environ['PATH']}",
                       HANGTEN_TEST_SETUP_EVENTS=str(events), HANGBOARD_PYTHON=sys.executable,
                       PASEO_WORKTREE_PATH=str(workspace))
    result = subprocess.run(["bash", str(command), "0", "8", str(workspace / ".context/board-cache")],
                            cwd=workspace, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    recorded = events.read_text().splitlines()
    assert recorded[0] == "validated cache probe"
    assert len([event for event in recorded if event.startswith("sudo ")]) == (0 if cache_hit else 2)
    assert not list((workspace / ".context").glob("*-cad-ci-setup.*"))
