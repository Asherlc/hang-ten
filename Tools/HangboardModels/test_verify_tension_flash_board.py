"""Pure-contract tests for the Flash Board actual-export verifier."""

from __future__ import annotations

import importlib.util
import io
import json
import hashlib
import itertools
from pathlib import Path
import unittest
import zipfile
import struct
import zlib



TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "verify_tension_flash_board", TOOLS / "verify_tension_flash_board.py"
)
assert SPEC and SPEC.loader
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


EXPECTED_IDS = frozenset(
    {
        "three-edge-left",
        "three-edge-center",
        "three-edge-right",
        "two-edge-left",
        "two-edge-right",
        "small-crimp-left",
        "small-crimp-right",
    }
)


def valid_report() -> dict[str, object]:
    return {
        "boardID": "tension.flash-board",
        "holdIDs": sorted(EXPECTED_IDS),
        "hold_ids_preserved": 7,
        "body_mesh_count": 1,
        "attachment_mesh_count": 0,
        "hardware_mesh_count": 0,
        "baked_cord_mesh_count": 0,
        "baked_anchor_mesh_count": 0,
        "triangleCeiling": verifier.TRIANGLE_CEILING,
        "triangles": 39232,
        "explicitTriangles": True,
        "canonicalTexture": {
            "member": "textures/canonical-neutral-wood.png",
            "sha256": hashlib.sha256(verifier._canonical_texture_bytes()).hexdigest(),
            "profile": {"sRGB": "00", "gAMA": "", "cHRM": ""},
        },
        "attachment": {
            "nodeID": "flash-board-body",
            "role": "body",
            "sourceNodeID": "flash-board-body",
            "accessible": True,
        },
        "positionProbes": {
            position_id: {
                "expectedHoldIDs": list(verifier.POSITION_HOLD_IDS[position_id]),
                "rayProbeCount": len(verifier.POSITION_HOLD_IDS[position_id]),
                "clearanceProbeCount": 1,
                "allRayProbesPassed": True,
                "allClearanceProbesPassed": True,
                "actualMeshClearance": True,
                "canonicalPoseTested": True,
            }
            for position_id in verifier.POSITION_HOLD_IDS
        },
    }


class VerifyTensionFlashBoardTests(unittest.TestCase):
    def test_position_specs_cover_exact_four_positions_and_their_active_holds(self):
        self.assertEqual(set(verifier.POSITION_HOLD_IDS), {
            "three-edge-upright",
            "three-edge-inverted",
            "two-edge-upright",
            "two-edge-inverted",
        })
        self.assertEqual(verifier.POSITION_HOLD_IDS["three-edge-upright"], (
            "three-edge-left",
            "three-edge-center",
            "three-edge-right",
        ))
        self.assertEqual(set(verifier.POSITION_HOLD_IDS["two-edge-upright"]), EXPECTED_IDS - {
            "three-edge-left",
            "three-edge-center",
            "three-edge-right",
        })


    def test_verify_report_accepts_the_actual_export_contract(self):
        report = verifier.verify_report(valid_report(), expected_ids=EXPECTED_IDS)
        self.assertEqual(report["hold_ids_preserved"], 7)
        self.assertEqual(report["attachment"]["nodeID"], "flash-board-body")


    def test_verify_report_rejects_contract_regressions(self):
        for field, value in (
            ("hold_ids_preserved", 6),
            ("body_mesh_count", 2),
            ("hardware_mesh_count", 1),
            ("baked_cord_mesh_count", 1),
            ("baked_anchor_mesh_count", 1),
            ("explicitTriangles", False),
        ):
            with self.subTest(field=field):
                report = valid_report()
                report[field] = value
                with self.assertRaises(ValueError):
                    verifier.verify_report(report, expected_ids=EXPECTED_IDS)


    def test_verify_report_rejects_unknown_or_missing_attachment_node(self):
        report = valid_report()
        report["attachment"]["nodeID"] = ""
        with self.assertRaisesRegex(ValueError, "attachment node must identify"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["attachment"].update(nodeID="three-edge-left", role="hold")
        with self.assertRaisesRegex(ValueError, "attachment node must be body or attachment role"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_rejects_inaccessible_attachment(self):
        for accessible in (False, None, 1, "true"):
            with self.subTest(accessible=accessible):
                report = valid_report()
                report["attachment"]["accessible"] = accessible
                with self.assertRaisesRegex(ValueError, "attachment"):
                    verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_every_canonical_pose_preserves_actual_descriptor_bounds(self):
        document = json.loads(verifier.BOARD_JSON.read_text(encoding="utf-8"))
        media = document["presentations"][0]["media"]
        descriptor = json.loads((verifier.BOARD_JSON.parent / media["descriptorPath"]).read_text())
        bounds = descriptor["modelBounds"]
        corners = list(itertools.product(*zip(bounds["min"], bounds["max"])))
        for position_id, pose in media["suspension"]["canonicalPoses"].items():
            with self.subTest(position=position_id):
                transformed = [verifier._transform_point(point, pose) for point in corners]
                for axis in range(3):
                    self.assertAlmostEqual(min(point[axis] for point in transformed), bounds["min"][axis], places=8)
                    self.assertAlmostEqual(max(point[axis] for point in transformed), bounds["max"][axis], places=8)

    def test_attachment_point_must_match_declared_finite_point_within_bounds(self):
        bounds = {"min": [0.0, 0.0, 0.0], "max": [0.5, 0.076, 0.076]}
        attachment = {"pointInModel": [0.017, 0.048, 0.076]}
        actual = verifier.validate_attachment_point(attachment, bounds)
        for value, expected in zip(actual, (0.017, 0.048, 0.076)):
            self.assertAlmostEqual(value, expected, places=9)
        attachment["pointInModel"] = [0.0170005, 0.048, 0.076]
        verifier.validate_attachment_point(attachment, bounds)
        for point in (None, [0.017, 0.048], [0.017, 0.048, 0.076, 0],
                      [True, 0.048, 0.076], ["0.017", 0.048, 0.076],
                      [10 ** 400, 0.048, 0.076],
                      [float("nan"), 0.048, 0.076], [0.017, float("inf"), 0.076],
                      [0.017002, 0.048, 0.076], [0.017, 0.048, 0.0760001]):
            with self.subTest(point=point):
                with self.assertRaisesRegex(ValueError, "attachment point"):
                    verifier.validate_attachment_point({"pointInModel": point}, bounds)


    def test_verify_report_requires_all_position_probe_results(self):
        report = valid_report()
        del report["positionProbes"]["two-edge-inverted"]
        with self.assertRaisesRegex(ValueError, "position"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_canonical_texture_contract_rejects_a_valid_substitute_png(self):
        canonical = verifier._canonical_texture_bytes()
        payload = b"alt\x00x"
        kind = b"tEXt"
        chunk = struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        substitute = canonical[:-12] + chunk + canonical[-12:]
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("textures/canonical-neutral-wood.png", substitute)
        with self.assertRaisesRegex(ValueError, "byte-identical"):
            verifier._verify_canonical_texture_archive(zipfile.ZipFile(io.BytesIO(archive.getvalue())))

    def test_pose_probe_uses_transformed_catenary_not_a_source_face_plane(self):
        document = json.loads(verifier.BOARD_JSON.read_text(encoding="utf-8"))
        suspension = document["presentations"][0]["media"]["suspension"]
        bounds = {"min": [0.0, 0.0, 0.0], "max": [0.5, 0.076, 0.076]}
        pose = suspension["canonicalPoses"]["three-edge-inverted"]
        samples = verifier._suspension_samples(bounds, suspension, pose)
        # A source-space straight probe would never expose the posed curve's
        # actual midpoint.  The canonical half-turn moves the attachment and
        # produces a finite slack catenary with a distinct midpoint.
        self.assertEqual(samples[0], (0.25, 0.296, 0.038))
        self.assertNotEqual(samples[len(samples) // 2], (0.25, 0.296, 0.038))
        self.assertNotEqual(samples[-1], tuple(suspension["attachment"]["pointInModel"]))

    def test_mesh_clearance_rejects_collision_even_when_plane_probe_would_pass(self):
        samples = [(0.0, 0.0, 0.1), (0.5, 0.0, 0.1)]
        # The legacy check only compared z against a board face plane at z=0;
        # this mesh callback reports a nearer actual triangle at the midpoint.
        def nearest(node_id, point):
            if node_id == "flash_board_body_008" and point[0] >= 0.25:
                return 0.0005, (point[0], point[1], 0.1005)
            return 1.0, point

        result = verifier._check_centerline_clearance(
            samples,
            required_clearance=0.003,
            attachment_node_id="flash_board_body_008",
            nearest=nearest,
        )
        self.assertFalse(result["passed"])

    def test_mesh_clearance_exempts_only_approved_attachment_endpoint(self):
        samples = [(0.0, 0.0, 0.1), (0.5, 0.0, 0.1), (1.0, 0.0, 0.1)]

        def check(contact, nearest_point, contact_node="attachment"):
            def nearest(node_id, point):
                if node_id == contact_node and point == contact:
                    return 0.0, nearest_point
                return 1.0, point
            nearest.node_ids = ("attachment", "hold")
            return verifier._check_centerline_clearance(
                samples, required_clearance=0.003,
                attachment_node_id="attachment", nearest=nearest,
            )["passed"]

        self.assertTrue(check(samples[-1], samples[-1]))
        self.assertFalse(check(samples[1], samples[1]))
        self.assertFalse(check(samples[-1], (1.0, 0.00002, 0.1)))
        self.assertFalse(check(samples[-1], samples[-1], "hold"))


if __name__ == "__main__":
    unittest.main()
