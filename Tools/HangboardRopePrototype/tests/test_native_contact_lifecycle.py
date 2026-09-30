"""Exercise private-session cleanup using real, bounded owned children."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import sys
import time
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    "native_screen", REPO / "Tools/HangboardRopePrototype/run_native_contact_screen.py")
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class LifecycleTests(unittest.TestCase):
    def owned_root(self):
        owner = Path(os.environ.get("PASEO_WORKTREE_PATH", REPO)).name
        root = REPO / ".context" / f"{owner}-native-contact" / "lifecycle-tests"
        root.mkdir(parents=True, exist_ok=True)
        return owner, root

    def test_signal_during_spawn_is_deferred_until_session_is_owned(self):
        owner, root = self.owned_root()
        commands = screen.OwnedCommands(owner, root)
        original_handler = signal.signal(signal.SIGTERM, commands.interrupted)
        original_popen = screen.subprocess.Popen
        def interrupted_spawn(*args, **kwargs):
            child = original_popen(*args, **kwargs)
            # Actual signal at the otherwise nondeterministic registration
            # boundary; the subprocess and its private session are real.
            if kwargs.get("start_new_session"):
                os.kill(os.getpid(), signal.SIGTERM)
            return child
        try:
            with patch.object(screen.subprocess, "Popen", side_effect=interrupted_spawn):
                with self.assertRaises(SystemExit) as interrupted:
                    commands.run("spawn-interruption-test",
                                 [sys.executable, "-c", "import time; time.sleep(5)"],
                                 root / "spawn-interruption.log", dict(os.environ))
            self.assertEqual(interrupted.exception.code, 143)
            self.assertFalse(commands.active)
        finally:
            signal.signal(signal.SIGTERM, original_handler)
            commands.cleanup()

    def test_nonzero_child_status_is_preserved_after_cleanup(self):
        owner, root = self.owned_root()
        commands = screen.OwnedCommands(owner, root)
        status = commands.run("nonzero-test", [sys.executable, "-c", "raise SystemExit(7)"],
                              root / "nonzero.log", dict(os.environ))
        self.assertEqual(status, 7)
        self.assertFalse(commands.active)

    def test_interrupted_driver_deletes_running_private_session(self):
        owner, root = self.owned_root()
        script = root / f"{owner}-interrupt-child.py"
        script.write_text("""import os, signal, time
signal.alarm(5)
time.sleep(.05)
os.kill(int(os.environ['OWNED_DRIVER_PID']), signal.SIGTERM)
while True: time.sleep(.05)
""")
        commands = screen.OwnedCommands(owner, root)
        class Interrupted(Exception):
            pass
        def interrupted(signum, frame):
            raise Interrupted()
        original = signal.signal(signal.SIGTERM, interrupted)
        try:
            with self.assertRaises(Interrupted):
                commands.run("interruption-test", [sys.executable, str(script)],
                             root / "interruption.log", dict(os.environ, OWNED_DRIVER_PID=str(os.getpid())))
            self.assertFalse(commands.active)
            records = [json.loads(line) for line in commands.manifest.read_text().splitlines()]
            with self.assertRaises(ProcessLookupError):
                os.killpg(records[-1]["group"], 0)
        finally:
            signal.signal(signal.SIGTERM, original)
            commands.cleanup()

    def test_surviving_descendant_is_deleted_after_leader_exits(self):
        owner, root = self.owned_root()
        script = root / f"{owner}-term-resistant-child.py"
        # The child has its own five-second fail-safe so a broken cleanup
        # implementation cannot leave an unbounded process behind.
        script.write_text("""import os, signal, time
read, write = os.pipe()
if os.fork() == 0:
    os.close(read)
    null = os.open('/dev/null', os.O_WRONLY)
    os.dup2(null, 1)
    os.dup2(null, 2)
    os.close(null)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    signal.alarm(5)
    os.write(write, b'ready')
    os.close(write)
    while True: time.sleep(.05)
os.close(write)
os.read(read, 5)
os.close(read)
""")
        commands = screen.OwnedCommands(owner, root)
        try:
            status = commands.run("lifecycle-test", [sys.executable, str(script)],
                                  root / "run.log", dict(os.environ))
            self.assertEqual(status, 0)
            self.assertFalse(commands.active)
            records = [json.loads(line) for line in commands.manifest.read_text().splitlines()]
            owned = records[-2]
            self.assertEqual(records[-1]["status"], "deleted-and-verified")
            with self.assertRaises(ProcessLookupError):
                os.killpg(owned["group"], 0)
        finally:
            # Wait for the fixture's fail-safe if testing a broken version;
            # never signal any historical PID from an ownership file.
            deadline = time.monotonic() + 7
            while commands.active and time.monotonic() < deadline:
                try:
                    commands.cleanup()
                except RuntimeError:
                    time.sleep(.05)
            self.assertFalse(commands.active)


if __name__ == "__main__":
    unittest.main()
