"""Focused tests for manifest-driven supplied model imports."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import import_model_package as importer
import verify_imported_model_packages as verifier


class MappingValidationTests(unittest.TestCase):
    def mapping(self, meshes: list[dict[str, object]]) -> dict[str, object]:
        return {
            "schemaVersion": 1,
            "packageID": "fixture",
            "logicalHoldIDs": ["left"],
            "objects": meshes,
        }

    def test_rejects_mapping_for_unknown_source_object(self) -> None:
        mapping = self.mapping(
            [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "Missing", "role": "hold", "holdID": "left"},
            ]
        )
        with self.assertRaisesRegex(importer.MappingError, "unknown source object: Missing"):
            importer.validate_mapping(mapping, {"Body": "MESH", "Hold": "MESH"})

    def test_rejects_duplicate_source_mapping(self) -> None:
        mapping = self.mapping(
            [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "Hold", "role": "hold", "holdID": "left"},
                {"sourceNodeID": "Hold", "role": "hold", "holdID": "left"},
            ]
        )
        with self.assertRaisesRegex(importer.MappingError, "duplicate source mapping: Hold"):
            importer.validate_mapping(mapping, {"Body": "MESH", "Hold": "MESH"})

    def test_rejects_incomplete_logical_inventory(self) -> None:
        mapping = self.mapping(
            [{"sourceNodeID": "Body", "role": "body"}]
        )
        with self.assertRaisesRegex(importer.MappingError, "unmapped logical hold IDs: left"):
            importer.validate_mapping(mapping, {"Body": "MESH"})

    def test_allows_multiple_named_meshes_for_one_logical_hold(self) -> None:
        mapping = self.mapping(
            [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "HoldA", "role": "hold", "holdID": "left"},
                {"sourceNodeID": "HoldB", "role": "hold", "holdID": "left"},
            ]
        )
        result = importer.validate_mapping(
            mapping, {"Body": "MESH", "HoldA": "MESH", "HoldB": "MESH"}
        )
        self.assertEqual(result.hold_ids_by_node["HoldA"], "left")
        self.assertEqual(result.hold_ids_by_node["HoldB"], "left")

    def test_attachment_must_be_nonselectable_and_nonmesh(self) -> None:
        mapping = self.mapping(
            [
                {"sourceNodeID": "Body", "role": "body"},
                {"sourceNodeID": "Hold", "role": "hold", "holdID": "left"},
                {
                    "sourceNodeID": "Passage",
                    "role": "attachment",
                    "selectable": False,
                },
            ]
        )
        result = importer.validate_mapping(
            mapping, {"Body": "MESH", "Hold": "MESH", "Passage": "EMPTY"}
        )
        self.assertEqual(result.attachment_node_ids, ("Passage",))


class SourceManifestTests(unittest.TestCase):
    def test_archive_hash_and_retained_member_hash_are_verified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("pkg/README.md", b"evidence\n")
                bundle.writestr("pkg/model.blend", b"blend")
            archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
            readme_hash = hashlib.sha256(b"evidence\n").hexdigest()
            entry = {
                "zipPath": str(archive),
                "zipSHA256": archive_hash,
                "sourceModel": "pkg/model.blend",
                "retainedMembers": {"pkg/README.md": readme_hash},
            }
            importer.verify_source_entry(entry)
            entry["retainedMembers"]["pkg/README.md"] = "0" * 64
            with self.assertRaisesRegex(importer.SourceManifestError, "hash mismatch"):
                importer.verify_source_entry(entry)

    def test_manifest_json_is_written_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            importer.write_json(output, {"z": 1, "a": 2})
            self.assertEqual(output.read_text(), '{\n  "a": 2,\n  "z": 1\n}\n')

    def test_normal_python_cli_uses_process_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "source.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("pkg/README.md", b"evidence\n")
                bundle.writestr("pkg/model.blend", b"blend")
            manifest = root / "manifest.json"
            mapping = root / "mapping.json"
            report = root / "report.json"
            importer.write_json(manifest, {"packages": [{
                "packageID": "rejected", "zipPath": str(archive),
                "zipSHA256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "sourceModel": "pkg/model.blend",
                "retainedMembers": {"pkg/README.md": hashlib.sha256(b"evidence\n").hexdigest()},
            }]})
            importer.write_json(mapping, {
                "schemaVersion": 1, "packageID": "rejected",
                "promotionStatus": "rejected", "rejectionReasons": ["incomplete"],
                "logicalHoldIDs": [], "objects": [],
            })
            process = ["import_model_package.py", "--manifest", str(manifest), "--mapping", str(mapping), "--package", "rejected", "--output-directory", str(root / "output"), "--report", str(report)]
            with patch.object(sys, "argv", process):
                self.assertEqual(importer.main(), 0)
            self.assertEqual(json.loads(report.read_text())["status"], "rejected")


class VerificationReportTests(unittest.TestCase):
    def test_report_pairs_keep_importer_and_source_ids_distinct(self) -> None:
        self.assertEqual(
            verifier.report_node_pairs({"Hold_mesh_001": "Hold", "Body_mesh_001": "Body"}),
            [("Body_mesh_001", "Body"), ("Hold_mesh_001", "Hold")],
        )

    def test_imported_hierarchy_nodes_are_not_treated_as_meshes(self) -> None:
        self.assertEqual(
            verifier.mesh_node_ids({"Root": "EMPTY", "Body_mesh_001": "MESH"}),
            {"Body_mesh_001"},
        )

    def test_accepts_normalized_importer_ids_through_source_correspondence(self) -> None:
        verifier.require_source_correspondence(
            {"Body_mesh_001": "Body", "Hold_mesh_001": "Hold"},
            {"Body", "Hold"},
        )

    def test_rejects_missing_explicit_source_id_correspondence(self) -> None:
        with self.assertRaisesRegex(ValueError, "source mesh IDs"):
            verifier.require_source_correspondence(
                {"Body_mesh_001": "Body", "Other_mesh_001": "Other"},
                {"Body", "Hold"},
            )

    def test_rejects_zero_triangle_mesh(self) -> None:
        report = {
            "status": "verified",
            "cleanReimport": True,
            "descriptorMatchesActualUSDZ": True,
            "meshes": [{"nodeID": "Body", "triangles": 0, "materials": ["Wood"]}],
        }
        with self.assertRaisesRegex(ValueError, "positive triangles"):
            verifier.validate_report_document(report)

    def test_rejects_materialless_mesh(self) -> None:
        report = {
            "status": "verified",
            "cleanReimport": True,
            "descriptorMatchesActualUSDZ": True,
            "meshes": [{"nodeID": "Body", "triangles": 2, "materials": []}],
        }
        with self.assertRaisesRegex(ValueError, "native material"):
            verifier.validate_report_document(report)


if __name__ == "__main__":
    unittest.main()
