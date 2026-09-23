"""Contact-first descriptor contract tests."""

from __future__ import annotations

import importlib
import hashlib
import json
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

    def test_reusable_descriptor_v2_uses_generic_slots(self) -> None:
        module = self.descriptor_module()
        descriptor = module.compile_reusable_descriptor(
            b"unit-usdz",
            (
                module.SlotNodeBinding("unit-body", "body"),
                module.SlotNodeBinding("unit-edge", "contact", "edge"),
            ),
            {"unit-body": ((0.0, 0.0, 0.0),), "unit-edge": ((0.2, 0.3, 0.0),)},
            frozenset({"edge"}),
        ).to_json()
        self.assertEqual(descriptor["schemaVersion"], 2)
        self.assertEqual(
            descriptor["nodes"],
            [
                {"nodeID": "unit-body", "role": "body"},
                {"nodeID": "unit-edge", "role": "contact", "contactSlotID": "edge"},
            ],
        )
        self.assertEqual(set(descriptor["contactSlots"]), {"edge"})

    def test_v1_descriptor_canonical_bytes_are_frozen(self) -> None:
        module = self.descriptor_module()
        descriptor = module.compile_descriptor(
            b"exact-usdz",
            [
                module.NodeBinding("Body", "body"),
                module.NodeBinding("Contact", "contact", "edge-left"),
            ],
            {
                "Body": [(0.0, 0.0, 0.0), (1.0, 1.0, 0.2)],
                "Contact": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)],
            },
            frozenset({"edge-left"}),
        )
        raw = json.dumps(
            descriptor.to_json(), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "63b9ce74f1c8f86011d0396f6638ba987cf83393c39f8899f2bb88b201ae43e0",
        )


    def test_authored_outline_defines_the_v2_slot_region(self) -> None:
        module = self.descriptor_module()
        descriptor = module.compile_reusable_descriptor(
            b"unit-usdz",
            (
                module.SlotNodeBinding("unit-body", "body"),
                module.SlotNodeBinding("unit-edge", "contact", "edge"),
            ),
            {"unit-body": ((0.0, 0.0, 0.0), (1.0, 1.0, 0.2)), "unit-edge": ((0.2, 0.3, 0.2),)},
            frozenset({"edge"}),
            {"edge": [(0.25, 0.6), (0.75, 0.6), (0.75, 0.8), (0.25, 0.8)]},
        ).to_json()
        slot = descriptor["contactSlots"]["edge"]
        self.assertEqual(slot["outline"], [[0.25, 0.6], [0.75, 0.6], [0.75, 0.8], [0.25, 0.8]])
        self.assertEqual(slot["facePlaneAABB"], {"min": [0.25, 0.6], "max": [0.75, 0.8]})
        self.assertEqual(slot["center"], [0.5, 0.7])

    def test_authored_outline_defines_the_v1_contact_region(self) -> None:
        module = self.descriptor_module()
        descriptor = module.compile_descriptor(
            b"board-usdz",
            [
                module.NodeBinding("Body", "body"),
                module.NodeBinding("Contact", "contact", "edge-left"),
            ],
            {"Body": [(0.0, 0.0, 0.0), (1.0, 1.0, 0.2)], "Contact": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)]},
            frozenset({"edge-left"}),
            {"edge-left": [(0.1, 0.2), (0.4, 0.2), (0.4, 0.5), (0.1, 0.5)]},
        ).to_json()
        contact = descriptor["contacts"]["edge-left"]
        self.assertEqual(contact["outline"], [[0.1, 0.2], [0.4, 0.2], [0.4, 0.5], [0.1, 0.5]])
        self.assertEqual(contact["facePlaneAABB"], {"min": [0.1, 0.2], "max": [0.4, 0.5]})

    def test_descriptor_without_an_outline_omits_the_key(self) -> None:
        module = self.descriptor_module()
        descriptor = module.compile_descriptor(
            b"board-usdz",
            [
                module.NodeBinding("Body", "body"),
                module.NodeBinding("Contact", "contact", "edge-left"),
            ],
            {"Body": [(0.0, 0.0, 0.0), (1.0, 1.0, 0.2)], "Contact": [(0.1, 0.2, 0.2), (0.4, 0.5, 0.2)]},
            frozenset({"edge-left"}),
        ).to_json()
        self.assertNotIn("outline", descriptor["contacts"]["edge-left"])

    def test_outline_parser_rejects_an_aabb_that_does_not_derive_from_the_outline(self) -> None:
        module = self.descriptor_module()
        value = {
            "schemaVersion": 2,
            "coordinateFrame": "hang-ten-board-v1",
            "modelSHA256": "0" * 64,
            "modelBounds": {"min": [0.0, 0.0, 0.0], "max": [1.0, 1.0, 0.2]},
            "nodes": [
                {"nodeID": "unit-body", "role": "body"},
                {"nodeID": "unit-edge", "role": "contact", "contactSlotID": "edge"},
            ],
            "contactSlots": {
                "edge": {
                    "nodeIDs": ["unit-edge"],
                    "facePlaneAABB": {"min": [0.1, 0.1], "max": [0.5, 0.6]},
                    "center": [0.3, 0.35],
                    "outline": [[0.1, 0.2], [0.4, 0.2], [0.4, 0.5], [0.1, 0.5]],
                }
            },
        }
        with self.assertRaisesRegex(ValueError, "facePlaneAABB must derive"):
            module.ModelDescriptorV2.from_json(value)




if __name__ == "__main__":
    unittest.main()
