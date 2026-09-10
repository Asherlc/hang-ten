"""Pure-contract tests for the Flash Board actual-export verifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest



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


if __name__ == "__main__":
    unittest.main()
