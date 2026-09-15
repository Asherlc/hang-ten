"""Contract tests for the Training Center shipped-asset verifier."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path


class VerifyTrangoRockProdigyTrainingCenterTests(unittest.TestCase):
    def test_duplicate_pinch_triangles_are_rejected_even_with_distinct_ids(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        triangle = ((0, 0, 0), (1, 0, 0), (0, 1, 0))
        triangles = {f"pinch-{kind}-{side}": {triangle} for side in ("left", "right") for kind in ("medium", "wide")}
        with self.assertRaisesRegex(ValueError, "share triangles"):
            verifier.require_disjoint_pinch_triangles(triangles)

    def test_distinct_pinch_triangles_can_share_boundary_vertices(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        triangles = {}
        for side in ("left", "right"):
            triangles[f"pinch-medium-{side}"] = {((0, 0, 0), (1, 0, 0), (0, 1, 0))}
            triangles[f"pinch-wide-{side}"] = {((1, 0, 0), (0, 1, 0), (1, 1, 0))}
        self.assertEqual(set(verifier.require_disjoint_pinch_triangles(triangles).values()), {1})

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

    def test_every_source_node_retains_its_reviewed_contact_binding(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        # These reviewed source labels intentionally differ from catalog facts.
        # Checking only the value set would let left/right or depth swaps pass.
        per_side = {
            "jug": "jug",
            "upper-variable-rail": "edge-large-vder",
            "lower-variable-rail": "edge-shallow-vder",
            "thin-crimp": "edge-thin-crimp",
            "three-finger-slot": "pocket-three-finger-slot",
            "shallow-index-middle-pocket": "pocket-index-middle-deep",
            "deep-middle-ring-pocket": "pocket-middle-ring-deep",
            "medium-index-middle-pocket": "pocket-index-middle-medium-shallow",
            "shallow-middle-ring-pocket": "pocket-middle-ring-shallow",
            "pinch-medium": "pinch-medium",
            "pinch-wide": "pinch-wide",
            "sloper": "sloper",
        }
        expected = {
            f"{source}-{side}": f"{contact}-{side}"
            for side in ("left", "right")
            for source, contact in per_side.items()
        }
        self.assertEqual(set(verifier.EXPECTED_SOURCE_TO_CONTACT_IDS), set(expected))
        for source_node, contact_id in expected.items():
            with self.subTest(source_node=source_node):
                self.assertEqual(verifier.EXPECTED_SOURCE_TO_CONTACT_IDS[source_node], contact_id)
        self.assertEqual(
            set(verifier.EXPECTED_SOURCE_TO_CONTACT_IDS.values()),
            set(verifier.EXPECTED_CONTACT_IDS),
        )


if __name__ == "__main__":
    unittest.main()
