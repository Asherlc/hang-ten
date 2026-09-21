"""Actual-USDZ regression for Poker's shared C/D rounded-contact section.

These probes are authored object-space coordinates, not image measurements.
The pre-fix export routed C's 25/40 mm rays to D and had a 44.90 degree ridge.
"""

from pathlib import Path
import shutil
import subprocess
import unittest


class PokerRoundedSectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("blender"), "Blender provides USD/NumPy")
    def test_exported_cd_relief_has_correct_ownership_and_no_geometric_ridge(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [shutil.which("blender"), "--background", "--factory-startup",
             "--python", str(root / "Tools/HangboardModels/verify_owl_climb_poker.py"),
             "--", str(root / "Hangboards/owl-climb-poker/assets/primary.usdz")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("POKER_CD_SECTION_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
