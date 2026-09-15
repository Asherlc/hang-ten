"""Contract tests for the Training Center shipped-asset verifier."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path


class VerifyTrangoRockProdigyTrainingCenterTests(unittest.TestCase):
    def test_expected_contact_inventory_is_the_existing_ordered_catalog_inventory(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        root = Path(__file__).resolve().parents[2]
        board = json.loads(
            (root / "Hangboards/trango-rock-prodigy-training-center/board.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            verifier.EXPECTED_CONTACT_IDS,
            tuple(contact["id"] for contact in board["contacts"]),
        )
        self.assertEqual(24, len(verifier.EXPECTED_CONTACT_IDS))

    def test_mapping_retains_distinct_bilateral_pinch_contacts(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        self.assertEqual(
            verifier.EXPECTED_SOURCE_TO_CONTACT_IDS["pinch-medium-left"],
            "pinch-medium-left",
        )
        self.assertEqual(
            verifier.EXPECTED_SOURCE_TO_CONTACT_IDS["pinch-wide-left"],
            "pinch-wide-left",
        )
        self.assertEqual(
            verifier.EXPECTED_SOURCE_TO_CONTACT_IDS["pinch-medium-right"],
            "pinch-medium-right",
        )
        self.assertEqual(
            verifier.EXPECTED_SOURCE_TO_CONTACT_IDS["pinch-wide-right"],
            "pinch-wide-right",
        )
        self.assertEqual(
            set(verifier.EXPECTED_SOURCE_TO_CONTACT_IDS.values()),
            set(verifier.EXPECTED_CONTACT_IDS),
        )


if __name__ == "__main__":
    unittest.main()
