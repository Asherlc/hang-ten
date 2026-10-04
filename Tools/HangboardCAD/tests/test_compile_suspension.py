"""A rope build uses the authored native body, never a renderer shell or another pose."""
import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def compiler():
    assert importlib.util.find_spec("compile_suspension") is not None, "native suspension compiler is missing"
    return importlib.import_module("compile_suspension")


def feature(name, *, node="body", solids=1, presentation=""):
    return SimpleNamespace(Name=name, NodeID=node, NodeRole="body",
                           HangTenPresentationID=presentation,
                           Shape=SimpleNamespace(Solids=[object()] * solids, Volume=100 if solids else 0,
                                                 isValid=lambda: True))


def document(*objects):
    return SimpleNamespace(Objects=objects, HangTenPresentationID="primary", getObject=lambda name: next(
        (obj for obj in objects if obj.Name == name), None))


def test_imports_from_the_native_scratch_wrapper(tmp_path):
    script = Path(__file__).resolve().parents[1] / "compile_suspension.py"
    result = subprocess.run(
        [sys.executable, "-I", "-c", f"import runpy; runpy.run_path({str(script)!r}, run_name='compiler_import')"],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_generated_artifact_retains_instance_translation_precision(tmp_path, monkeypatch):
    module = compiler()
    payload = {"translation": [module.cad_source.LexemeFloat(value)
                               for value in ("-0.120000000", "-0.350000000", "0.000000000")]}
    monkeypatch.setattr(module, "compile_suspension", lambda source, assets: payload)
    assets = tmp_path / "assets"
    assert module.main(["--source", str(tmp_path / "fixture.FCStd"), "--assets", str(assets)]) == 0
    saved = module.cad_source.loads((assets / "suspension.json").read_text())
    assert [coordinate.lexeme for coordinate in saved["translation"]] == [
        "-0.120000000", "-0.350000000", "0.000000000",
    ]


def test_selects_only_the_current_presentation_solid():
    previous = feature("Depth18", presentation="depth-18")
    current = feature("Depth10", presentation="depth-10")
    result = compiler().selected_body(document(previous, current),
                                     {"bodyNodeID": "body"}, "depth-10", {})
    assert result is current


def test_untagged_body_belongs_only_to_the_document_default_presentation():
    primary = feature("Primary")
    alternate = feature("Alternate", presentation="alternate")
    doc = document(primary, alternate)
    assert compiler().selected_body(doc, {"bodyNodeID": "body"}, "primary", {}) is primary
    assert compiler().selected_body(doc, {"bodyNodeID": "body"}, "alternate", {}) is alternate


def test_connected_cord_mouths_can_bind_to_attachment_nodes():
    body = feature("Body", node="ring_body")
    mouth = feature("RoofExit", node="roof_exit")
    mouth.NodeRole = "attachment"
    setup = {"passages": {"left": [{"id": "mouth", "nodeID": "roof_exit"}], "right": []}}
    assert compiler().selected_body(document(body, mouth), setup, "primary", {}) is body


def test_shell_requires_an_explicit_native_collision_feature():
    surface = feature("Surface", solids=0)
    solid = feature("FinalSolid", node=None)
    doc = document(surface, solid)
    with pytest.raises(ValueError, match="one.*solid"):
        compiler().selected_body(doc, {"bodyNodeID": "body"}, "primary", {})
    assert compiler().selected_body(doc, {"bodyNodeID": "body"}, "primary",
                                    {"collisionFeature": "FinalSolid"}) is solid


def test_rejects_a_missing_declared_collision_feature():
    with pytest.raises(ValueError, match="collision feature"):
        compiler().selected_body(document(feature("Body")), {"bodyNodeID": "body"}, "primary",
                                 {"collisionFeature": "Missing"})
