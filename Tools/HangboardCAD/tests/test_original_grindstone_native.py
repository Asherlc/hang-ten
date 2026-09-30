"""Native edit propagation and cavity topology for the original 2017 board."""
from pathlib import Path
import subprocess
import sys
import os
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[3]
FREECAD = Path(os.environ.get('HANGTEN_FREECAD_CMD', '/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd'))


@pytest.mark.skipif(not FREECAD.is_file(), reason='pinned FreeCAD is unavailable')
def test_original_grindstone_native_source():
    (ROOT / '.context').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=ROOT.name + '-grindstone-test-', dir=ROOT / '.context') as scratch:
        result = subprocess.run(
            [sys.executable, str(ROOT / 'Tools/HangboardCAD/run_freecad.py'),
             '--freecad', str(FREECAD),
             str(ROOT / 'Tools/HangboardCAD/tests/original_grindstone_native_source_checks.py'), scratch],
            cwd=ROOT, capture_output=True, text=True, timeout=300,
            env={**os.environ, 'TMPDIR': scratch},
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'all original Grindstone native source checks passed' in result.stdout
