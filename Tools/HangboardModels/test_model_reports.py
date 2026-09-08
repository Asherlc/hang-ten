"""Exercise report bookkeeping without importing Blender or rendering assets."""
import argparse
import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest


TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]


def statements(filename):
    return ast.parse((TOOLS / filename).read_text()).body


def execute(nodes, namespace):
    exec(compile(ast.Module(body=nodes, type_ignores=[]), "<model-tool>", "exec"), namespace)


class ModelReportTests(unittest.TestCase):
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
