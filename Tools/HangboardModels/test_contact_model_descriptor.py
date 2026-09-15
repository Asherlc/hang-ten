"""Contact-first descriptor contract tests."""

from __future__ import annotations

import importlib
import unittest


class ContactModelDescriptorTests(unittest.TestCase):
    def descriptor_module(self):
        try:
            return importlib.import_module("contact_model_descriptor")
        except ModuleNotFoundError as error:
            self.fail(f"contact-first descriptor compiler is missing: {error}")

    def test_compiler_emits_only_current_contact_fields(self) -> None:
        module = self.descriptor_module()

        nodes = [
            module.NodeBinding("Body", "body"),
            module.NodeBinding("Contact", "contact", "edge-left"),
        ]
        descriptor = module.compile_descriptor(
            b"exact-usdz",
            nodes,
            {
                "Body": [(0.0, 0.0, 0.0), (1.0, 1.0, 0.2)],
                "Contact": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)],
            },
            frozenset({"edge-left"}),
        ).to_json()

        self.assertEqual(
            set(descriptor),
            {"schemaVersion", "coordinateFrame", "modelSHA256", "modelBounds", "nodes", "contacts"},
        )
        self.assertEqual(
            descriptor["nodes"],
            [
                {"nodeID": "Body", "role": "body"},
                {"nodeID": "Contact", "role": "contact", "contactID": "edge-left"},
            ],
        )
        self.assertEqual(set(descriptor["contacts"]), {"edge-left"})
        self.assertNotIn("holds", descriptor)

    def test_descriptor_allows_multiple_bodies_attachments_and_contact_pieces(self) -> None:
        module = self.descriptor_module()
        nodes = [
            module.NodeBinding("BodyLeft", "body"),
            module.NodeBinding("BodyRight", "body"),
            module.NodeBinding("PassageLeft", "attachment"),
            module.NodeBinding("PassageRight", "attachment"),
            module.NodeBinding("ContactLeft", "contact", "edge"),
            module.NodeBinding("ContactRight", "contact", "edge"),
        ]
        vertices = {
            "BodyLeft": [(0.0, 0.0, 0.0), (0.45, 1.0, 0.2)],
            "BodyRight": [(0.55, 0.0, 0.0), (1.0, 1.0, 0.2)],
            "PassageLeft": [(0.1, 0.4, 0.0)],
            "PassageRight": [(0.9, 0.4, 0.0)],
            "ContactLeft": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)],
            "ContactRight": [(0.6, 0.2, 0.2), (0.9, 0.5, 0.2)],
        }

        descriptor = module.compile_descriptor(
            b"exact-usdz", nodes, vertices, frozenset({"edge"})
        )

        self.assertEqual(descriptor.contacts["edge"].node_ids, ("ContactLeft", "ContactRight"))
        self.assertEqual(
            [node.role for node in descriptor.nodes],
            ["body", "body", "contact", "contact", "attachment", "attachment"],
        )

    def test_descriptor_rejects_legacy_hold_fields(self) -> None:
        module = self.descriptor_module()
        legacy = {
            "schemaVersion": 1,
            "coordinateFrame": "hang-ten-board-v1",
            "modelSHA256": "0" * 64,
            "modelBounds": {"min": [0, 0, 0], "max": [1, 1, 1]},
            "nodes": [
                {"nodeID": "Body", "role": "body"},
                {"nodeID": "Hold", "role": "hold", "holdID": "left"},
            ],
            "holds": {
                "left": {
                    "nodeIDs": ["Hold"],
                    "facePlaneAABB": {"min": [0, 0], "max": [1, 1]},
                    "center": [0.5, 0.5],
                }
            },
        }
        with self.assertRaisesRegex(ValueError, "unknown key"):
            module.ModelDescriptorV1.from_json(legacy)


if __name__ == "__main__":
    unittest.main()
