"""Blender-free contract tests for The Hangboard shipped-asset verifier."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path


class VerifyTheHangboardTests(unittest.TestCase):
    def module(self):
        return importlib.import_module("verify_the_hangboard")

    def test_expected_inventory_is_the_existing_ordered_contact_inventory(self) -> None:
        verifier = self.module()
        root = Path(__file__).resolve().parents[2]
        board = json.loads((root / "Hangboards/the-hangboard/board.json").read_text(encoding="utf-8"))
        self.assertEqual(verifier.EXPECTED_CONTACT_IDS, tuple(item["id"] for item in board["contacts"]))
        self.assertEqual(15, len(verifier.EXPECTED_CONTACT_IDS))

    def test_repaired_surface_contract_rejects_floating_caps(self) -> None:
        verifier = self.module()
        results = [
            {"x": x, "z": z, "intersects": True, "nodeID": "body_001"}
            for x, z in verifier.MOUNTING_CAP_CENTERS_METERS
        ]
        verifier.require_hardware_free_results(results)
        results[-1]["nodeID"] = "mounting_hardware_omission_caps_001"
        with self.assertRaisesRegex(ValueError, "body surface"):
            verifier.require_hardware_free_results(results)


if __name__ == "__main__":
    unittest.main()
