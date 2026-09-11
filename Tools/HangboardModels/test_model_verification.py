"""Blender-free contract tests for the shared model verifier."""
from pathlib import Path
import json
import tempfile
import unittest

from model_verification import (
    BoardProbe, MaterialPolicy, ModelVerificationConfig, VerificationReport,
    verify_model_package,
)
from model_verification import _asset_inventory

TOOLS = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(TOOLS))
import verify_wood_grips_compact_ii as compact


class ModelVerificationTests(unittest.TestCase):
    def test_compact_adapter_config_preserves_exact_ordered_inventory_and_ceiling(self):
        config = compact.compact_ii_config()
        expected = tuple(
            item["id"] for item in json.loads(
                (TOOLS.parents[1] / "Hangboards/metolius-wood-grips-compact-ii/board.json").read_text()
            )["holds"]
        )
        self.assertEqual(config.expected_hold_ids, expected)
        self.assertEqual(len(config.expected_hold_ids), 19)
        self.assertEqual(config.package_relative_assets, frozenset({
            "assets/primary.usdz", "assets/primary.model.json"
        }))
        self.assertEqual(config.triangle_ceiling, 150_000)

    def test_compact_adapter_routes_through_shared_verifier(self):
        self.assertIs(compact.verify_model_package, verify_model_package)
    def config(self, board_json: Path) -> ModelVerificationConfig:
        return ModelVerificationConfig(
            board_id="fixture", board_json=board_json,
            package_relative_assets=frozenset({"assets/primary.usdz", "assets/primary.model.json"}),
            expected_hold_ids=("left", "right"),
        )

    def package(self, directory: Path, *, assets=("assets/primary.usdz", "assets/primary.model.json")) -> None:
        board = directory / "board.json"
        board.write_text(json.dumps({"holds": [{"id": "left"}, {"id": "right"}]}))
        for relative in assets:
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fixture" if path.suffix == ".usdz" else b"{}")

    def test_verify_model_package_rejects_an_unconfigured_regular_asset(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            self.package(package, assets=("assets/primary.usdz", "assets/primary.model.json", "assets/extra.bin"))
            with self.assertRaisesRegex(ValueError, "asset inventory"):
                verify_model_package(package, self.config(package / "board.json"))

    def test_ordered_logical_inventory_rejects_reordered_board(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            self.package(package)
            (package / "board.json").write_text(json.dumps({"holds": [{"id": "right"}, {"id": "left"}]}))
            with self.assertRaisesRegex(ValueError, "logical inventory"):
                verify_model_package(package, self.config(package / "board.json"))

    def test_probe_cannot_turn_off_core_inventory_failure(self):
        class PassingProbe:
            id = "pass"
            def run(self, imported, config):
                return {"id": self.id, "status": "passed"}
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            self.package(package)
            (package / "board.json").write_text(json.dumps({"holds": [{"id": "left"}]}))
            config = ModelVerificationConfig(**{**self.config(package / "board.json").__dict__, "board_probes": (PassingProbe(),)})
            with self.assertRaisesRegex(ValueError, "logical inventory"):
                verify_model_package(package, config)

    def test_report_serializes_stably_without_blender(self):
        report = VerificationReport(board_id="fixture", checks={"triangles": 3})
        self.assertEqual(json.loads(report.to_json())['boardID'], "fixture")
        self.assertEqual(report.to_dict()["checks"]["triangles"], 3)

    def test_canonical_material_policy_is_explicit(self):
        policy = MaterialPolicy.canonical_wood()
        self.assertTrue(policy.require_image)
        self.assertTrue(policy.require_embedded_texture)
        self.assertEqual(policy.texture_name, "canonical-neutral-wood.png")

    def test_empty_nested_asset_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            self.package(package)
            (package / "assets" / "empty").mkdir()
            with self.assertRaisesRegex(ValueError, "asset inventory"):
                verify_model_package(package, self.config(package / "board.json"))

    def test_nonempty_directory_named_empty_is_allowed(self):
        with tempfile.TemporaryDirectory() as raw:
            package = Path(raw)
            self.package(package)
            nested = package / "assets" / "empty"
            nested.mkdir()
            (nested / "extra.bin").write_bytes(b"x")
            self.assertEqual(
                _asset_inventory(package),
                frozenset({"assets/primary.usdz", "assets/primary.model.json", "assets/empty/extra.bin"}),
            )


if __name__ == "__main__":
    unittest.main()
