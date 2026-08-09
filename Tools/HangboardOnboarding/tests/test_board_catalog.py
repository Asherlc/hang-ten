from __future__ import annotations

import importlib.util
import json
import sys
import shutil
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
BOARD_PATH = REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "board.json"
ACCEPTED_RUN_PATH = (
    REPO_ROOT
    / "Tools"
    / "HangboardOnboarding"
    / "reference"
    / "metolius-compact-ii"
    / "accepted-run"
)

COMPACT_II_HOLD_IDS = {
    "jug-left",
    "jug-right",
    "sloper-flat-left",
    "sloper-flat-right",
    "sloper-round-center",
    "edge-29-left",
    "edge-29-right",
    "pocket-29-three-left",
    "pocket-29-three-right",
    "pocket-29-two-left",
    "pocket-29-two-right",
    "pocket-29-four-center",
    "edge-19-left",
    "edge-19-right",
    "pocket-19-three-left",
    "pocket-19-three-right",
    "pocket-19-two-left",
    "pocket-19-two-right",
    "pocket-19-four-center",
}


def load_module():
    module_path = (
        REPO_ROOT
        / "Tools"
        / "HangboardOnboarding"
        / "src"
        / "hangboard_vectorizer"
        / "board_catalog.py"
    )
    if not module_path.is_file():  # pragma: no cover - verified in red phase
        raise AssertionError("hangboard_vectorizer.board_catalog is missing")
    spec = importlib.util.spec_from_file_location("board_catalog_under_test", module_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise AssertionError("unable to load hangboard_vectorizer.board_catalog")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BoardCatalogTests(unittest.TestCase):
    def test_validate_catalog_accepts_compact_ii_package(self) -> None:
        module = load_module()
        self.assertTrue(CATALOG_PATH.is_file(), "Hangboards/catalog.json is missing")
        self.assertTrue(BOARD_PATH.is_file(), "Compact II board.json is missing")

        catalog = module.validate_catalog(CATALOG_PATH)
        board = module.load_board(BOARD_PATH)

        self.assertEqual([entry.id for entry in catalog.boards], ["metolius.wood-grips-compact-ii"])
        self.assertEqual(board.id, "metolius.wood-grips-compact-ii")
        self.assertEqual(board.lifecycle, "shipped")
        self.assertEqual(len(board.holds), 19)
        self.assertEqual({hold.id for hold in board.holds}, COMPACT_II_HOLD_IDS)
        self.assertEqual({hold.region_id for hold in board.holds}, set(range(1, 20)))

    def test_validate_catalog_rejects_duplicate_ids_and_escaping_paths(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)

            duplicate_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            duplicate_payload["boards"].append(
                {
                    "id": "metolius.wood-grips-compact-ii",
                    "path": "metolius-wood-grips-compact-ii/board.json",
                    "lifecycle": "shipped",
                }
            )
            catalog_path.write_text(json.dumps(duplicate_payload, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "duplicate"):
                module.validate_catalog(catalog_path)

            escape_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            escape_payload["boards"] = [
                {
                    "id": "metolius.wood-grips-compact-ii",
                    "path": "../outside/board.json",
                    "lifecycle": "shipped",
                }
            ]
            catalog_path.write_text(json.dumps(escape_payload, indent=2) + "\n", encoding="utf-8")
            outside = workspace / "outside"
            outside.mkdir()
            shutil.copy2(board_root / "board.json", outside / "board.json")

            with self.assertRaisesRegex(ValueError, "inside"):
                module.validate_catalog(catalog_path)

    def test_register_run_copies_artifacts_and_derives_approved_lifecycle(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"

            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["boards"][0]["lifecycle"] = "draft"
            catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")

            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            board_payload["lifecycle"] = "draft"
            board_payload["onboardingRuns"] = []
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

            registered = module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                ACCEPTED_RUN_PATH,
                run_id="accepted-run",
            )

            copied_run = board_root / "onboarding" / "runs" / "accepted-run"
            self.assertEqual(registered.lifecycle, "approved")
            self.assertTrue((copied_run / "run.json").is_file())
            self.assertTrue(
                (copied_run / "stages" / "04" / "attempt-0001" / "stage-4-manifest.json").is_file()
            )
            self.assertEqual(
                (copied_run / "run.json").read_bytes(),
                (ACCEPTED_RUN_PATH / "run.json").read_bytes(),
            )

            persisted = module.load_board(board_path)
            self.assertEqual(persisted.lifecycle, "approved")
            self.assertEqual([run.id for run in persisted.onboarding_runs], ["accepted-run"])
            self.assertEqual(persisted.onboarding_runs[0].region_count, 19)
            self.assertEqual(
                persisted.onboarding_runs[0].path.as_posix(),
                "onboarding/runs/accepted-run",
            )


def copy_catalog_fixture(destination_root: Path) -> tuple[Path, Path]:
    hangboards_root = destination_root / "Hangboards"
    board_root = hangboards_root / "metolius-wood-grips-compact-ii"
    board_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG_PATH, hangboards_root / "catalog.json")
    shutil.copy2(BOARD_PATH, board_root / "board.json")
    return hangboards_root / "catalog.json", board_root


if __name__ == "__main__":
    unittest.main()
