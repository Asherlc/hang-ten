"""Exercise report bookkeeping without importing Blender or rendering assets."""
import argparse
import ast
from collections.abc import Mapping
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
BEASTMAKER_IDS = frozenset(
    hold["id"]
    for hold in json.loads(
        (ROOT / "Hangboards/beastmaker-1000/board.json").read_text(encoding="utf-8")
    )["holds"]
)


def statements(filename):
    return ast.parse((TOOLS / filename).read_text()).body


def execute(nodes, namespace):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<model-tool>", "exec"), namespace)


def beastmaker_report_functions():
    tree = ast.parse((TOOLS / "verify_beastmaker_1000.py").read_text())
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"load_report", "verify_report"}
    ]
    namespace = {"Path": Path, "Mapping": Mapping, "json": json}
    execute(nodes, namespace)
    return (
        namespace.get("load_report", lambda path: json.loads(Path(path).read_text())),
        namespace.get("verify_report", lambda report, *, expected_ids: report),
    )


def compact_package_paths():
    tree = ast.parse((TOOLS / "verify_wood_grips_compact_ii.py").read_text())
    nodes = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "package_paths"
    ]
    namespace = {"Path": Path}
    execute(nodes, namespace)
    return namespace.get(
        "package_paths",
        lambda package: (
            Path(package) / "wood-grips-compact-ii.usdz",
            Path(package) / "export-verification.json",
        ),
    )


class ModelReportTests(unittest.TestCase):
    def test_beastmaker_report_requires_22_hold_ids_and_no_hardware(self):
        load_report, verify_report = beastmaker_report_functions()
        fixture = {
            "hold_ids_preserved": 22,
            "hardware_mesh_count": 0,
        }
        with tempfile.TemporaryDirectory(
            prefix=f"{ROOT.name}-beastmaker-report-", dir=ROOT / ".context"
        ) as directory:
            fixture_path = Path(directory) / "fixture-report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            report = verify_report(load_report(fixture_path), expected_ids=BEASTMAKER_IDS)

        self.assertEqual(len(BEASTMAKER_IDS), 22)
        self.assertEqual(report["hold_ids_preserved"], 22)
        self.assertEqual(report["hardware_mesh_count"], 0)

    def test_beastmaker_report_rejects_hardware_meshes(self):
        _, verify_report = beastmaker_report_functions()
        with self.assertRaises(ValueError):
            verify_report(
                {"hold_ids_preserved": 22, "hardware_mesh_count": 1},
                expected_ids=BEASTMAKER_IDS,
            )

    def test_compact_verifier_uses_compiler_package_assets(self):
        paths = compact_package_paths()
        with tempfile.TemporaryDirectory(
            prefix=f"{ROOT.name}-compact-package-", dir=ROOT / ".context"
        ) as directory:
            package = Path(directory)
            assets = package / "assets"
            assets.mkdir()
            (assets / "primary.usdz").write_bytes(b"fixture USDZ")
            (assets / "primary.model.json").write_text("{}", encoding="utf-8")
            model, descriptor = paths(package)

        self.assertEqual(model, assets / "primary.usdz")
        self.assertEqual(descriptor, assets / "primary.model.json")

    def test_default_outputs_follow_checkout_name(self):
        for filename in ("wood_grips_compact_ii.py", "verify_wood_grips_compact_ii.py",
                         "render_hold_highlights.py"):
            with self.subTest(tool=filename):
                nodes = statements(filename)
                start = next(i for i, node in enumerate(nodes)
                             if isinstance(node, ast.Assign) and node.targets[0].id == "ROOT")
                end = next(i for i, node in enumerate(nodes)
                           if isinstance(node, ast.Assign) and node.targets[0].id == "args")
                namespace = {"Path": Path, "argparse": argparse,
                             "__file__": f"/tmp/another-checkout/Tools/HangboardModels/{filename}"}
                execute(nodes[start:end], namespace)
                args = namespace["parser"].parse_args([])
                expected = Path("/tmp/another-checkout/.context/another-checkout-wood-grips-compact-ii").resolve()
                self.assertEqual(args.output, expected / "highlights" if hasattr(args, "blend") else expected)
                if hasattr(args, "blend"):
                    self.assertEqual(args.blend, expected / "wood-grips-compact-ii.blend")

    def test_preserved_hold_count_measures_matching_ids(self):
        tree = ast.parse((TOOLS / "verify_wood_grips_compact_ii.py").read_text())
        expression = next(value for node in ast.walk(tree) if isinstance(node, ast.Dict)
                          for key, value in zip(node.keys, node.values)
                          if isinstance(key, ast.Constant) and key.value == "hold_ids_preserved")
        count = eval(compile(ast.Expression(expression), "<hold-count>", "eval"),
                     {"expected": {"left", "right"}, "ids": {"left", "right", "body"}})
        self.assertEqual(count, 2)

    def test_compact_source_tags_body_and_exact_hold_id(self):
        """The compiler input must carry roles, never infer them from node names."""
        tree = ast.parse((TOOLS / "wood_grips_compact_ii.py").read_text())
        function = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "tag_model_piece"
            ),
            None,
        )
        self.assertIsNotNone(function, "Compact generator must tag every compiler source mesh")
        namespace = {}
        execute([function], namespace)

        class Piece(dict):
            def __init__(self, name):
                super().__init__()
                self.name = name

        tag = namespace["tag_model_piece"]
        body = Piece("wood-body")
        hold = Piece("sloper-round-center")
        tag(body, frozenset({"sloper-round-center"}))
        tag(hold, frozenset({"sloper-round-center"}))

        self.assertEqual(body, {"role": "body"})
        self.assertEqual(
            hold,
            {"role": "hold", "hold_id": "sloper-round-center"},
        )

    def test_compact_compiler_source_discards_render_only_objects(self):
        """Catches saving the review wall, camera, or lamps into compiler input."""
        tree = ast.parse((TOOLS / "wood_grips_compact_ii.py").read_text())
        function = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.FunctionDef)
                and node.name == "discard_render_only_scene_objects"
            ),
            None,
        )
        self.assertIsNotNone(
            function,
            "Compact generator must remove review-only objects before saving compiler source",
        )
        namespace = {}
        execute([function], namespace)
        body, hold = object(), object()
        review_wall, review_camera, review_lamp = object(), object(), object()
        removed = []
        namespace["discard_render_only_scene_objects"](
            (body, hold, review_wall, review_camera, review_lamp),
            (body, hold),
            removed.append,
        )
        self.assertEqual(removed, [review_wall, review_camera, review_lamp])

    def overview_report(self, previous, missing=()):
        context = ROOT / ".context"
        context.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=f"{ROOT.name}-report-test-", dir=context) as directory:
            out = Path(directory)
            if previous is not None:
                (out / "highlight-report.json").write_text(json.dumps(previous))
            for filename in ("left.png", "right.png", "sheet.png"):
                if filename not in missing:
                    (out / filename).write_bytes(b"fixture image evidence")
            nodes = statements("render_hold_highlights.py")
            start = next(i for i, node in enumerate(nodes)
                         if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                         and node.targets[0].id == "report")
            # Run the real report-writing tail. Any rendering would need bpy,
            # which is intentionally unavailable in this overview-only fixture.
            namespace = {"ROOT": ROOT, "source": out / "model.blend", "source_sha": "current",
                         "holds": [{"id": "left"}, {"id": "right"}], "entries": [],
                         "out": out, "json": json, "args": SimpleNamespace(overview_only=True),
                         "print": lambda *args, **kwargs: None}
            execute(nodes[start:], namespace)
            return json.loads((out / "highlight-report.json").read_text())

    def previous_report(self, sha="current"):
        return {"source_sha256": sha, "individual_holds": [
            {"number": 1, "id": "left", "name": "Left", "image": "left.png"},
            {"number": 2, "id": "right", "name": "Right", "image": "right.png"}],
            "contact_sheet": "sheet.png"}

    def test_overview_preserves_existing_evidence_for_same_source(self):
        previous = self.previous_report()
        report = self.overview_report(previous)
        self.assertEqual(report["individual_holds"], previous["individual_holds"])
        self.assertEqual(report["contact_sheet"], "sheet.png")

    def test_overview_invalidates_evidence_for_changed_source(self):
        report = self.overview_report(self.previous_report("old"))
        self.assertEqual(report["source_sha256"], "current")
        self.assertEqual(report["individual_holds"], [])
        self.assertNotIn("contact_sheet", report)

    def test_overview_omits_missing_evidence(self):
        report = self.overview_report(self.previous_report(), missing=("right.png", "sheet.png"))
        self.assertEqual([entry["id"] for entry in report["individual_holds"]], ["left"])
        self.assertNotIn("contact_sheet", report)

    def test_overview_without_previous_report(self):
        report = self.overview_report(None)
        self.assertEqual(report["individual_holds"], [])
        self.assertNotIn("contact_sheet", report)


if __name__ == "__main__":
    unittest.main()
