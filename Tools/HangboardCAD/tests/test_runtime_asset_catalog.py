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
    if damage == "asset": (repository / "Hangboards/first/assets/primary.usdz").write_bytes(b"modified")
    elif damage == "hand": (repository / "HangTen/Resources/GripHand/hand-mesh.json").write_text("changed")
    elif damage == "plan": (repository / "HangTen/Resources/PlanLibrary.json").write_text("changed")
    elif damage == "cad": (repository / "Hangboards/first.FCStd").write_bytes(b"modified source")
    elif damage == "extra_board":
        path = repository / "Hangboards/deleted/assets/primary.usdz"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"stale board")
    with pytest.raises((ValueError, RuntimeError)):
        runtime_asset_catalog.validate_catalog(manifest, "other-commit" if damage == "wrong_revision" else "tested-commit")


def producer_jobs(*attempts):
    return [{"run_id": 42, "name": "Compile runtime assets / Assemble runtime catalog",
             "run_attempt": attempt, "status": "completed", "conclusion": "success"}
            for attempt in attempts]


def test_delayed_release_cannot_receive_a_later_untested_retry():
    artifacts = [
        {"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False},
        {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    assert runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=producer_jobs(1, 2)) == 101


def test_test_only_retry_uses_the_latest_retained_catalog_producer():
    artifacts = [
        {"id": 104, "name": "hang-ten-board-assets-42-4", "expired": False},
        {"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False},
        {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    assert runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2, 4)) == 102


@pytest.mark.parametrize("damage", ["expired", "duplicate", "missing_id", "invalid_id"])
def test_release_cannot_fall_back_from_an_unusable_latest_catalog(damage):
    latest = {"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}, latest]
    if damage == "expired": latest["expired"] = True
    elif damage == "duplicate": artifacts.append({**latest, "id": 103})
    elif damage == "missing_id": latest.pop("id")
    elif damage == "invalid_id": latest["id"] = True
    with pytest.raises(ValueError):
        runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2))


def test_catalog_selection_requires_the_exact_owner_run_and_producer_attempt():
    artifacts = [
        {"id": 1, "name": "other-board-assets-42-1", "expired": False},
        {"id": 2, "name": "hang-ten-board-assets-43-1", "expired": False},
        {"id": 3, "name": "hang-ten-board-assets-42", "expired": False},
        {"id": 4, "name": "hang-ten-board-assets-42-zero", "expired": False},
        {"id": 5, "name": "hang-ten-board-assets-42-0", "expired": False},
        {"id": 6, "name": "hang-ten-board-assets-42-2", "expired": False},
    ]
    with pytest.raises(ValueError, match="no catalog"):
        runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=producer_jobs(1))


def test_deleted_latest_catalog_cannot_select_an_older_producer():
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="no catalog"):
        runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 3, jobs=producer_jobs(1, 2))


@pytest.mark.parametrize("damage", ["failed", "running", "other_run", "other_job", "future", "missing"])
def test_catalog_selection_requires_a_successful_producer_in_the_tested_run(damage):
    jobs = producer_jobs(1)
    if damage == "failed": jobs[0]["conclusion"] = "failure"
    elif damage == "running": jobs[0]["status"] = "in_progress"
    elif damage == "other_run": jobs[0]["run_id"] = 43
    elif damage == "other_job": jobs[0]["name"] = "Compile board shard 1"
    elif damage == "future": jobs[0]["run_attempt"] = 2
    elif damage == "missing": jobs = []
    artifacts = [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]
    with pytest.raises(ValueError, match="no successful catalog producer"):
        runtime_asset_catalog.select_catalog_artifact(artifacts, "hang-ten", 42, 1, jobs=jobs)


def test_paginated_release_selection_prints_only_the_immutable_id(tmp_path, monkeypatch, capsys):
    artifacts = tmp_path / "artifacts.json"
    artifacts.write_text(json.dumps([
        {"artifacts": [{"id": 101, "name": "hang-ten-board-assets-42-1", "expired": False}]},
        {"artifacts": [{"id": 102, "name": "hang-ten-board-assets-42-2", "expired": False}]},
    ]))
    jobs = tmp_path / "jobs.json"
    jobs.write_text(json.dumps([{"jobs": producer_jobs(1)}, {"jobs": producer_jobs(2)}]))
    monkeypatch.setattr(sys, "argv", ["runtime_asset_catalog.py", "--artifact-pages", str(artifacts),
                                   "--job-pages", str(jobs), "--owner", "hang-ten",
                                   "--run-id", "42", "--run-attempt", "3"])
    assert runtime_asset_catalog.main() == 0
    assert capsys.readouterr().out == "102\n"
