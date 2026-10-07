"""Contract tests for the Training Center shipped-asset verifier."""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path


PACKAGE_SOURCE = Path(__file__).resolve().parents[1] / "HangboardPackages" / "src"
if str(PACKAGE_SOURCE) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SOURCE))
board_catalog = importlib.import_module("hangboard_packages.board_catalog")


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

    def test_reusable_verifier_rebuilds_authored_bounds_and_slot_frames(self) -> None:
        import copy
        import tempfile
        import zipfile
        from contact_model_descriptor import SlotNodeBinding, compile_reusable_descriptor
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        model_bytes = b"fixture-usdz"
        vertices = {"body": [(-0.3, 0, 0), (-0.1, 1, 0.1)],
                    "hold": [(-0.25, 0.2, 0), (-0.2, 0.6, 0.05)]}
        model = {"nodes": {name: {"points_m": points} for name, points in vertices.items()}}
        nodes = [SlotNodeBinding("body", "body"), SlotNodeBinding("hold", "contact", "edge")]
        outlines = {"edge": [(-0.25, 0.2), (-0.2, 0.2), (-0.2, 0.6), (-0.25, 0.6)]}
        expected = compile_reusable_descriptor(model_bytes, nodes, vertices, frozenset({"edge"}), outlines).to_json()
        scratch = Path(__file__).resolve().parents[2] / ".context" / "verifier-tests"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            package = Path(directory) / "fixture"
            package.mkdir()
            document = """<Document><ObjectData>
            <Object name="Body"><Properties>
              <Property name="NodeID"><String value="body"/></Property>
              <Property name="NodeRole"><String value="body"/></Property>
            </Properties></Object>
            <Object name="Hold"><Properties>
              <Property name="NodeID"><String value="hold"/></Property>
              <Property name="NodeRole"><String value="contact"/></Property>
              <Property name="ContactSlotID"><String value="edge"/></Property>
              <Property name="HangTenHoldOutline"><String value="[[-250,200],[-200,200],[-200,600],[-250,600]]"/></Property>
            </Properties></Object></ObjectData></Document>"""
            with zipfile.ZipFile(package.parent / "fixture.FCStd", "w") as archive:
                archive.writestr("Document.xml", document)
            verifier.require_reusable_descriptor_matches_source(package, model_bytes, model, expected)
            for field in ("modelBounds", "contactSlots"):
                stale = copy.deepcopy(expected)
                if field == "modelBounds":
                    stale[field]["min"][0] -= 0.01
                else:
                    stale[field]["edge"]["center"][0] += 0.01
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, "descriptor.*CAD.*USDZ"):
                    verifier.require_reusable_descriptor_matches_source(package, model_bytes, model, stale)

    def test_expected_contact_inventory_is_the_existing_ordered_catalog_inventory(self) -> None:
        verifier = importlib.import_module("verify_trango_rock_prodigy_training_center")
        root = Path(__file__).resolve().parents[2]
        board = json.loads(
            board_catalog.read_board_json(
                root / "Hangboards/trango-rock-prodigy-training-center"
            )
        )
        self.assertEqual(
            verifier.EXPECTED_CONTACT_IDS,
            tuple(contact["id"] for contact in board["contacts"]),
        )
        self.assertEqual(24, len(verifier.EXPECTED_CONTACT_IDS))

if __name__ == "__main__":
    unittest.main()
