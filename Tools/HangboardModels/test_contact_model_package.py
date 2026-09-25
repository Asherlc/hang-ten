"""Contact-first model compiler boundary tests."""

from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


class ContactModelPackageTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("contact_model_package")
        except ModuleNotFoundError as error:
            self.fail(f"contact-first model package compiler is missing: {error}")

    def test_board_loader_accepts_only_v3_contact_inventory(self) -> None:
        compiler = self.module()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            current = root / "current.json"
            legacy = root / "legacy.json"
            current.write_text(json.dumps({"schemaVersion": 3, "contacts": [{"id": "left"}, {"id": "right"}]}))
            legacy.write_text(json.dumps({"schemaVersion": 2, "holds": [{"id": "left"}]}))

            self.assertEqual(
                compiler.load_logical_contact_ids(current),
                frozenset({"left", "right"}),
            )
            with self.assertRaisesRegex(ValueError, "schemaVersion must be 3"):
                compiler.load_logical_contact_ids(legacy)

    def test_compiler_rejects_unknown_descriptor_version_before_opening_scene(self) -> None:
        compiler = self.module()

        with self.assertRaisesRegex(ValueError, "descriptor_version must be 1 or 2"):
            compiler.compile_model_package(
                Path("source.blend"),
                Path("board.json"),
                Path("output"),
                descriptor_version=3,
            )

    def test_reusable_scene_must_declare_at_least_one_contact_slot(self) -> None:
        compiler = self.module()
        scene = SimpleNamespace(
            objects=(
                SimpleNamespace(type="MESH", get=lambda *_args, **_kwargs: None),
                SimpleNamespace(type="EMPTY", get=lambda *_args, **_kwargs: "ignored"),
            )
        )
        slot_ids = compiler._declared_contact_slot_ids(scene, imported=False)
        self.assertEqual(slot_ids, frozenset())
        with self.assertRaisesRegex(ValueError, "at least one contact slot"):
            compiler._require_reusable_contact_slots(slot_ids)
        self.assertEqual(
            compiler._require_reusable_contact_slots(frozenset({"edge"})),
            frozenset({"edge"}),
        )



if __name__ == "__main__":
    unittest.main()
