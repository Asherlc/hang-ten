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
LIGAMENT_GRID_SIZE = 3


def valid_report() -> dict[str, object]:
    candidate = verifier.load_review_candidate()
    bounds = {"min": [0.0, 0.0, 0.0], "max": [0.5, 0.075999998, 0.075999998]}
    branch_specs = {
        position_id: verifier._branch_probe_specs(
            bounds,
            candidate,
            candidate["canonicalPoses"][position_id],
            {passage_id: "flash-board-body" for passage_id in verifier.REVIEW_PASSAGE_IDS},
        )
        for position_id in verifier.POSITION_HOLD_IDS
    }
    logical_bindings = [
        {"nodeID": "flash-board-body", "role": "body"},
        *[
            {"nodeID": hold_id, "role": "hold", "holdID": hold_id}
            for hold_id in sorted(EXPECTED_IDS)
        ],
    ]
    passage_correspondence = [
        {
            "passageID": passage_id,
            "nodeID": "flash-board-body",
            "sourceNodeID": "flash-board-body",
            "role": "body",
            "pointInModel": list(verifier.REVIEW_PASSAGE_POINTS[passage_id]),
        }
        for passage_id in verifier.REVIEW_PASSAGE_IDS
    ]
    def clear_aperture_ray(origin, direction):
        return {
            "origin": list(origin),
            "direction": list(direction),
            "hit": False,
            "nearestRole": None,
            "nearestNodeID": None,
            "nearestTriangleIndex": None,
            "location": None,
            "passed": True,
        }

    swept_tube_probe = verifier._swept_passage_probe(
        (0.0, 0.0, 0.0),
        minimum_z=0.0,
        maximum_z=0.075999998,
        aperture_ray=clear_aperture_ray,
    )
    return {
        "boardID": "tension.flash-board",
        "candidateID": verifier.REVIEW_CANDIDATE_ID,
        "suspensionType": "twoBranchCord",
        "holdIDs": sorted(EXPECTED_IDS),
        "hold_ids_preserved": 7,
        "body_mesh_count": 1,
        "attachment_mesh_count": 0,
        "meshCount": 8,
        "logicalBindings": [
            {**binding, "sourceNodeID": binding["nodeID"]}
            for binding in logical_bindings
        ],
        "passageCorrespondence": passage_correspondence,
        "passageRayResults": [
            {
                "passageID": passage_id,
                "nodeID": "flash-board-body",
                "sourceNodeID": "flash-board-body",
                "hit": True,
                "nearestRole": "body",
                "nearestTriangleIndex": 0,
                "surfaceDepthMeters": 0.001,
                "behavior": "through-passage",
                "sweptTubeProbe": swept_tube_probe,
                "passed": True,
            }
            for passage_id in verifier.REVIEW_PASSAGE_IDS
        ],
        "texturedMeshCount": 8,
        "materialChecks": [
            {"nodeID": binding["nodeID"], "material": "canonical-neutral-wood", "images": [{"name": "canonical", "width": 1, "height": 1}]}
            for binding in logical_bindings
        ],
        "modelSHA256": candidate["expectedModel"]["modelSHA256"],
        "descriptorSHA256": candidate["expectedModel"]["descriptorSHA256"],
        "modelIdentity": candidate["expectedModel"]["identity"],
        "coordinateFrame": "hang-ten-board-v1",
        "modelBounds": bounds,
        "exactDescriptorForActualUSDZ": True,
        "sourceImagesClearedBeforeImport": True,
        "sourcePieceCorrespondence": {
            binding["nodeID"]: binding["nodeID"] for binding in logical_bindings
        },
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
                "rayProbeCount": len(verifier.POSITION_HOLD_IDS[position_id]) * 5,
                "ligamentResults": [
                    {
                        "regionID": region_id,
                        "sampleRow": row,
                        "sampleColumn": column,
                        "expectedRole": "body",
                        "nearestRole": "body",
                        "nearestTriangleIndex": index,
                        "passed": True,
                    }
                    for index, (region_id, row, column) in enumerate(
                        (region_id, row, column)
                        for region_id in verifier.LIGAMENT_IDS_BY_POSITION[position_id]
                        for row in range(LIGAMENT_GRID_SIZE)
                        for column in range(LIGAMENT_GRID_SIZE)
                    )
                ],
                "allLigamentProbesPassed": True,
                "surfaceRayResults": [
                    {
                        "expectedID": hold_id,
                        "sampleIndex": sample_index,
                        "nearestID": hold_id,
                        "nearestTriangleIndex": 0,
                        "hit": True,
                        "passed": True,
                    }
                    for hold_id in verifier.POSITION_HOLD_IDS[position_id]
                    for sample_index in range(5)
                ],
                "branchClearanceResults": [
                    {
                        "branchID": spec["branchID"],
                        "passageIDs": spec["passageIDs"],
                        "interfacePoints": [
                            {"passageID": passage_id, "nodeID": node_id, "pointInModel": list(point)}
                            for passage_id, (node_id, point) in zip(spec["passageIDs"], spec["interfacePoints"])
                        ],
                        "passed": True,
                        "minimumDistanceMeters": 0.004,
                        "requiredClearanceMeters": 0.003,
                        "sampleCount": 99,
                        "centerlineSampleCount": len(spec["samples"]),
                        "centerlineSamples": [list(point) for point in spec["samples"]],
                        "declaredRestLengthMeters": 0.75,
                    }
                    for spec in branch_specs[position_id]
                ],
                "clearanceProbeCount": 198,
                "allRayProbesPassed": True,
                "allClearanceProbesPassed": True,
                "actualMeshClearance": True,
                "canonicalPoseTested": True,
            }
            for position_id in verifier.POSITION_HOLD_IDS
        },
    }


class VerifyTensionFlashBoardTests(unittest.TestCase):
    def test_review_candidate_binds_exact_named_passages_and_poses(self):
        candidate = verifier.load_review_candidate()
        self.assertEqual(candidate["candidateID"], verifier.REVIEW_CANDIDATE_ID)
        self.assertEqual(
            [item["id"] for item in candidate["passages"]["left"] + candidate["passages"]["right"]],
            list(verifier.REVIEW_PASSAGE_IDS),
        )
        self.assertEqual(set(candidate["canonicalPoses"]), set(verifier.POSITION_HOLD_IDS))

    def test_tracked_candidate_pins_model_anchor_and_branch_dimensions(self):
        candidate = verifier.load_review_candidate()
        self.assertTrue(verifier.REVIEW_CANDIDATE_PATH.is_file())
        self.assertEqual(
            candidate["expectedModel"],
            {
                "identity": "tension.flash-board.reviewed-usdz-v1",
                "sourceBodyNodeID": "flash-board-body",
                "modelSHA256": "4098ba4f8d8211683e6ec5c4466cd2725c0a040caae4a75e561d705315757524",
                "descriptorSHA256": "fd2c3e057c9feee1d6da57448bd9e4d58510ae8a6c60120282e51b13c228019c",
                "coordinateFrame": "hang-ten-board-v1",
            },
        )
        self.assertEqual(candidate["anchor"]["offsetFromBoardBounds"], [0, 0.22, 0])
        self.assertEqual(
            [(branch["id"], branch["restLength"], branch["radius"]) for branch in candidate["branches"]],
            [("left-branch", 0.75, 0.002), ("right-branch", 0.75, 0.002)],
        )

    def test_review_candidate_rejects_arbitrary_passage_identity_or_point(self):
        candidate = verifier.load_review_candidate()
        candidate["passages"]["left"][0]["id"] = "invented-hole"
        with self.assertRaisesRegex(ValueError, "passage"):
            verifier.validate_review_candidate(candidate)

        candidate = verifier.load_review_candidate()
        candidate["passages"]["right"][1]["pointInModel"][0] += 0.001
        with self.assertRaisesRegex(ValueError, "point"):
            verifier.validate_review_candidate(candidate)

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


    def test_verify_report_requires_four_passage_correspondences_and_nonselectable_inventory(self):
        report = valid_report()
        report["passageCorrespondence"] = report["passageCorrespondence"][:3]
        with self.assertRaisesRegex(ValueError, "four passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["logicalBindings"].append(
            {"nodeID": "lower-ledge", "role": "hold", "holdID": "three-edge-left"}
        )
        with self.assertRaisesRegex(ValueError, "selectable|binding"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["passageCorrespondence"][0]["role"] = "hold"
        with self.assertRaisesRegex(ValueError, "passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_requires_through_aperture_evidence_on_the_bound_body(self):
        report = valid_report()
        report["passageRayResults"][0]["sweptTubeProbe"]["samples"][0]["frontToRear"]["passed"] = False
        with self.assertRaisesRegex(ValueError, "passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        del report["passageRayResults"][0]["sweptTubeProbe"]["samples"][-1]
        with self.assertRaisesRegex(ValueError, "passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["passageCorrespondence"][0]["sourceNodeID"] = "wrong-body"
        with self.assertRaisesRegex(ValueError, "passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)


    def test_verify_report_requires_surface_rays_and_both_branch_clearance_results(self):
        report = valid_report()
        del report["positionProbes"]["three-edge-upright"]["surfaceRayResults"]
        with self.assertRaisesRegex(ValueError, "surface ray"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["positionProbes"]["two-edge-inverted"]["branchClearanceResults"] = []
        with self.assertRaisesRegex(ValueError, "branch clearance"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_rejects_fabricated_surface_ray_correspondence(self):
        for mutation in ("nearestID", "hit"):
            report = valid_report()
            ray = report["positionProbes"]["three-edge-upright"]["surfaceRayResults"][0]
            ray[mutation] = "wrong" if mutation == "nearestID" else False
            with self.subTest(mutation=mutation), self.assertRaisesRegex(ValueError, "surface ray"):
                verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_swept_passage_probe_rejects_centerline_open_but_tube_blocked_aperture(self):
        point = (0.25, 0.5, 0.0)
        blocked_offset = verifier.PASSAGE_TUBE_RADIUS_METERS, 0.0

        def aperture_ray(origin, direction):
            offset = (origin[0] - point[0], origin[1] - point[1])
            blocked = abs(offset[0] - blocked_offset[0]) <= 1e-9 and abs(offset[1]) <= 1e-9
            return {
                "origin": list(origin),
                "direction": list(direction),
                "hit": blocked,
                "nearestRole": "body" if blocked else None,
                "nearestNodeID": "flash-board-body" if blocked else None,
                "nearestTriangleIndex": 7 if blocked else None,
                "location": list(origin) if blocked else None,
                "passed": not blocked,
            }

        probe = verifier._swept_passage_probe(
            point,
            minimum_z=0.0,
            maximum_z=0.076,
            aperture_ray=aperture_ray,
        )
        self.assertFalse(probe["passed"])
        self.assertTrue(probe["samples"][0]["passed"])
        blocked = [sample for sample in probe["samples"] if not sample["passed"]]
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["offsetMeters"], [verifier.PASSAGE_TUBE_RADIUS_METERS, 0.0])

    def test_verify_report_rejects_repeated_surface_sample_indices(self):
        report = valid_report()
        rays = report["positionProbes"]["three-edge-upright"]["surfaceRayResults"]
        rays[1]["sampleIndex"] = 0
        with self.assertRaisesRegex(ValueError, "surface ray"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_rejects_wrong_branch_linkage_or_pose_flag(self):
        report = valid_report()
        report["positionProbes"]["three-edge-upright"]["branchClearanceResults"][0]["passageIDs"] = [
            "right-inner-passage", "right-outer-passage"
        ]
        with self.assertRaisesRegex(ValueError, "branch passage"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["positionProbes"]["three-edge-upright"]["canonicalPoseTested"] = False
        with self.assertRaisesRegex(ValueError, "canonical"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_requires_full_named_ligament_inventory(self):
        report = valid_report()
        report["positionProbes"]["two-edge-upright"]["ligamentResults"].pop()
        with self.assertRaisesRegex(ValueError, "ligament"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

        report = valid_report()
        report["positionProbes"]["three-edge-inverted"]["ligamentResults"][1]["sampleColumn"] = 0
        with self.assertRaisesRegex(ValueError, "ligament"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)

    def test_verify_report_rejects_model_hash_not_bound_to_candidate_fixture(self):
        report = valid_report()
        report["modelSHA256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "model"):
            verifier.verify_report(report, expected_ids=EXPECTED_IDS)


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

    def test_interface_exception_does_not_mask_body_collision_beyond_interface_point(self):
        samples = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]

        def nearest(node_id, point):
            if point == samples[-1]:
                return 0.0005, (1.0005, 0.0, 0.0)
            return 1.0, point

        result = verifier._check_centerline_clearance(
            samples,
            required_clearance=0.003,
            attachment_node_id="flash-board-body",
            interface_points=(("flash-board-body", samples[-1]),),
            nearest=nearest,
        )
        self.assertFalse(result["passed"])

    def test_two_branch_probe_specs_cover_both_branches_and_their_passage_interfaces(self):
        suspension = {
            "type": "twoBranchCord",
            "passages": {
                "left": [
                    {"id": "left-top", "nodeID": "body", "pointInModel": [0.2, 0.9, 0.05]},
                    {"id": "left-bottom", "nodeID": "body", "pointInModel": [0.3, 0.9, 0.05]},
                ],
                "right": [
                    {"id": "right-top", "nodeID": "body", "pointInModel": [0.7, 0.9, 0.05]},
                    {"id": "right-bottom", "nodeID": "body", "pointInModel": [0.8, 0.9, 0.05]},
                ],
            },
            "branches": [
                {"id": "left-branch", "passageIDs": ["left-top", "left-bottom"], "restLength": 1.5, "radius": 0.002},
                {"id": "right-branch", "passageIDs": ["right-top", "right-bottom"], "restLength": 1.5, "radius": 0.002},
            ],
            "anchor": {"offsetFromBoardBounds": [0, 0.22, 0]},
        }
        pose = {"rotation": [0, 0, 0, 1], "translation": [0, 0, 0]}
        specs = verifier._branch_probe_specs(
            {"min": [0, 0, 0], "max": [1, 1, 1]},
            suspension,
            pose,
            {passage_id: "body" for passage_id in ("left-top", "left-bottom", "right-top", "right-bottom")},
        )
        self.assertEqual([spec["branchID"] for spec in specs], ["left-branch", "right-branch"])
        self.assertTrue(all(len(spec["samples"]) == 64 for spec in specs))
        self.assertTrue(all(len(spec["interfacePoints"]) == 2 for spec in specs))
        self.assertEqual(specs[0]["passageIDs"], ["left-top", "left-bottom"])


if __name__ == "__main__":
    unittest.main()
