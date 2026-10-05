"""A release must receive exactly the catalog compiled for the tested revision."""
import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import prepare_assets
import runtime_asset_catalog


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    repository = tmp_path / "repository"
    hangboards = repository / "Hangboards"
    hangboards.mkdir(parents=True)
    monkeypatch.setattr(prepare_assets, "REPOSITORY", repository)
    monkeypatch.setattr(prepare_assets, "source_targets", lambda source: {"primary": ("primary.usdz", "primary.model.json")})
    monkeypatch.setattr(prepare_assets.cad_source, "load_rope_physics_authoring", lambda source: None)
    monkeypatch.setattr(prepare_assets.cad_source, "load_suspension_authoring", lambda source: None)
    reports = repository / ".context/reports"
    reports.mkdir(parents=True)
    fingerprint = prepare_assets.compiler_fingerprint()
    for package in ["first", "second"]:
        (hangboards / f"{package}.FCStd").write_bytes(package.encode())
        assets = hangboards / package / "assets"
        assets.mkdir(parents=True)
        (assets / "primary.usdz").write_bytes(b"model")
        (assets / "primary.model.json").write_text(json.dumps({"modelSHA256": hashlib.sha256(b"model").hexdigest()}))
    for index in range(2):
        packages = prepare_assets.shard_packages(["first", "second"], index, 2)
        (reports / f"shard-{index}.json").write_text(json.dumps({
            "schemaVersion": 1, "revision": "tested-commit", "compilerSHA256": fingerprint,
            "shardIndex": index, "shardCount": 2, "failures": [],
            "prepared": [prepare_assets.validate_assets(package, hangboards / package / "assets")[0] for package in packages],
        }))
    for relative in ["HangTen/Resources/GripHand/hand-mesh.json", "HangTen/Resources/PlanLibrary.json"]:
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    manifest = repository / ".context/catalog.json"
    return repository, reports, manifest


def test_complete_shards_produce_a_verifiable_release_catalog(catalog):
    _, reports, manifest = catalog
    runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
    runtime_asset_catalog.validate_catalog(manifest, "tested-commit")
    recorded = json.loads(manifest.read_text())
    assert recorded["sources"] == {
        "Hangboards/first.FCStd": hashlib.sha256(b"first").hexdigest(),
        "Hangboards/second.FCStd": hashlib.sha256(b"second").hexdigest(),
        "HangTen/Resources/PlanLibrary.json": hashlib.sha256(b"{}").hexdigest(),
    }
    assert set(recorded["files"]) == {
        "Hangboards/first/assets/primary.usdz",
        "Hangboards/first/assets/primary.model.json",
        "Hangboards/second/assets/primary.usdz",
        "Hangboards/second/assets/primary.model.json",
        "HangTen/Resources/GripHand/hand-mesh.json",
    }


def test_catalog_rejects_retained_plan_in_generated_file_inventory(catalog):
    _, reports, manifest = catalog
    runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
    recorded = json.loads(manifest.read_text())
    recorded["files"]["HangTen/Resources/PlanLibrary.json"] = hashlib.sha256(b"{}").hexdigest()
    manifest.write_text(json.dumps(recorded))
    with pytest.raises(ValueError, match="source or output hashes"):
        runtime_asset_catalog.validate_catalog(manifest, "tested-commit")


@pytest.mark.parametrize("operation", ["create", "validate"])
@pytest.mark.parametrize("damage", ["missing", "symlink"])
def test_catalog_requires_a_regular_retained_plan_source(catalog, operation, damage):
    repository, reports, manifest = catalog
    if operation == "validate":
        runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
        runtime_asset_catalog.validate_catalog(manifest, "tested-commit")
    source = repository / "HangTen/Resources/PlanLibrary.json"
    source.unlink()
    if damage == "symlink":
        replacement = repository / ".context/plan-copy.json"
        replacement.write_text("{}")
        source.symlink_to(replacement)
    with pytest.raises(ValueError):
        if operation == "create":
            runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
        else:
            runtime_asset_catalog.validate_catalog(manifest, "tested-commit")


@pytest.mark.parametrize("damage", ["missing", "duplicate", "overlap", "wrong_revision", "wrong_compiler", "failed", "wrong_source"])
def test_incomplete_or_mixed_shards_cannot_publish_a_catalog(catalog, damage):
    _, reports, manifest = catalog
    path = reports / "shard-0.json"
    if damage == "missing": path.unlink()
    else:
        report = json.loads(path.read_text())
        if damage == "duplicate": report["prepared"].append(dict(report["prepared"][0]))
        elif damage == "overlap":
            path = reports / "shard-1.json"
            overlapping = report["prepared"][0]
            report = json.loads(path.read_text())
            report["prepared"].append(overlapping)
        elif damage == "wrong_revision": report["revision"] = "other-commit"
        elif damage == "wrong_compiler": report["compilerSHA256"] = "old-compiler"
        elif damage == "failed": report["failures"] = ["native build failed"]
        elif damage == "wrong_source":
            # Alter whichever shard contains a board; empty shards are valid.
            path = next(path for path in reports.glob("*.json") if json.loads(path.read_text())["prepared"])
            report = json.loads(path.read_text())
            report["prepared"][0]["sourceSHA256"] = "old-source"
        path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
    assert not manifest.exists()


@pytest.mark.parametrize("damage", ["asset", "hand", "plan", "cad", "extra_board", "wrong_revision"])
def test_release_rejects_changed_sources_or_delivered_bytes(catalog, damage):
    repository, reports, manifest = catalog
    runtime_asset_catalog.create_catalog(manifest, reports, 2, "tested-commit")
    runtime_asset_catalog.validate_catalog(manifest, "tested-commit")
    if damage == "asset": (repository / "Hangboards/first/assets/primary.usdz").write_bytes(b"modified")
    elif damage == "hand": (repository / "HangTen/Resources/GripHand/hand-mesh.json").write_text("changed")
    elif damage == "plan": (repository / "HangTen/Resources/PlanLibrary.json").write_text('{"changed":true}')
    elif damage == "cad": (repository / "Hangboards/first.FCStd").write_bytes(b"modified source")
    elif damage == "extra_board":
        path = repository / "Hangboards/deleted/assets/primary.usdz"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"stale board")
    with pytest.raises((ValueError, RuntimeError)):
        runtime_asset_catalog.validate_catalog(manifest, "other-commit" if damage == "wrong_revision" else "tested-commit")
