"""Tests for audited direct-source contact model imports."""

from __future__ import annotations

import hashlib
import importlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


class ImportContactModelSourceTests(unittest.TestCase):
    def module(self):
        try:
            return importlib.import_module("import_contact_model_source")
        except ModuleNotFoundError as error:
            self.fail(f"contact-first source importer is missing: {error}")

    def mapping(self) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            "packageID": "fixture",
            "logicalContactIDs": ["edge"],
            "objects": [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "Left", "role": "contact", "contactID": "edge"},
                {"sourceNodeID": "Right", "role": "contact", "contactID": "edge"},
                {
                    "sourceNodeID": "Passage",
                    "role": "attachment",
                    "selectable": False,
                    "order": 1,
                    "position": [0.1, 0.2, 0.3],
                    "metadata": {"kind": "cord-passage"},
                },
            ],
        }

    def test_mapping_preserves_multiple_mesh_pieces_for_one_contact(self) -> None:
        importer = self.module()
        result = importer.validate_mapping(
            self.mapping(),
            {"Body": "MESH", "Left": "MESH", "Right": "MESH", "Passage": "EMPTY"},
        )
        self.assertEqual(result.contact_ids_by_node, {"Left": "edge", "Right": "edge"})
        self.assertEqual(result.logical_contact_ids, frozenset({"edge"}))
        self.assertEqual(result.attachment_node_ids, ("Passage",))

    def test_reusable_mapping_records_slot_ids(self) -> None:
        importer = self.module()
        mapping = {
            "schemaVersion": 2,
            "unitContactSlotIDs": ["edge"],
            "objects": [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "Left", "role": "contact", "contactSlotID": "edge"},
                {"sourceNodeID": "Right", "role": "contact", "contactSlotID": "edge"},
            ],
        }

        result = importer.validate_mapping(
            mapping,
            {"Body": "MESH", "Left": "MESH", "Right": "MESH"},
        )

        self.assertEqual(
            result.contact_slot_ids_by_node,
            {"Left": "edge", "Right": "edge"},
        )

    def test_mapping_rejects_legacy_hold_vocabulary(self) -> None:
        importer = self.module()
        mapping = self.mapping()
        mapping["objects"][1] = {"sourceNodeID": "Left", "role": "hold", "holdID": "edge"}
        with self.assertRaisesRegex(importer.MappingError, "unknown mapping role"):
            importer.validate_mapping(
                mapping,
                {"Body": "MESH", "Left": "MESH", "Right": "MESH", "Passage": "EMPTY"},
            )

    def test_manifest_requires_exact_user_provided_source_hash(self) -> None:
        importer = self.module()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "source.blend"
            source.write_bytes(b"audited source")
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps({
                "schemaVersion": 1,
                "packageID": "fixture",
                "manufacturerPhysicalAuthority": {"publisher": "Manufacturer", "evidencePacket": "evidence.json"},
                "historicalSource": {"status": "missing"},
                "auditedModelSource": {
                    "provenanceType": "user-provided",
                    "authorization": "explicit user ruling",
                    "retainedPath": str(source),
                    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                },
                "supersessionRuling": "Supersedes only the historical archive.",
            }))

            self.assertEqual(importer.verify_source_manifest(manifest, "fixture"), source.resolve())
            document = json.loads(manifest.read_text())
            document["auditedModelSource"]["sha256"] = "0" * 64
            manifest.write_text(json.dumps(document))
            with self.assertRaisesRegex(importer.SourceManifestError, "hash mismatch"):
                importer.verify_source_manifest(manifest, "fixture")

    def test_source_loader_dispatches_by_extension_after_empty_scene_reset(self) -> None:
        importer = self.module()
        calls: list[tuple[str, str | None]] = []

        bpy = SimpleNamespace(
            ops=SimpleNamespace(
                wm=SimpleNamespace(
                    read_factory_settings=lambda *, use_empty: calls.append(
                        ("reset", str(use_empty))
                    ),
                    open_mainfile=lambda *, filepath: calls.append(("blend", filepath)),
                ),
                import_scene=SimpleNamespace(
                    gltf=lambda *, filepath: calls.append(("gltf", filepath)),
                ),
            )
        )

        importer._load_source_model(bpy, Path("Retained.GLB"))
        self.assertEqual(
            calls,
            [("reset", "True"), ("gltf", "Retained.GLB")],
        )

        calls.clear()
        importer._load_source_model(bpy, Path("Retained.blend"))
        self.assertEqual(calls, [("blend", "Retained.blend")])


if __name__ == "__main__":
    unittest.main()
