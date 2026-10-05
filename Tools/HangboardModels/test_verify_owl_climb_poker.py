"""Actual-USDZ regression for Poker's shared C/D rounded-contact section.

These probes are authored object-space coordinates, not image measurements.
The pre-fix export routed C's 25/40 mm rays to D and had a 44.90 degree ridge.
"""

from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest


class PokerRoundedSectionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("blender"), "Blender provides USD/NumPy")
    def test_exported_cd_relief_has_correct_ownership_and_no_geometric_ridge(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run(
            [shutil.which("blender"), "--background", "--factory-startup",
             "--python", str(root / "Tools/HangboardModels/verify_owl_climb_poker.py"),
             "--", str(root / "Hangboards/owl-climb-poker/assets/primary.usdz")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("POKER_CD_SECTION_OK", result.stdout)


class PokerOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from pxr import Sdf, Usd, UsdGeom
            path = Path(__file__).with_name("verify_owl_climb_poker.py")
            spec = importlib.util.spec_from_file_location("poker_verifier", path)
            cls.verifier = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.verifier)
        except ModuleNotFoundError as error:
            raise unittest.SkipTest("Host OpenUSD and NumPy are required") from error
        cls.Sdf, cls.Usd, cls.UsdGeom = Sdf, Usd, UsdGeom

    def test_native_mesh_uses_descriptor_identity_without_custom_attributes(self):
        stage = self.Usd.Stage.CreateInMemory()
        mesh = self.UsdGeom.Mesh.Define(stage, "/root/c_relief").GetPrim()
        self.assertEqual(self.verifier.mesh_owner(mesh, {"c_relief": "face-c-left-shallow-half-round"}),
                         "face-c-left-shallow-half-round")
        child = self.UsdGeom.Mesh.Define(stage, "/root/Board/Hold/D/Mesh").GetPrim()
        self.assertEqual(self.verifier.mesh_owner(child, {"Board/Hold/D": "face-d-left-deep-rounded-recess"}),
                         "face-d-left-deep-rounded-recess")

    def test_standalone_legacy_mesh_inherits_its_contact_attribute(self):
        stage = self.Usd.Stage.CreateInMemory()
        parent = self.UsdGeom.Xform.Define(stage, "/Board/Contact").GetPrim()
        parent.CreateAttribute("userProperties:contact_id", self.Sdf.ValueTypeNames.String).Set("legacy-contact")
        mesh = self.UsdGeom.Mesh.Define(stage, "/Board/Contact/Mesh").GetPrim()
        self.assertEqual(self.verifier.mesh_owner(mesh, None), "legacy-contact")
        body = self.UsdGeom.Mesh.Define(stage, "/Board/Body").GetPrim()
        self.assertEqual(self.verifier.mesh_owner(body, None), "body")

    def test_descriptor_does_not_silently_accept_missing_or_conflicting_identity(self):
        stage = self.Usd.Stage.CreateInMemory()
        mesh = self.UsdGeom.Mesh.Define(stage, "/root/relief").GetPrim()
        with self.assertRaisesRegex(AssertionError, "mesh missing from descriptor"):
            self.verifier.mesh_owner(mesh, {"other": "contact"})
        mesh.CreateAttribute("userProperties:contact_id", self.Sdf.ValueTypeNames.String).Set("wrong-contact")
        with self.assertRaisesRegex(AssertionError, "attribute conflict"):
            self.verifier.mesh_owner(mesh, {"relief": "correct-contact"})

    def test_descriptor_identity_is_bound_to_the_actual_asset_bytes(self):
        with tempfile.TemporaryDirectory(prefix="placid-badger-poker-identity-") as directory:
            asset = Path(directory) / "primary.usdz"
            asset.write_bytes(b"identity-fixture")
            self.assertIsNone(self.verifier.descriptor_owners(asset))
            document = {"schemaVersion": 1, "modelSHA256": hashlib.sha256(asset.read_bytes()).hexdigest(),
                        "nodes": [{"nodeID": "relief", "role": "contact", "contactID": "contact-c"},
                                  {"nodeID": "body", "role": "body"}]}
            asset.with_suffix(".model.json").write_text(json.dumps(document))
            self.assertEqual(self.verifier.descriptor_owners(asset), {"relief": "contact-c", "body": "body"})
            asset.write_bytes(b"replacement-mesh")
            with self.assertRaisesRegex(AssertionError, "SHA-256"):
                self.verifier.descriptor_owners(asset)

    def test_geometry_checks_still_reject_wrong_contact_ridges_and_flattened_relief(self):
        report = {"cRays": [], "dRays": [], "seams": []}
        for side, x in [("left", -.132), ("right", .132)]:
            report["cRays"] += [{"x": x, "owner": f"face-c-{side}-shallow-half-round", "frontZ": z}
                                for z in [.045, .035]]
            report["dRays"].append({"x": x, "owner": f"face-d-{side}-deep-rounded-recess", "frontZ": .025})
            report["seams"].append({"side": side, "angleDegrees": 2.75})
        self.verifier.require_section(report)
        wrong_owner = copy.deepcopy(report)
        wrong_owner["cRays"][0]["owner"] = "face-d-left-deep-rounded-recess"
        with self.assertRaisesRegex(AssertionError, "ownership"):
            self.verifier.require_section(wrong_owner)
        ridge = copy.deepcopy(report)
        ridge["seams"][0]["angleDegrees"] = 88.24
        with self.assertRaisesRegex(AssertionError, "geometric ridge"):
            self.verifier.require_section(ridge)
        flat = copy.deepcopy(report)
        for row in flat["cRays"]:
            row["frontZ"] = .049
        with self.assertRaisesRegex(AssertionError, "near-flush C skirt"):
            self.verifier.require_section(flat)
        shallow = copy.deepcopy(report)
        for row in shallow["dRays"]:
            row["frontZ"] = .045
        with self.assertRaisesRegex(AssertionError, "substantial rounded recess"):
            self.verifier.require_section(shallow)
        missing = copy.deepcopy(report)
        missing["seams"] = []
        with self.assertRaisesRegex(AssertionError, "missing shared C/D edge"):
            self.verifier.require_section(missing)


if __name__ == "__main__":
    unittest.main()
