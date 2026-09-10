"""Pure-Python characterization tests for shipped model packages."""

import hashlib
import json
from pathlib import Path

import pytest

from model_characterization import assert_baseline_matches, capture_model_baseline


ROOT = Path(__file__).resolve().parents[2]


def _fixture_package(tmp_path: Path) -> tuple[Path, Path]:
    package = tmp_path / "package"
    assets = package / "assets"
    assets.mkdir(parents=True)
    model = b"fixture usdz"
    descriptor = {"schemaVersion": 1, "nodes": [], "holds": {}}
    (assets / "primary.usdz").write_bytes(model)
    descriptor_path = assets / "primary.model.json"
    descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
    board = tmp_path / "board.json"
    board.write_text(json.dumps({"holds": [{"id": "a"}, {"id": "b"}]}), encoding="utf-8")
    return package, board


def test_capture_model_baseline_records_exact_two_asset_tree_and_hashes(tmp_path):
    package, board_json = _fixture_package(tmp_path)
    descriptor = package / "assets" / "primary.model.json"
    baseline = capture_model_baseline(package, board_json)
    assert baseline["assets"] == ["assets/primary.model.json", "assets/primary.usdz"]
    assert baseline["logicalHoldIDs"] == ["a", "b"]
    assert baseline["descriptorSHA256"] == hashlib.sha256(descriptor.read_bytes()).hexdigest()


def test_baseline_comparison_rejects_reordered_inventory():
    with pytest.raises(ValueError, match="logicalHoldIDs"):
        assert_baseline_matches({"logicalHoldIDs": ["b", "a"]}, {"logicalHoldIDs": ["a", "b"]})


@pytest.mark.parametrize("slug", ["beastmaker-1000", "metolius-wood-grips-compact-ii", "tension-flash-board"])
def test_shipped_packages_capture_without_blender(slug):
    package = ROOT / "Hangboards" / slug
    baseline = capture_model_baseline(package, package / "board.json")
    assert baseline["assets"] == ["assets/primary.model.json", "assets/primary.usdz"]
    assert baseline["logicalHoldIDs"]
    assert baseline["descriptor"]["modelSHA256"] == baseline["modelSHA256"]
