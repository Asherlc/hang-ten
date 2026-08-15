from __future__ import annotations

import os
from pathlib import Path
import subprocess


WORKBENCH_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WORKBENCH_ROOT.parents[1]
LAUNCHER = REPOSITORY_ROOT / "scripts" / "run-supported-python.sh"


def _fake_python(path: Path, version: str, supported: bool) -> None:
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"${1:-}\" = '-c' ]; then\n"
        f"  exit {0 if supported else 1}\n"
        "fi\n"
        f"printf '%s|%s\\n' '{version}' \"$*\" > \"$FAKE_PYTHON_LOG\"\n",
        encoding="utf-8",
    )
    path.chmod(0o755)


def test_stage_launcher_uses_the_first_supported_versioned_python(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    execution_log = tmp_path / "execution.log"
    for version, supported in (("3.13", False), ("3.12", False), ("3.11", True), ("3.10", True)):
        _fake_python(fake_bin / f"python{version}", version, supported)
    _fake_python(fake_bin / "python3", "unversioned", False)

    result = subprocess.run(
        [str(LAUNCHER), "stage.py", "--repository-root", "/tmp/repository"],
        env={
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "FAKE_PYTHON_LOG": str(execution_log),
        },
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert execution_log.read_text(encoding="utf-8") == "3.11|stage.py --repository-root /tmp/repository\n"


def test_stage_launcher_explains_when_no_supported_python_is_available(tmp_path: Path) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for version in ("3.13", "3.12", "3.11", "3.10"):
        _fake_python(fake_bin / f"python{version}", version, False)
    _fake_python(fake_bin / "python3", "unversioned", False)

    result = subprocess.run(
        [str(LAUNCHER), "stage.py"],
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Python 3.10 or newer is required to stage direct board packages." in result.stderr
    assert "Set HANGTEN_PYTHON to an explicit supported interpreter." in result.stderr
