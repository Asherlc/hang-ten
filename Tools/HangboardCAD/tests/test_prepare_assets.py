"""Runtime compilation must work without any previously checked-in exports."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_assets


@pytest.fixture
def compiler(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    package = repository / "Hangboards" / "fixture"
    package.mkdir(parents=True)
    (package.parent / "fixture.FCStd").write_bytes(b"authored source")
    monkeypatch.setattr(prepare_assets, "REPOSITORY", repository)
    authoring = {"physics": None, "suspension": None}
    monkeypatch.setattr(prepare_assets.cad_source, "load_rope_physics_authoring", lambda source: authoring["physics"], raising=False)
    monkeypatch.setattr(prepare_assets.cad_source, "load_suspension_authoring", lambda source: authoring["suspension"], raising=False)
    targets = {"primary": ("primary.usdz", "primary.model.json")}
    monkeypatch.setattr(prepare_assets, "source_targets", lambda source: targets)

    def build(package, destination, freecad, extra_path, presentation_id=None):
        destination.mkdir(parents=True, exist_ok=True)
        asset_name, descriptor_name = targets[presentation_id or "primary"]
        data = asset_name.encode()
        (destination / asset_name).write_bytes(data)
        (destination / descriptor_name).write_text(json.dumps({
            "modelSHA256": hashlib.sha256(data).hexdigest(),
        }))
        if authoring["physics"] is not None:
            (destination / "primary.physics.json").write_text(json.dumps({
                "modelSHA256": hashlib.sha256(data).hexdigest(),
            }))

    monkeypatch.setattr(prepare_assets, "_run_build", build)
    return package, targets, build, authoring


def test_compiles_without_any_committed_descriptor(compiler, tmp_path):
    package, _, _, _ = compiler
    out = tmp_path / "compiled"
    report = prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert report["package"] == "fixture"
    assert (out / "fixture/assets/primary.usdz").read_bytes() == b"primary.usdz"
    assert (out / "fixture/assets/primary.model.json").is_file()
    assert not (package / "assets").exists()


def test_carries_all_configurations(compiler, tmp_path):
    package, targets, _, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert {p.name for p in (out / "fixture/assets").iterdir()} == {
        "primary.usdz", "primary.model.json",
        "depth-10mm.usdz", "depth-10mm.model.json",
    }


def test_carries_matching_physics_descriptor(compiler, tmp_path):
    package, _, _, authoring = compiler
    authoring["physics"] = {}
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    physics = json.loads((out / "fixture/assets/primary.physics.json").read_text())
    assert physics["modelSHA256"] == hashlib.sha256(b"primary.usdz").hexdigest()


def test_rejects_mismatched_compiled_hash_before_publication(compiler, tmp_path, monkeypatch):
    package, _, build, _ = compiler

    def corrupt(*args):
        build(*args)
        (args[1] / "primary.model.json").write_text('{"modelSHA256":"wrong"}')

    monkeypatch.setattr(prepare_assets, "_run_build", corrupt)
    out = tmp_path / "compiled"
    with pytest.raises(RuntimeError, match="does not hash"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert not (out / "fixture/assets").exists()


def test_failed_configuration_leaves_previous_complete_outputs(compiler, tmp_path, monkeypatch):
    package, targets, build, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    existing = out / "fixture/assets/primary.usdz"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"previous")

    def fail(package, destination, freecad, extra_path, presentation_id=None):
        if presentation_id == "depth-10mm":
            raise RuntimeError("configuration failed")
        build(package, destination, freecad, extra_path, presentation_id)

    monkeypatch.setattr(prepare_assets, "_run_build", fail)
    with pytest.raises(RuntimeError, match="configuration failed"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert existing.read_bytes() == b"previous"


def test_removed_configuration_is_pruned_after_successful_build(compiler, tmp_path):
    package, targets, _, _ = compiler
    targets["depth-10mm"] = ("depth-10mm.usdz", "depth-10mm.model.json")
    out = tmp_path / "compiled"
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    authored = out / "fixture/assets/source-evidence.txt"
    authored.write_text("retain authored evidence")
    del targets["depth-10mm"]
    prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert {p.name for p in authored.parent.iterdir()} == {
        "primary.usdz", "primary.model.json", "source-evidence.txt",
    }
    assert authored.read_text() == "retain authored evidence"


def test_suspension_failure_preserves_previous_complete_package(compiler, tmp_path, monkeypatch):
    package, _, _, authoring = compiler
    authoring["suspension"] = {}
    out = tmp_path / "compiled"
    existing = out / "fixture/assets/primary.usdz"
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"previous")

    def fail(*args):
        raise RuntimeError("native cord route could not be solved")

    monkeypatch.setattr(prepare_assets, "_run_suspension", fail, raising=False)
    with pytest.raises(RuntimeError, match="cord route"):
        prepare_assets.prepare(package.name, out, Path("freecad"), "")
    assert existing.read_bytes() == b"previous"
