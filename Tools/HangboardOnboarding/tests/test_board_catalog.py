from __future__ import annotations

import importlib.util
import json
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = REPO_ROOT / "Hangboards" / "catalog.json"
BOARD_PATH = REPO_ROOT / "Hangboards" / "metolius-wood-grips-compact-ii" / "board.json"
ACCEPTED_RUN_PATH = (
    REPO_ROOT
    / "Tools"
    / "HangboardOnboarding"
    / "boards"
    / "metolius-wood-grips-compact-ii"
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
        pocket_holds = [hold for hold in board.holds if hold.kind == "pocket"]
        self.assertTrue(pocket_holds)
        for hold in pocket_holds:
            self.assertIn("pocket", hold.features)

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

    def test_validate_catalog_reports_missing_hold_frame_with_precise_path(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            del board_payload["holds"][0]["frame"]
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                r"board\.holds\[0\]\.frame is missing",
            ):
                module.validate_catalog(catalog_path)

    def test_validate_catalog_rejects_non_normalized_hold_frames(self) -> None:
        module = load_module()

        invalid_frames = (
            ({"x": -0.01}, r"board\.holds\[0\]\.frame\.x must stay inside"),
            ({"y": 0.9, "height": 0.2}, r"board\.holds\[0\]\.frame\.y must stay inside"),
            ({"width": 0}, r"board\.holds\[0\]\.frame\.x extent must be positive"),
            ({"height": -0.1}, r"board\.holds\[0\]\.frame\.y extent must be positive"),
        )

        for updates, expected_error in invalid_frames:
            with self.subTest(updates=updates), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir)
                catalog_path, board_root = copy_catalog_fixture(workspace)
                board_path = board_root / "board.json"
                board_payload = json.loads(board_path.read_text(encoding="utf-8"))
                board_payload["holds"][0]["frame"].update(updates)
                board_path.write_text(
                    json.dumps(board_payload, indent=2) + "\n", encoding="utf-8"
                )

                with self.assertRaisesRegex(ValueError, expected_error):
                    module.validate_catalog(catalog_path)

    def test_register_run_copies_artifacts_and_derives_approved_lifecycle(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_root = workspace / ".context"
            context_run_root = context_root / "hangboard-onboarding" / "accepted-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

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
                context_run_root,
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

    def test_register_run_keeps_non_complete_run_in_onboarding_lifecycle(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_run_root = workspace / ".context" / "hangboard-onboarding" / "partial-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["boards"][0]["lifecycle"] = "draft"
            catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            board_payload["lifecycle"] = "draft"
            board_payload["onboardingRuns"] = []
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")
            run_payload = json.loads((context_run_root / "run.json").read_text(encoding="utf-8"))
            run_payload["pipeline"]["status"] = "awaiting_approval"
            (context_run_root / "run.json").write_text(
                json.dumps(run_payload, indent=2) + "\n", encoding="utf-8"
            )

            registered = module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                context_run_root,
                run_id="partial-run",
            )

            self.assertEqual(registered.lifecycle, "onboarding")
            self.assertEqual(registered.onboarding_runs[0].lifecycle, "onboarding")
            self.assertEqual(registered.onboarding_runs[0].status, "awaiting_approval")
            self.assertEqual(registered.onboarding_runs[0].region_count, 19)
            self.assertEqual(module.load_catalog(catalog_path).boards[0].lifecycle, "onboarding")

    def test_register_run_estimates_regions_from_latest_stage_4_artifact_root(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_run_root = workspace / ".context" / "hangboard-onboarding" / "partial-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

            run_path = context_run_root / "run.json"
            run_payload = json.loads(run_path.read_text(encoding="utf-8"))
            run_payload["pipeline"]["status"] = "awaiting_approval"
            latest_stage4 = json.loads(
                json.dumps(next(stage for stage in run_payload["stages"] if stage["stage"] == 4))
            )
            latest_stage4["attempt"] = 2
            latest_stage4["artifactRoot"] = "stages/04/attempt-0002/custom"
            run_payload["stages"].append(latest_stage4)
            run_path.write_text(json.dumps(run_payload, indent=2) + "\n", encoding="utf-8")

            manifest_path = (
                context_run_root
                / "stages"
                / "04"
                / "attempt-0002"
                / "custom"
                / "stage-4-manifest.json"
            )
            manifest_path.parent.mkdir(parents=True)
            manifest_payload = json.loads(
                (
                    context_run_root
                    / "stages"
                    / "04"
                    / "attempt-0001"
                    / "stage-4-manifest.json"
                ).read_text(encoding="utf-8")
            )
            manifest_payload["regions"] = manifest_payload["regions"][:3]
            manifest_path.write_text(
                json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8"
            )

            self._make_draft_board_and_catalog(catalog_path, board_path)

            registered = module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                context_run_root,
                run_id="partial-run",
            )

            self.assertEqual(registered.lifecycle, "onboarding")
            self.assertEqual(registered.onboarding_runs[0].region_count, 3)

    def test_register_run_estimates_zero_regions_when_stage_4_manifest_is_absent(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_run_root = workspace / ".context" / "hangboard-onboarding" / "partial-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)
            (context_run_root / "stages" / "04" / "attempt-0001" / "stage-4-manifest.json").unlink()

            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["boards"][0]["lifecycle"] = "draft"
            catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            board_payload["lifecycle"] = "draft"
            board_payload["onboardingRuns"] = []
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")
            run_payload = json.loads((context_run_root / "run.json").read_text(encoding="utf-8"))
            run_payload["pipeline"]["status"] = "ready_for_next_stage"
            (context_run_root / "run.json").write_text(
                json.dumps(run_payload, indent=2) + "\n", encoding="utf-8"
            )

            registered = module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                context_run_root,
                run_id="partial-run",
            )

            self.assertEqual(registered.lifecycle, "onboarding")
            self.assertEqual(registered.onboarding_runs[0].region_count, 0)
            self.assertEqual(module.load_catalog(catalog_path).boards[0].lifecycle, "onboarding")

    def test_register_run_rejects_invalid_complete_run_manifests(self) -> None:
        module = load_module()
        mutations = (
            ("missing stage 4", lambda run: run["stages"].pop(), "missing stage 4"),
            (
                "absolute artifact root",
                lambda run: next(stage for stage in run["stages"] if stage["stage"] == 4).__setitem__(
                    "artifactRoot", "/tmp/stage-4"
                ),
                "safe relative path",
            ),
            (
                "parent artifact root",
                lambda run: next(stage for stage in run["stages"] if stage["stage"] == 4).__setitem__(
                    "artifactRoot", "stages/04/attempt-0001/.."
                ),
                "safe relative path",
            ),
        )

        for name, mutate, expected_error in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir)
                catalog_path, board_root = copy_catalog_fixture(workspace)
                board_path = board_root / "board.json"
                context_run_root = workspace / ".context" / "hangboard-onboarding" / "complete-run"
                shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)
                run_path = context_run_root / "run.json"
                run_payload = json.loads(run_path.read_text(encoding="utf-8"))
                mutate(run_payload)
                run_path.write_text(json.dumps(run_payload, indent=2) + "\n", encoding="utf-8")
                self._make_draft_board_and_catalog(catalog_path, board_path)

                with self.assertRaisesRegex(ValueError, expected_error):
                    module.register_run(
                        catalog_path,
                        "metolius.wood-grips-compact-ii",
                        context_run_root,
                        run_id="complete-run",
                    )

        for name, mutate, expected_error in (
            (
                "duplicate region ids",
                lambda manifest: manifest["regions"][1].__setitem__("id", manifest["regions"][0]["id"]),
                "duplicate stage-4 region id",
            ),
            (
                "region key mismatch",
                lambda manifest: manifest["regions"][0].__setitem__("key", "jug-right"),
                "does not match board hold",
            ),
            (
                "run and manifest region count mismatch",
                lambda manifest: manifest["regions"].pop(),
                "run region count does not match board hold count",
            ),
        ):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temp_dir:
                workspace = Path(temp_dir)
                catalog_path, board_root = copy_catalog_fixture(workspace)
                board_path = board_root / "board.json"
                context_run_root = workspace / ".context" / "hangboard-onboarding" / "complete-run"
                shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)
                manifest_path = context_run_root / "stages" / "04" / "attempt-0001" / "stage-4-manifest.json"
                manifest_payload = json.loads(manifest_path.read_text(encoding="utf-8"))
                mutate(manifest_payload)
                manifest_path.write_text(
                    json.dumps(manifest_payload, indent=2) + "\n", encoding="utf-8"
                )
                self._make_draft_board_and_catalog(catalog_path, board_path)

                with self.assertRaisesRegex(ValueError, expected_error):
                    module.register_run(
                        catalog_path,
                        "metolius.wood-grips-compact-ii",
                        context_run_root,
                        run_id="complete-run",
                    )

    @staticmethod
    def _make_draft_board_and_catalog(catalog_path: Path, board_path: Path) -> None:
        catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog_payload["boards"][0]["lifecycle"] = "draft"
        catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
        board_payload = json.loads(board_path.read_text(encoding="utf-8"))
        board_payload["lifecycle"] = "draft"
        board_payload["onboardingRuns"] = []
        board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

    def test_register_run_preserves_shipped_lifecycle(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_root = workspace / ".context"
            context_run_root = context_root / "hangboard-onboarding" / "accepted-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            board_payload["lifecycle"] = "shipped"
            board_payload["onboardingRuns"] = []
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

            registered = module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                context_run_root,
                run_id="accepted-run",
            )

            self.assertEqual(registered.lifecycle, "shipped")
            self.assertEqual([run.lifecycle for run in registered.onboarding_runs], ["approved"])

            persisted = module.load_board(board_path)
            self.assertEqual(persisted.lifecycle, "shipped")

            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            self.assertEqual(catalog_payload["boards"][0]["lifecycle"], "shipped")

    def test_register_run_rejects_reference_path_and_accepts_context_run(self) -> None:
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

            with self.assertRaisesRegex(ValueError, "inside a \\.context directory"):
                module.register_run(
                    catalog_path,
                    "metolius.wood-grips-compact-ii",
                    ACCEPTED_RUN_PATH,
                    run_id="reference-run",
                )

            context_root = workspace / ".context"
            context_run_root = context_root / "hangboard-onboarding" / "accepted-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

            module.register_run(
                catalog_path,
                "metolius.wood-grips-compact-ii",
                context_run_root,
                run_id="accepted-run",
            )

            persisted = module.load_board(board_path)
            self.assertEqual([run.id for run in persisted.onboarding_runs], ["accepted-run"])

    def test_validate_catalog_rejects_unsupported_swift_hold_enums(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            board_payload = json.loads(board_path.read_text(encoding="utf-8"))

            invalid_cases = [
                ("kind", "pinch", "unsupported Swift HoldKind"),
                ("gripType", "monoPocket", "unsupported Swift GripType"),
                ("features", ["pocket", "monoPocket"], "unsupported Swift HoldFeature"),
            ]

            for field, value, message in invalid_cases:
                mutated = json.loads(json.dumps(board_payload))
                mutated["holds"][0][field] = value
                board_path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    module.validate_catalog(catalog_path)

            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

    def test_register_run_rejects_nested_symlink_escape(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_root = workspace / ".context"
            context_run_root = context_root / "hangboard-onboarding" / "accepted-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)

            catalog_payload = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog_payload["boards"][0]["lifecycle"] = "draft"
            catalog_path.write_text(json.dumps(catalog_payload, indent=2) + "\n", encoding="utf-8")
            board_payload = json.loads(board_path.read_text(encoding="utf-8"))
            board_payload["lifecycle"] = "draft"
            board_payload["onboardingRuns"] = []
            board_path.write_text(json.dumps(board_payload, indent=2) + "\n", encoding="utf-8")

            outside_root = workspace / "outside"
            outside_root.mkdir()
            (outside_root / "payload.txt").write_text("escape", encoding="utf-8")
            (context_run_root / "escape-link").symlink_to(outside_root, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symlink"):
                module.register_run(
                    catalog_path,
                    "metolius.wood-grips-compact-ii",
                    context_run_root,
                    run_id="accepted-run",
                )

    def test_register_run_does_not_dereference_symlink_created_after_precheck(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_run_root = workspace / ".context" / "hangboard-onboarding" / "raced-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)
            self._make_draft_board_and_catalog(catalog_path, board_path)

            outside = workspace / "outside.txt"
            outside.write_text("outside payload", encoding="utf-8")
            original_check = module._require_tree_without_symlinks

            def check_then_create_raced_link(root: Path) -> None:
                original_check(root)
                (root / "raced-link").symlink_to(outside)

            with patch.object(
                module,
                "_require_tree_without_symlinks",
                side_effect=check_then_create_raced_link,
            ):
                module.register_run(
                    catalog_path,
                    "metolius.wood-grips-compact-ii",
                    context_run_root,
                    run_id="raced-run",
                )

            copied_link = board_root / "onboarding" / "runs" / "raced-run" / "raced-link"
            self.assertTrue(copied_link.is_symlink())
            self.assertEqual(copied_link.readlink(), outside)

    def test_register_run_rolls_back_files_and_copy_when_catalog_write_fails(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = Path(temp_dir)
            catalog_path, board_root = copy_catalog_fixture(workspace)
            board_path = board_root / "board.json"
            context_run_root = workspace / ".context" / "hangboard-onboarding" / "rollback-run"
            shutil.copytree(ACCEPTED_RUN_PATH, context_run_root)
            self._make_draft_board_and_catalog(catalog_path, board_path)
            previous_board = board_path.read_bytes()
            previous_catalog = catalog_path.read_bytes()

            real_atomic_write = module._atomic_write_text

            def fail_catalog_write(path: Path, payload: str) -> None:
                if Path(path) == catalog_path:
                    raise OSError("simulated catalog write failure")
                real_atomic_write(path, payload)

            with patch.object(module, "_atomic_write_text", side_effect=fail_catalog_write):
                with self.assertRaisesRegex(OSError, "simulated catalog write failure"):
                    module.register_run(
                        catalog_path,
                        "metolius.wood-grips-compact-ii",
                        context_run_root,
                        run_id="rollback-run",
                    )

            self.assertEqual(board_path.read_bytes(), previous_board)
            self.assertEqual(catalog_path.read_bytes(), previous_catalog)
            self.assertFalse(
                (board_root / "onboarding" / "runs" / "rollback-run").exists()
            )

    def test_stage4_manifest_path_reports_missing_run_manifest(self) -> None:
        module = load_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            run_root = Path(temp_dir) / "missing-run"
            with self.assertRaisesRegex(ValueError, r"run\.json does not exist"):
                module._stage4_manifest_path(run_root, fallback_to_default=False)


def copy_catalog_fixture(destination_root: Path) -> tuple[Path, Path]:
    hangboards_root = destination_root / "Hangboards"
    board_root = hangboards_root / "metolius-wood-grips-compact-ii"
    board_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CATALOG_PATH, hangboards_root / "catalog.json")
    shutil.copy2(BOARD_PATH, board_root / "board.json")
    return hangboards_root / "catalog.json", board_root


if __name__ == "__main__":
    unittest.main()
