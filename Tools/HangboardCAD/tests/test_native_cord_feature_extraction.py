"""Exercise cord feature binding against actual native FreeCAD solids."""
import os
import json
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
def test_native_cord_feature_extraction():
    context = ROOT / ".context" / ROOT.name
    context.mkdir(parents=True, exist_ok=True)
    process = None
    temp = None
    ownership = None
    record = {"workspaceOwner": ROOT.name}
    try:
        with tempfile.TemporaryDirectory(prefix=f"{ROOT.name}-cord-feature-tests-", dir=context) as temp:
            env = dict(os.environ, TMPDIR=temp, XDG_CACHE_HOME=temp)
            ownership = context / (Path(temp).name + "-ownership.json")
            record["temporaryDirectory"] = temp
            try:
                process = subprocess.Popen(
                    [sys.executable, str(ROOT / "Tools/HangboardCAD/run_freecad.py"),
                     "--freecad", str(FREECAD), "--extra-python-path", env["HANGTEN_CAD_PYTHONPATH"],
                     str(Path(__file__).with_name("native_cord_feature_checks.py"))],
                    cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    start_new_session=True,
                )
                record["ownedProcessGroup"] = process.pid
                ownership.write_text(json.dumps(record, indent=2) + "\n")
                stdout, stderr = process.communicate(timeout=120)
            finally:
                # Cleanup is active before launch and before the ownership
                # write, so a failed receipt cannot leave a native child alive.
                if process is not None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    try:
                        os.killpg(process.pid, 0)
                        group_absent = False
                    except ProcessLookupError:
                        group_absent = True
                    record.update(processGroupAbsent=group_absent, exitCode=process.returncode)
                    assert group_absent
    finally:
        if temp is not None:
            record["temporaryDirectoryAbsent"] = not Path(temp).exists()
            assert record["temporaryDirectoryAbsent"]
        if ownership is not None:
            ownership.write_text(json.dumps(record, indent=2) + "\n")
    assert process.returncode == 0, stdout + stderr


def test_failed_ownership_write_still_cleans_native_process(monkeypatch, tmp_path):
    import importlib
    module = importlib.import_module(__name__)
    monkeypatch.setattr(module, "ROOT", tmp_path / "placid-badger")
    monkeypatch.setenv("HANGTEN_CAD_PYTHONPATH", "unused-fake-native-path")
    signals = []

    class Process:
        pid = 123987
        returncode = None

        def communicate(self, timeout):
            pytest.fail("receipt failure must occur before native communicate")

        def wait(self):
            self.returncode = -9

    process = Process()
    monkeypatch.setattr(module.subprocess, "Popen", lambda *a, **k: process)

    def kill_group(pid, sig):
        assert pid == process.pid
        signals.append(sig)
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(module.os, "killpg", kill_group)
    original_write = Path.write_text
    failed = []

    def fail_first_receipt(path, text, *args, **kwargs):
        if path.name.endswith("-ownership.json") and not failed:
            failed.append(path)
            raise OSError("injected ownership receipt failure")
        return original_write(path, text, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_first_receipt)
    with pytest.raises(OSError, match="injected ownership"):
        test_native_cord_feature_extraction()
    assert signals == [signal.SIGKILL, 0]
    receipt = json.loads(failed[0].read_text())
    assert receipt["processGroupAbsent"] and receipt["temporaryDirectoryAbsent"]
    assert not Path(receipt["temporaryDirectory"]).exists()
