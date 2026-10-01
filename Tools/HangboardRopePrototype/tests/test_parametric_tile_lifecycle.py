"""Catch a shell trap waiting for an RTK wrapper instead of its live driver."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import shutil
import sys
import time
import unittest

REPO = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('tile_owned_commands', REPO/'Tools/HangboardRopePrototype/run_native_contact_screen.py')
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class TileLauncherLifecycleTests(unittest.TestCase):
    def test_shell_interruption_waits_for_actual_driver_deletion(self):
        owner = Path(os.environ.get('PASEO_WORKTREE_PATH', REPO)).name
        root = REPO/'.context'/f'{owner}-parametric-tiles'/'lifecycle-test'
        root.mkdir(parents=True, exist_ok=True)
        pid_path = root/'current-driver.pid'
        pid_path.unlink(missing_ok=True)
        fixture = root/f'{owner}-bounded-driver.py'
        fixture.write_text('#!'+sys.executable+'\n'+'''import os, signal, time
from pathlib import Path
signal.alarm(5)
Path(os.environ['TILE_TEST_PID_PATH']).write_text(str(os.getpid()))
os.kill(int(os.environ['TILE_TEST_SHELL_PID']), signal.SIGTERM)
while True: time.sleep(.01)
''')
        fixture.chmod(0o700)
        real_rtk = shutil.which('rtk')
        wrapper = root/'rtk'
        # A permissible proxy wrapper that doesn't forward TERM. Everything
        # else delegates to the actual RTK. Cleanup must own the Python driver
        # directly, independently of an external wrapper's signal policy.
        wrapper.write_text('#!'+sys.executable+'\n'+f'''import os, signal, subprocess, sys
if len(sys.argv) > 2 and sys.argv[1] == 'proxy' and sys.argv[2] == {str(fixture)!r}:
    signal.alarm(5)
    subprocess.Popen(sys.argv[2:]).wait()
else:
    os.execv({real_rtk!r}, [{real_rtk!r}, *sys.argv[1:]])
''')
        wrapper.chmod(0o700)
        class ObservingCommands(screen.OwnedCommands):
            def release_reserved(self, process, label):
                # Observe before our outer fail-safe kills the private group:
                # that cleanup must not hide a broken inner launcher trap.
                if pid_path.exists():
                    pid = int(pid_path.read_text())
                    states = dict(self.group_members(process.pid))
                    self.driver_alive_at_shell_exit = pid in states and not states[pid].startswith('Z')
                super().release_reserved(process, label)
        commands = ObservingCommands(owner, root)
        commands.driver_alive_at_shell_exit = None
        env = dict(os.environ, HANGTEN_NATIVE_SCREEN_PYTHON=str(fixture), TILE_TEST_PID_PATH=str(pid_path),
                   PATH=str(root)+os.pathsep+os.environ['PATH'])
        script = REPO/'Tools/HangboardRopePrototype/run_parametric_tile_screen.sh'
        try:
            # exec preserves this exact shell PID through the launcher. The
            # fixture signals only its known parent shell; its alarm and the
            # outer current private group are independent cleanup fail-safes.
            started = time.monotonic()
            status = commands.run('tile-launcher-signal-fixture',
                ['bash', '-c', 'export TILE_TEST_SHELL_PID=$$; exec bash "$1"', 'tile-fixture', str(script)],
                root/'launcher.log', env)
            self.assertEqual(status, 143)
            self.assertIs(commands.driver_alive_at_shell_exit, False)
            # Waiting for the fixture's five-second alarm is not trap cleanup.
            self.assertLess(time.monotonic()-started, 2.)
            self.assertFalse(commands.active)
        finally:
            commands.cleanup()


if __name__ == '__main__':
    unittest.main()
