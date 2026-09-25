"""Zlagboard exact-revision migration and shipping-boundary regressions."""
import hashlib
import json
from pathlib import Path

import pytest
from hangboard_packages.board_catalog import load_board_package
from test_board_package_staging import load_staging_module, configure_xcode_destination, odr_staging_root

ROOT = Path(__file__).resolve().parents[3]
AUDIT = ROOT / "docs/source-audits/2026-09-20-hangboards-batch-05-migration"


@pytest.mark.parametrize("slug,count,height", [("zlagboard-evo", 21, .120), ("zlagboard-pro", 28, .152)])
def test_exact_revision_model_inventory_and_geometry(slug, count, height):
    package = ROOT / "Hangboards" / slug
    board = json.loads((package / "board.json").read_text())
    assert board["presentations"][0]["media"]["type"] == "model"
    assert "dimensions" not in board  # no manufacturer board-only measurements
    assert not list(package.rglob("*.png"))
    assert "contactGeometry" not in json.dumps(board)
    descriptor = json.loads((package / "assets/primary.model.json").read_text())
    assert descriptor["modelSHA256"] == hashlib.sha256((package / "assets/primary.usdz").read_bytes()).hexdigest()
    assert set(descriptor["contacts"]) == {c["id"] for c in board["contacts"]}
    assert len(board["contacts"]) == count
    bounds = descriptor["modelBounds"]
    assert bounds["max"][1] - bounds["min"][1] == pytest.approx(height, abs=.004)
    assert bounds["max"][2] - bounds["min"][2] < .06
    # Descriptor centers are normalized +Y-up, unlike raster screen coordinates.
    contacts = descriptor["contacts"]
    assert contacts["edge-30-left"]["center"][0] < contacts["edge-35-center"]["center"][0] < contacts["edge-30-right"]["center"][0]
    assert contacts["edge-30-left"]["center"][1] > contacts["edge-20-left"]["center"][1]
    if slug == "zlagboard-pro":
        assert board["id"] == "zlagboard.pro"
        assert board["name"] == "Zlagboard.Pro 2.0"
        assert contacts["edge-20-left"]["center"][1] > contacts["edge-incut-15-left"]["center"][1]
    load_board_package(package)


def test_approved_evidence_is_hash_bound_and_separate_from_model_acceptance():
    approval = json.loads((AUDIT / "human-approval.json").read_text())
    assert approval["reviewedAt"] == "2026-09-20"
    assert approval["approved"] is True
    assert approval["modelAcceptance"] is False
    assert len(approval["originals"]) == 24
    assert len(approval["reviewRenders"]) == 12
    assert len(approval["cordExclusions"]) == 6
    for item in approval["originals"] + approval["reviewRenders"]:
        assert hashlib.sha256((AUDIT / item["path"]).read_bytes()).hexdigest() == item["sha256"]


def test_zlagboard_staging_keeps_metadata_bundled_and_exact_usdz_in_odr(tmp_path, monkeypatch):
    destination = tmp_path / "build/HangTen.app/Hangboards"
    configure_xcode_destination(monkeypatch, destination)
    load_staging_module().stage_board_packages(ROOT, destination)
    for slug in ("zlagboard-evo", "zlagboard-pro"):
        source = ROOT / "Hangboards" / slug
        assert not (destination / slug / "assets/primary.usdz").exists()
        assert (destination / slug / "assets/primary.model.json").read_bytes() == (source / "assets/primary.model.json").read_bytes()
        assert (destination / slug / "board.json").read_bytes() == (source / "board.json").read_bytes()
        assert (odr_staging_root(destination) / slug / "Hangboards" / slug / "assets/primary.usdz").read_bytes() == (source / "assets/primary.usdz").read_bytes()
