"""Blender-free contract tests for the Baguette Evo actual-export verifier."""

from __future__ import annotations

import importlib
import json
import unittest
from pathlib import Path
from types import SimpleNamespace


class VerifyYYBaguetteEvoTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("verify_yy_baguette_evo")
        except ModuleNotFoundError as error:
            self.fail(f"Baguette actual-export verifier is missing: {error}")

    def test_expected_inventory_is_the_current_ordered_contact_inventory(self) -> None:
        verifier = self.module()
        root = Path(__file__).resolve().parents[2]
        board = json.loads((root / "Hangboards/yy-baguette-evo/board.json").read_text())
        self.assertEqual(
            verifier.EXPECTED_CONTACT_IDS,
            tuple(item["id"] for item in board["contacts"]),
        )
        self.assertEqual(len(verifier.EXPECTED_CONTACT_IDS), 19)

    def test_report_contract_rejects_legacy_role_and_identity_fields(self) -> None:
        verifier = self.module()
        valid = {
            "status": "verified",
            "cleanReimport": True,
            "descriptorMatchesActualUSDZ": True,
            "meshes": [
                {
                    "nodeID": "Contact",
                    "role": "contact",
                    "contactID": "edge-20-left",
                    "triangles": 2,
                    "materials": ["Wood"],
                }
            ],
        }
        verifier.validate_report_document(valid)
        legacy = json.loads(json.dumps(valid))
        legacy["meshes"][0] = {
            "nodeID": "Hold",
            "role": "hold",
            "holdID": "edge-20-left",
            "triangles": 2,
            "materials": ["Wood"],
        }
        with self.assertRaisesRegex(ValueError, "role"):
            verifier.validate_report_document(legacy)

    def test_source_correspondence_requires_all_twenty_contact_pieces_and_body(self) -> None:
        verifier = self.module()
        correspondence = {f"imported-{index}": source for index, source in enumerate(verifier.EXPECTED_SOURCE_MESH_IDS)}
        verifier.require_source_correspondence(correspondence)
        correspondence.pop(next(iter(correspondence)))
        with self.assertRaisesRegex(ValueError, "source mesh"):
            verifier.require_source_correspondence(correspondence)

    def test_source_correspondence_rejects_swapped_contact_bindings(self) -> None:
        verifier = self.module()
        correspondence = {
            "BodyImported": "body",
            "LeftImported": "hold-edge-20mm-left",
            "RightImported": "hold-edge-20mm-right",
        }
        bindings = {
            "BodyImported": SimpleNamespace(role="body", contact_id=None),
            "LeftImported": SimpleNamespace(role="contact", contact_id="edge-20-left"),
            "RightImported": SimpleNamespace(role="contact", contact_id="edge-20-right"),
        }
        expected_roles = {
            "body": "body",
            "hold-edge-20mm-left": "contact",
            "hold-edge-20mm-right": "contact",
        }
        expected_contacts = {
            "hold-edge-20mm-left": "edge-20-left",
            "hold-edge-20mm-right": "edge-20-right",
        }

        verifier.require_source_bindings(
            correspondence,
            bindings,
            expected_roles,
            expected_contacts,
        )
        bindings["LeftImported"].contact_id = "edge-20-right"
        bindings["RightImported"].contact_id = "edge-20-left"
        with self.assertRaisesRegex(ValueError, "role/contact binding"):
            verifier.require_source_bindings(
                correspondence,
                bindings,
                expected_roles,
                expected_contacts,
            )


if __name__ == "__main__":
    unittest.main()
