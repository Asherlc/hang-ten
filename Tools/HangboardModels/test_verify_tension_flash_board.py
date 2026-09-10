"""Pure-contract tests for the Flash Board actual-export verifier."""

from __future__ import annotations

import importlib.util
import io
import json
import hashlib
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
        report["attachment"] = {"nodeID": "", "role": "body", "sourceNodeID": "flash-board-body"}
        with self.assertRaisesRegex(ValueError, "attachment"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["attachment"] = {
            "nodeID": "three-edge-left",
            "role": "hold",
            "sourceNodeID": "flash-board-body",
        }
        with self.assertRaisesRegex(ValueError, "attachment"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)


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


if __name__ == "__main__":
    unittest.main()
