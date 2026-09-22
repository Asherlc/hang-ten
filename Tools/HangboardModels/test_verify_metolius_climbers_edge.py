"""Contract tests for the shipped Climber's Edge bore-removal verifier."""

from __future__ import annotations

import importlib
import unittest


class VerifyMetoliusClimbersEdgeTests(unittest.TestCase):
    def module(self):
        return importlib.import_module("verify_metolius_climbers_edge")

    def test_requires_all_eight_rays_to_hit_the_repaired_body_not_a_floating_cap(self) -> None:
        verifier = self.module()
        results = [
            {"x": x, "z": z, "intersects": True, "nodeID": "body_001"}
            for x, z in verifier.BORE_CENTERS_METERS
        ]
        verifier.require_bore_free_results(results)
        results[-1]["nodeID"] = "bore_free_body_caps_001"
        with self.assertRaisesRegex(ValueError, "body surface"):
            verifier.require_bore_free_results(results)


if __name__ == "__main__":
    unittest.main()
