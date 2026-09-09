"""Focused encoded-sRGB guard for the shared canonical wood source."""

from __future__ import annotations

from pathlib import Path
import unittest

from canonical_wood_color import (
    assert_light_neutral_wood_srgb,
    assert_standard_srgb_png_profile,
    srgb_color_evidence,
)


ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT / "Tools/HangboardModels/assets/canonical-neutral-wood.png"


class CanonicalWoodColorTests(unittest.TestCase):
    def test_committed_png_declares_standard_srgb_profile(self):
        assert_standard_srgb_png_profile(CANONICAL.read_bytes())

    def test_committed_encoded_srgb_is_light_neutral_wood(self):
        assert_light_neutral_wood_srgb(srgb_color_evidence(CANONICAL.read_bytes()))

    def test_white_high_albedo_is_rejected(self):
        with self.assertRaises(AssertionError):
            assert_light_neutral_wood_srgb((0.95, 0.95, 0.95, 0.02))

    def test_scene_kit_calibrated_light_tan_is_accepted(self):
        assert_light_neutral_wood_srgb((210 / 255, 196 / 255, 173 / 255, 0.04))


if __name__ == "__main__":
    unittest.main()
