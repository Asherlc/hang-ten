"""Pure-Python characterization tests for shipped model packages."""

import hashlib
import json
from pathlib import Path

import pytest

from model_characterization import assert_baseline_matches, capture_model_baseline


ROOT = Path(__file__).resolve().parents[2]
BASELINES = {
    "beastmaker-1000": {
        "modelSHA256": "19fb5895575792fb69e82aa3c8a04fa14a6bd40a8a97f486bc16be014e546f3d",
        "descriptorSHA256": "ee095c463804312cbd6ed08f5113019793b934ab6806a6fb343be939ff8a68d3",
        "logicalHoldIDs": ["jug-left", "jug-right", "sloper-35-left", "sloper-35-right", "sloper-center", "pocket-top-outer-left", "pocket-top-outer-right", "pocket-top-left", "pocket-top-right", "pocket-middle-outer-left", "pocket-middle-mid-left", "pocket-middle-inner-left", "pocket-middle-center", "pocket-middle-inner-right", "pocket-middle-mid-right", "pocket-middle-outer-right", "pocket-bottom-outer-left", "pocket-bottom-mid-left", "pocket-bottom-inner-left", "pocket-bottom-inner-right", "pocket-bottom-mid-right", "pocket-bottom-outer-right"],
    },
    "metolius-wood-grips-compact-ii": {
        "modelSHA256": "addf2cd2ddd34f18f311ccc1413ca94644df0d2f3d56020b68edf25625bc664a",
        "descriptorSHA256": "a652b1a184ec15432126502514d11db2b02768df7c3c0a892c62031f381c0c7f",
        "logicalHoldIDs": ["jug-left", "sloper-flat-left", "sloper-round-center", "sloper-flat-right", "jug-right", "edge-29-left", "pocket-29-three-left", "pocket-29-two-left", "pocket-29-four-center", "pocket-29-two-right", "pocket-29-three-right", "edge-29-right", "edge-19-left", "pocket-19-three-left", "pocket-19-three-right", "pocket-19-two-left", "pocket-19-two-right", "pocket-19-four-center", "edge-19-right"],
    },
    "tension-flash-board": {
        "modelSHA256": "ea4d014f1af63300561c8ad4ec6e78710ebc519c0811630502aba4e33d62c25b",
        "descriptorSHA256": "b7a31d182e1f8a07b27f0fa2157f9733969d1e0ff55aa8cc78f744e028cf2c58",
        "logicalHoldIDs": ["three-edge-left", "three-edge-center", "three-edge-right", "two-edge-left", "two-edge-right", "small-crimp-left", "small-crimp-right"],
    },
}


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


@pytest.mark.parametrize("slug", BASELINES)
def test_shipped_packages_match_fixed_baseline(slug):
    package = ROOT / "Hangboards" / slug
    baseline = capture_model_baseline(package, package / "board.json")
    expected = dict(BASELINES[slug], assets=["assets/primary.model.json", "assets/primary.usdz"],
                    descriptor=json.loads((ROOT / "Tools/HangboardModels/baselines" / f"{slug}.model.json").read_text()))
    assert_baseline_matches(baseline, expected)
