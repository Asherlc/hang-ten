"""Runtime physics and its authoring graph are covered by exact delivery identity."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_native_package_locks_physics_authoring_and_generated_input(tmp_path):
    spec = importlib.util.spec_from_file_location("delivery", ROOT / "scripts/verify-model-delivery.py")
    delivery = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(delivery)
    package = tmp_path / "Hangboards/example"
    (package / "assets").mkdir(parents=True)
    for name in ["example.FCStd", "rope-physics.json", "assets/primary.model.json", "assets/primary.physics.json"]:
        (package / name).write_text("fixture")
    assert "rope-physics.json" in delivery.package_suffixes(tmp_path, "example")
    assert "assets/primary.physics.json" in delivery.package_suffixes(tmp_path, "example")
    original = delivery.checksum_manifest(tmp_path, ["example"])
    (package / "rope-physics.json").write_text("changed topology")
    assert delivery.checksum_manifest(tmp_path, ["example"]) != original
