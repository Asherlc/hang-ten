from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from migration_manifest import MigrationManifest, load_migration_manifest


SCHEMA_PATH = Path(__file__).with_name("migration-manifest.schema.json")
EXPECTED_REVIEW_VIEWS = ("front", "three-quarter", "clay-detail", "active-hold")


def valid_document() -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "boardID": "metolius-wood-grips-compact-ii",
        "revision": "compact-ii-revision-3",
        "boardJSON": "Hangboards/metolius-wood-grips-compact-ii/board.json",
        "evidencePacket": "docs/source-audits/compact-ii/evidence-packet.json",
        "sourceBlend": {
            "path": "sources/compact-ii.blend",
            "sha256": "a" * 64,
        },
        "logicalHoldIDs": ["jug-left", "jug-right"],
        "presentation": {
            "id": "primary",
            "type": "model",
            "assetPath": "assets/primary.usdz",
            "descriptorPath": "assets/primary.model.json",
        },
        "positions": [
            {"id": "default", "activeHoldIDs": ["jug-left", "jug-right"]}
        ],
        "suspensionProfile": "none",
        "deliberateOmissions": ["screw holes", "mounting hardware"],
        "verification": {"triangleCeiling": 150000, "probeIDs": ["front"]},
        "reviewViews": ["front", "three-quarter", "clay-detail", "active-hold"],
        "artifacts": {"packageSHA256": "b" * 64, "descriptorSHA256": "c" * 64},
    }


class MigrationManifestTests(unittest.TestCase):
    def load(self, document: object) -> MigrationManifest:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manifest.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            return load_migration_manifest(path)

    def test_valid_manifest_preserves_order_and_typed_fields(self):
        manifest = self.load(valid_document())
        self.assertIsInstance(manifest, MigrationManifest)
        self.assertEqual(manifest.logical_hold_ids, ("jug-left", "jug-right"))
        self.assertEqual(manifest.presentation.asset_path, "assets/primary.usdz")
        self.assertEqual(manifest.positions[0].active_hold_ids, ("jug-left", "jug-right"))

    def test_unknown_members_are_rejected(self):
        document = valid_document()
        document["geometry"] = {}
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.load(document)

    def test_duplicate_keys_are_rejected(self):
        text = json.dumps(valid_document()).replace(
            '"schemaVersion": 1,', '"schemaVersion": 1, "schemaVersion": 1,', 1
        )
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manifest.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_migration_manifest(path)

    def test_null_and_wrong_scalar_kinds_are_rejected(self):
        for key, value in (("boardID", None), ("schemaVersion", "1"), ("logicalHoldIDs", "jug-left")):
            with self.subTest(key=key):
                document = valid_document()
                document[key] = value
                with self.assertRaises(ValueError):
                    self.load(document)

    def test_model_media_is_exactly_one_usdz_and_descriptor(self):
        document = valid_document()
        document["presentation"] = dict(document["presentation"], assetPath="assets/other.usdz")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "primary.usdz"):
            self.load(document)
        document = valid_document()
        document["presentation"] = dict(document["presentation"], descriptorPath="assets/other.model.json")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "primary.model.json"):
            self.load(document)

    def test_paths_must_be_relative_and_confined(self):
        for path_value in (
            "/tmp/model.usdz", "../model.usdz", "assets\\primary.usdz", "assets/../model.usdz",
            "assets/./primary.usdz", "assets//primary.usdz", "assets/primary\x00.usdz",
            "assets/primary\n.usdz", "assets/primary\x7f.usdz",
        ):
            with self.subTest(path=path_value):
                document = valid_document()
                document["presentation"] = dict(document["presentation"], assetPath=path_value)  # type: ignore[arg-type]
                with self.assertRaisesRegex(ValueError, "path"):
                    self.load(document)

    def test_every_path_bearing_field_uses_the_raw_relative_path_contract(self):
        mutations = (
            ("boardJSON", "assets/./board.json"),
            ("evidencePacket", "docs//evidence.json"),
            ("sourceBlend.path", "sources/../blend.blend"),
            ("presentation.assetPath", "assets/\x00primary.usdz"),
            ("presentation.descriptorPath", "assets/primary\n.model.json"),
        )
        for field, path_value in mutations:
            with self.subTest(field=field):
                document = valid_document()
                if field in {"boardJSON", "evidencePacket"}:
                    document[field] = path_value
                elif field == "sourceBlend.path":
                    document["sourceBlend"] = dict(document["sourceBlend"], path=path_value)  # type: ignore[arg-type]
                else:
                    document["presentation"] = dict(document["presentation"], **{field.split(".")[1]: path_value})  # type: ignore[arg-type]
                with self.assertRaisesRegex(ValueError, "path"):
                    self.load(document)

    def test_nested_duplicate_keys_are_rejected(self):
        text = json.dumps(valid_document()).replace(
            '"path": "sources/compact-ii.blend"',
            '"path": "sources/compact-ii.blend", "path": "sources/other.blend"',
            1,
        )
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "manifest.json"
            path.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_migration_manifest(path)

    def test_nested_explicit_null_and_wrong_scalar_type_are_rejected(self):
        for field, value in (("sourceBlend", None), ("presentation", "model"), ("verification", 1)):
            with self.subTest(field=field):
                document = valid_document()
                document[field] = value
                with self.assertRaises(ValueError):
                    self.load(document)

    def test_nonfinite_and_overflowed_numbers_are_rejected(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e400", "-1e400"):
            with self.subTest(token=token):
                text = json.dumps(valid_document()).replace("150000", token, 1)
                with tempfile.TemporaryDirectory() as raw:
                    path = Path(raw) / "manifest.json"
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, "finite|valid JSON"):
                        load_migration_manifest(path)

    def test_geometry_and_bounds_are_rejected_at_any_manifest_level(self):
        for key in ("geometry", "bounds", "modelBounds", "center"):
            document = valid_document()
            document["verification"] = dict(document["verification"], **{key: 1})  # type: ignore[arg-type]
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "geometry|bounds"):
                    self.load(document)

    def test_ids_are_nonempty_unique_and_position_ids_are_declared(self):
        document = valid_document()
        document["logicalHoldIDs"] = ["jug-left", "jug-left"]
        with self.assertRaisesRegex(ValueError, "logical"):
            self.load(document)
        document = valid_document()
        document["positions"] = [{"id": "default", "activeHoldIDs": ["unknown"]}]
        with self.assertRaisesRegex(ValueError, "position"):
            self.load(document)

    def test_positions_reject_duplicate_ids_and_duplicate_active_hold_ids(self):
        document = valid_document()
        document["positions"] = [
            {"id": "default", "activeHoldIDs": ["jug-left"]},
            {"id": "default", "activeHoldIDs": ["jug-right"]},
        ]
        with self.assertRaisesRegex(ValueError, "duplicate IDs"):
            self.load(document)

        document = valid_document()
        document["positions"] = [{"id": "default", "activeHoldIDs": ["jug-left", "jug-left"]}]
        with self.assertRaisesRegex(ValueError, "duplicate values"):
            self.load(document)

    def test_review_views_use_the_fixed_gallery_vocabulary(self):
        document = valid_document()
        document["reviewViews"] = ["front", "isometric"]
        with self.assertRaisesRegex(ValueError, "reviewViews"):
            self.load(document)

    def test_schema_declares_the_same_review_view_vocabulary_as_the_loader(self):
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        review_views = schema["properties"]["reviewViews"]
        self.assertEqual(tuple(review_views["items"]["enum"]), EXPECTED_REVIEW_VIEWS)
        self.assertEqual(review_views["minItems"], 1)
        self.assertNotIn("uniqueItems", schema["properties"]["positions"])

    def test_omissions_are_explicit_and_required(self):
        document = valid_document()
        document["deliberateOmissions"] = ["screw holes"]
        with self.assertRaisesRegex(ValueError, "omission"):
            self.load(document)

    def test_nonfinite_numbers_are_rejected(self):
        document = valid_document()
        document["verification"] = {"triangleCeiling": float("nan"), "probeIDs": []}
        with self.assertRaisesRegex(ValueError, "finite"):
            self.load(document)


if __name__ == "__main__":
    unittest.main()
