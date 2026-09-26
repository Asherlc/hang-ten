from __future__ import annotations

import json
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import hangboard_packages.cli as cli
from conftest import package_board_text
from hangboard_packages.board_catalog import (
    BoardInventory,
    BoardModelSingleCordSuspension,
    BoardPackage,
    PresentationMediaModel,
    PresentationMediaRaster,
    discover_board_packages,
)
from hangboard_packages.cord_audit import (
    CordAuditError,
    load_cord_audit_manifest,
    validate_cord_audit_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
PRODUCTION_MANIFEST = REPO_ROOT / "docs/source-audits/2026-09-13-model-hangboard-cord-audit.json"
NEWLY_MODEL_ONLY_EXCLUSIONS = {
    "clavellium-training-block",
    "dewoodstok-woodbord",
    "escape.unlimited",
    "evolv-kilter-basic-long",
    "metolius.wood-grips-deluxe-ii",
    "moon.armstrong",
    "target10a.linebreaker-base",
}


def test_pivot_exclusion_keeps_pulley_ropes_out_of_board_suspension() -> None:
    """Catch a pulley-kit rope promoted to Pivot suspension or missing evidence."""
    records = {r.package_id: r for r in load_cord_audit_manifest(PRODUCTION_MANIFEST).records}
    assert "trango.rock-prodigy-pivot" in records
    record = records["trango.rock-prodigy-pivot"]
    assert (record.decision, record.source_fact, record.topology) == (
        "excluded", "noDocumentedSuspension", None
    )
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    pivot = next(r for r in raw["records"] if r["packageID"] == "trango.rock-prodigy-pivot")
    assert pivot["ruling"] == (
        "noDocumentedSuspension; pulley-kit ropes are not Pivot suspension."
    )
    assert pivot["humanApproval"]["approved"] is True
    assert {e["snapshotSHA256"] for e in pivot["evidence"]} == {
        "339f743c7e5fff0b0619314cf6781d8f602c1545975390f4ab4424aa7461bf5d",
        "e05deb5c0ea6d3361122926d7b3efee6b72bb9aad0a75fc09663bf599731e3e4",
        "7aa2556dec24293e62c2be110fa7dfb6bcf118333ff35693e455a8a7babc67f7",
        "26cf8d599a1a08bbcbbf688e14c9806d5f2381dc2aecdb608998ab22cee2c1b3",
    }
    for evidence in pivot["evidence"]:
        snapshot = REPO_ROOT / evidence["snapshotPath"]
        assert snapshot.is_file() and not snapshot.is_symlink()
        assert snapshot.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == evidence["snapshotSHA256"]
    board = json.loads(package_board_text(REPO_ROOT / "Hangboards/trango-rock-prodigy-pivot"))
    media = board["presentations"][0]["media"]
    assert "suspension" not in media
    assert all("suspension" not in instance for instance in media["instances"])


def test_poker_exclusion_retains_all_four_approved_manufacturer_faces() -> None:
    """Catch missing coverage or accidental suspension/hardware promotion."""
    records = {r.package_id: r for r in load_cord_audit_manifest(PRODUCTION_MANIFEST).records}
    assert "owl-climb.poker" in records
    record = records["owl-climb.poker"]
    assert (record.decision, record.source_fact, record.topology) == ("excluded", "noDocumentedSuspension", None)
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    poker = next(r for r in raw["records"] if r["packageID"] == "owl-climb.poker")
    assert poker["ruling"] == "noDocumentedSuspension; excluded."
    assert poker["humanApproval"]["approved"] is True
    assert {e["snapshotSHA256"] for e in poker["evidence"]} == {
        "4bae58b408b3f3a82c524b1101079eafa01cd062c398cb203d4803fce9850eab",
        "0c1d54cb2bc4d8e7fa285f3053b927d7c1a1b3fbafdf0b5d7aface9c82d0dbad",
        "5fbff79f31db8e85d078a74eb629abd069fc276ac128b3d85a84fc15ad9f1c4e",
        "ae39598fbf75c0e4e4dfbb599c724ff1e2531ef12ecca84b3504805e7bc3af13",
    }
    for evidence in poker["evidence"]:
        snapshot = REPO_ROOT / evidence["snapshotPath"]
        assert snapshot.is_file() and not snapshot.is_symlink()
        assert snapshot.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(snapshot.read_bytes()).hexdigest() == evidence["snapshotSHA256"]


def test_helium_cord_audit_retains_exact_front_reverse_evidence() -> None:
    manifest = load_cord_audit_manifest(PRODUCTION_MANIFEST)
    records = {record.package_id: record for record in manifest.records}
    assert "crimptonite.helium-mobile" in records
    record = records["crimptonite.helium-mobile"]
    assert record.decision == "represented"
    assert record.source_fact == "documentedSuspension"
    assert record.topology == "pairedLeadCord"
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    helium = next(item for item in raw["records"] if item["packageID"] == "crimptonite.helium-mobile")
    assert helium["ruling"] == "pairedLeadCord exterior leads only; no inferred interior route or twoBranchCord."
    assert helium["humanApproval"]["reviewer"] == "Astra"
    assert helium["humanApproval"]["reviewedAt"] == "2026-09-20"
    assert {item["snapshotSHA256"] for item in helium["evidence"]} == {
        "9f5dea470c326d32c6bde1dd5427f2bfb95a81b99ae258c320ae9deec0384a40",
        "5d5c18d45ae6d30e6e951aa158a30b303d42d4583d18d4a6d82075ff5de50f6a",
    }
    for item in helium["evidence"]:
        retained = REPO_ROOT / item["snapshotPath"]
        assert retained.is_file() and not retained.is_symlink()
        assert retained.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == item["snapshotSHA256"]


def test_light_rail_cord_audit_retains_exact_approved_upper_entry_evidence() -> None:
    """Catch missing model coverage or substitution of the changed live field photo."""
    manifest = load_cord_audit_manifest(PRODUCTION_MANIFEST)
    records = {record.package_id: record for record in manifest.records}
    assert "metolius.light-rail-2" in records
    record = records["metolius.light-rail-2"]
    assert (record.decision, record.source_fact, record.topology) == (
        "represented", "documentedSuspension", "pairedLeadCord"
    )
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    rail = next(item for item in raw["records"] if item["packageID"] == "metolius.light-rail-2")
    assert rail["ruling"] == "pairedLeadCord upper-entry exterior leads only; no underside mouth or hidden vertical bore."
    assert rail["humanApproval"]["reviewer"] == "Astra"
    assert rail["humanApproval"]["reviewedAt"] == "2026-09-20"
    assert {item["snapshotSHA256"] for item in rail["evidence"]} == {
        "7b263d3e31773efe6abdb4dcaeee7e9fcea532696427dbbabfefbb5ba72bb272",
        "93cc83c29d011c0b1b84aa02b51f8f1df4e167805ab27bffde48938c83c7fa4a",
    }
    for item in rail["evidence"]:
        retained = REPO_ROOT / item["snapshotPath"]
        assert retained.is_file() and not retained.is_symlink()
        assert retained.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == item["snapshotSHA256"]


def test_rock_rings_cord_audit_retains_exact_manufacturer_and_owner_evidence() -> None:
    """Catch missing coverage or revival of the disproved central through-bore."""
    manifest = load_cord_audit_manifest(PRODUCTION_MANIFEST)
    records = {record.package_id: record for record in manifest.records}
    assert "metolius.rock-rings-3d" in records
    record = records["metolius.rock-rings-3d"]
    assert (record.decision, record.source_fact, record.topology) == (
        "represented", "documentedSuspension", "pairedLeadCord"
    )
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    rings = next(item for item in raw["records"] if item["packageID"] == "metolius.rock-rings-3d")
    assert rings["ruling"] == "two independent pairedLeadCord systems; no inter-unit connection or central through-bore."
    assert rings["humanApproval"]["reviewer"] == "Astra"
    assert rings["humanApproval"]["reviewedAt"] == "2026-09-20"
    assert {item["snapshotSHA256"] for item in rings["evidence"]} == {
        "d92a0f25dab857eae2ee9b8581651fa9162452c38e32a7955e23c74de4a3d77c",
        "b510bd192bb6fe54c6e4dcfa98c9d684a2db7582cbfd3682cebb6e031494a8f0",
        "df263e67395aa17a2f4df263ca74e4cbbfb7bfcf9c75e0dfa611d352ad3d3cba",
    }
    for item in rings["evidence"]:
        retained = REPO_ROOT / item["snapshotPath"]
        assert retained.is_file() and not retained.is_symlink()
        assert retained.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == item["snapshotSHA256"]


def test_penta_cord_audit_retains_exact_originals_without_inventing_binary_urls() -> None:
    """Catch a missing reusable record or laundering unknown image provenance."""
    records = {record.package_id: record for record in load_cord_audit_manifest(PRODUCTION_MANIFEST).records}
    assert "yy.penta-evo" in records
    record = records["yy.penta-evo"]
    assert (record.decision, record.source_fact, record.topology) == (
        "represented", "documentedSuspension", "pairedLeadCord"
    )
    raw = json.loads(PRODUCTION_MANIFEST.read_text())
    penta = next(item for item in raw["records"] if item["packageID"] == "yy.penta-evo")
    assert penta["ruling"] == "two independent paired exterior loops through the existing central ring; no invented channel or knot."
    assert {e["snapshotSHA256"] for e in penta["evidence"]} == {
        "83b95adc297d634659654f6f27bb43ebae1c53b171b747568ac5e022754e6571",
        "1107039ef6d2877cd68a293683c72ec93f3166633199d45484f58c13b48aa2fc",
    }
    for item in penta["evidence"]:
        retained = REPO_ROOT / item["snapshotPath"]
        assert retained.is_file() and not retained.is_symlink()
        assert retained.parent == PRODUCTION_MANIFEST.parent / "2026-09-13-model-cord-snapshots"
        assert hashlib.sha256(retained.read_bytes()).hexdigest() == item["snapshotSHA256"]
    source = json.loads((REPO_ROOT / "docs/source-audits/2026-09-20-batch-04-3d-source-register.json").read_text())["boards"]["yy.penta-evo"]
    assert all(e["binaryURL"] is None and e["status"] == "unhashed" for e in source["evidence"])


def test_documented_suspension_packages_use_reviewed_visual_cords() -> None:
    repository_root = Path(__file__).resolve().parents[3]
    inventory = cli.discover_board_packages(
        repository_root / "Hangboards", require_complete_inventory=True
    )
    manifest = load_cord_audit_manifest(
        repository_root
        / "docs/source-audits/2026-09-13-model-hangboard-cord-audit.json"
    )

    report = validate_cord_audit_manifest(manifest, inventory)
    records = {record.package_id: record for record in manifest.records}

    expected_topologies = {
        "captain-fingerfood.dual": "pairedLeadCord",
        "captain-fingerfood.pocket": "pairedLeadCord",
        "captain-fingerfood.unlevel": "pairedLeadCord",
        "j-bryant.ftg-32": "pairedLeadCord",
        "yy.baguette-evo": "twoBranchCord",
    }
    assert {
        package_id: records[package_id].topology
        for package_id in expected_topologies
    } == expected_topologies
    assert all(records[package_id].decision == "represented" for package_id in expected_topologies)
    assert all(
        records[package_id].source_fact == "documentedSuspension"
        for package_id in expected_topologies
    )
    assert report.decisions == {"excluded": 33, "represented": 13}

    captain_rest_lengths = {
        "captain-fingerfood.dual": 0.4,
        "captain-fingerfood.pocket": 0.4,
        "captain-fingerfood.unlevel": 0.4,
    }
    # Measured bore centres from each primary.usdz, converted out of USD Y-up via
    # the root rotateXYZ(-90,0,0); these are the holes the cord actually leaves.
    captain_recess_terminals = {
        "captain-fingerfood.dual": ((-0.026, 0.001, -0.005), (0.026, 0.001, -0.005)),
        "captain-fingerfood.pocket": ((-0.022, 0.0, -0.0025), (0.022, 0.0, -0.0025)),
        "captain-fingerfood.unlevel": ((-0.029, 0.0, -0.0067), (0.029, 0.0, -0.0067)),
    }
    for package_id, rest_length in captain_rest_lengths.items():
        board = next(
            package.board
            for package in inventory.packages
            if package.board.id == package_id
        )
        media = board.presentations[0].media
        assert media.suspension.anchor.offset_from_board_bounds == (0.0, 0.15, 0.0)
        assert media.suspension.cord.rest_length == rest_length
        assert all(
            len(attachment.contact_points_in_model) == 2
            for attachment in media.suspension.attachments
        )
        assert tuple(
            attachment.point_in_model for attachment in media.suspension.attachments
        ) == captain_recess_terminals[package_id]

    baguette = next(
        package.board
        for package in inventory.packages
        if package.board.id == "yy.baguette-evo"
    )
    baguette_suspension = baguette.presentations[0].media.suspension
    assert baguette_suspension.anchor.offset_from_board_bounds == (0.0, 0.2, 0.0)
    assert [branch.rest_length for branch in baguette_suspension.branches] == [0.945, 0.945]


def _model_package(package_id: str, *, suspension: object | None = None) -> BoardPackage:
    media = PresentationMediaModel(
        "assets/primary.usdz", "assets/primary.model.json", {}, suspension
    )
    presentation = SimpleNamespace(media=media)
    board = SimpleNamespace(id=package_id, presentations=(presentation,))
    return BoardPackage(Path(package_id), board)


def _raster_package(package_id: str) -> BoardPackage:
    media = PresentationMediaRaster("assets/primary.png", {})
    presentation = SimpleNamespace(media=media)
    board = SimpleNamespace(id=package_id, presentations=(presentation,))
    return BoardPackage(Path(package_id), board)


def _inventory(*packages: BoardPackage) -> BoardInventory:
    return BoardInventory(packages=packages, drafts=())


def _record(
    package_id: str,
    *,
    decision: str = "excluded",
    topology: str | None = None,
    source_fact: str | None = None,
    ruling: str = "The primary product listing does not establish a supplied cord.",
    evidence: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    evidence_value = evidence
    if evidence_value is not None:
        evidence_value = [
            {
                "exactRevisionID": "fixture-revision-2026",
                "sourceTier": "manufacturer",
                "snapshotSHA256": f"{index + 1:x}" * 64,
                "snapshotPath": (
                    "docs/source-audits/2026-09-13-model-cord-snapshots/"
                    f"fixture-{index}.html"
                ),
                **item,
            }
            for index, item in enumerate(evidence_value)
        ]
    return {
        "packageID": package_id,
        "decision": decision,
        "sourceFact": source_fact
        or (
            "documentedSuspension"
            if decision == "represented"
            else "noDocumentedSuspension"
        ),
        "topology": topology,
        "ruling": ruling,
        "evidence": evidence_value if evidence_value is not None else [
            {
                "view": "front",
                "url": "https://example.com/front",
                "exactRevisionID": "fixture-revision-2026",
                "sourceTier": "manufacturer",
                "snapshotSHA256": "a" * 64,
                "snapshotPath": (
                    "docs/source-audits/2026-09-13-model-cord-snapshots/fixture-front.html"
                ),
            },
            {
                "view": "side",
                "url": "https://example.com/side",
                "exactRevisionID": "fixture-revision-2026",
                "sourceTier": "manufacturer",
                "snapshotSHA256": "b" * 64,
                "snapshotPath": (
                    "docs/source-audits/2026-09-13-model-cord-snapshots/fixture-side.html"
                ),
            },
        ],
        "humanApproval": {
            "approved": True,
            "reviewer": "fixture-reviewer",
            "reviewedAt": "2026-09-13",
            "notes": "Exact revision and retained views approved.",
        },
    }


def _manifest_path(
    tmp_path: Path, records: list[dict[str, object]], *, write_snapshots: bool = True
) -> Path:
    if write_snapshots:
        for record in records:
            for evidence in record["evidence"]:  # type: ignore[index]
                snapshot_path = evidence.get("snapshotPath")  # type: ignore[union-attr]
                if not isinstance(snapshot_path, str):
                    continue
                snapshot = tmp_path / snapshot_path
                snapshot.parent.mkdir(parents=True, exist_ok=True)
                contents = f"fixture snapshot: {snapshot}".encode()
                snapshot.write_bytes(contents)
                if "snapshotSHA256" in evidence:  # type: ignore[operator]
                    evidence["snapshotSHA256"] = hashlib.sha256(contents).hexdigest()  # type: ignore[index]
    path = tmp_path / "cord-audit.json"
    path.write_text(json.dumps({"schemaVersion": 1, "records": records}), encoding="utf-8")
    return path


def _validate(
    tmp_path: Path, inventory: BoardInventory, records: list[dict[str, object]]
) -> object:
    return validate_cord_audit_manifest(
        load_cord_audit_manifest(_manifest_path(tmp_path, records)), inventory
    )


def test_model_inventory_requires_one_record_for_each_model_package(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.one"), _model_package("fixture.two"))

    with pytest.raises(CordAuditError, match=r"missing model package record: fixture\.two"):
        _validate(tmp_path, inventory, [_record("fixture.one")])


def test_duplicate_model_record_is_rejected(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")

    with pytest.raises(CordAuditError, match="duplicate model package record"):
        _validate(tmp_path, inventory, [record, record.copy()])


def test_raster_package_record_is_rejected(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.model"), _raster_package("fixture.raster"))

    with pytest.raises(CordAuditError, match="unknown model package record: fixture.raster"):
        _validate(tmp_path, inventory, [_record("fixture.model"), _record("fixture.raster")])


def test_represented_record_requires_matching_package_suspension_topology(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(CordAuditError, match="does not match package suspension topology"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                )
            ],
        )


def test_excluded_record_rejects_package_with_suspension(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="excluded record requires no package suspension"):
        _validate(tmp_path, inventory, [_record("fixture.board")])


def test_represented_record_requires_two_distinct_evidence_views(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="two distinct evidence views"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                    evidence=[{"view": "front", "url": "https://example.com/front"}],
                )
            ],
        )


def test_represented_record_accepts_same_source_page_url_for_independent_snapshots(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    report = _validate(
        tmp_path,
        inventory,
        [
            _record(
                "fixture.board",
                decision="represented",
                topology="singleCord",
                evidence=[
                    {"view": "front", "url": "https://example.com/view"},
                    {"view": "oblique", "url": "https://example.com/view"},
                ],
            )
        ],
    )

    assert report.to_json() == {
        "modelPackageIDs": ["fixture.board"],
        "decisions": {"represented": 1},
    }


def test_represented_record_rejects_duplicate_normalized_evidence_view_labels(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(CordAuditError, match="distinct evidence views"):
        _validate(
            tmp_path,
            inventory,
            [
                _record(
                    "fixture.board",
                    decision="represented",
                    topology="singleCord",
                    evidence=[
                        {"view": "Front", "url": "https://example.com/front"},
                        {"view": " front ", "url": "https://example.com/oblique"},
                    ],
                )
            ],
        )


def test_represented_record_rejects_reused_retained_source_artifact(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )
    record = _record(
        "fixture.board",
        decision="represented",
        topology="singleCord",
        evidence=[
            {"view": "front", "url": "https://example.com/front"},
            {"view": "oblique", "url": "https://example.com/front"},
        ],
    )
    record["evidence"][1]["snapshotPath"] = record["evidence"][0]["snapshotPath"]  # type: ignore[index]

    with pytest.raises(CordAuditError, match="distinct retained source artifacts"):
        _validate(tmp_path, inventory, [record])


def test_represented_record_rejects_reused_retained_source_bytes(
    tmp_path: Path,
) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.board",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        )
    )
    record = _record(
        "fixture.board",
        decision="represented",
        topology="singleCord",
        evidence=[
            {"view": "front", "url": "https://example.com/front"},
            {"view": "oblique", "url": "https://example.com/front"},
        ],
    )
    manifest_path = _manifest_path(tmp_path, [record])
    first = tmp_path / record["evidence"][0]["snapshotPath"]  # type: ignore[index]
    second = tmp_path / record["evidence"][1]["snapshotPath"]  # type: ignore[index]
    second.write_bytes(first.read_bytes())
    digest = hashlib.sha256(first.read_bytes()).hexdigest()
    record["evidence"][0]["snapshotSHA256"] = digest  # type: ignore[index]
    record["evidence"][1]["snapshotSHA256"] = digest  # type: ignore[index]
    manifest_path.write_text(
        json.dumps({"schemaVersion": 1, "records": [record]}), encoding="utf-8"
    )

    with pytest.raises(CordAuditError, match="distinct retained source artifacts"):
        validate_cord_audit_manifest(load_cord_audit_manifest(manifest_path), inventory)


def test_manifest_rejects_self_authored_markdown_ledger_as_snapshot(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["evidence"][0]["snapshotPath"] = (  # type: ignore[index]
        "docs/source-audits/2026-09-13-model-cord-snapshots/cord-evidence.md"
    )

    with pytest.raises(CordAuditError, match="source artifact"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_self_authored_json_ledger_as_snapshot(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["evidence"][0]["snapshotPath"] = (  # type: ignore[index]
        "docs/source-audits/2026-09-13-model-hangboard-cord-audit.json"
    )

    with pytest.raises(CordAuditError, match="beneath docs/source-audits/2026-09-13-model-cord-snapshots"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_snapshot_outside_canonical_snapshot_root(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["evidence"][0]["snapshotPath"] = "docs/source-audits/other.html"  # type: ignore[index]

    with pytest.raises(CordAuditError, match="beneath docs/source-audits/2026-09-13-model-cord-snapshots"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_symlink_snapshot(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    manifest_path = _manifest_path(tmp_path, [record])
    snapshot = tmp_path / record["evidence"][0]["snapshotPath"]  # type: ignore[index]
    retained = snapshot.with_name("retained-source.html")
    retained.write_bytes(snapshot.read_bytes())
    snapshot.unlink()
    snapshot.symlink_to(retained)

    with pytest.raises(CordAuditError, match="must not contain a symbolic link"):
        validate_cord_audit_manifest(load_cord_audit_manifest(manifest_path), inventory)


def test_manifest_rejects_symlinked_snapshot_directory(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    manifest_path = _manifest_path(tmp_path, [record])
    snapshot = tmp_path / record["evidence"][0]["snapshotPath"]  # type: ignore[index]
    retained = snapshot.parent / "retained"
    retained.mkdir()
    snapshot.rename(retained / snapshot.name)
    snapshot.parent.joinpath("linked").symlink_to(retained, target_is_directory=True)
    record["evidence"][0]["snapshotPath"] = (  # type: ignore[index]
        "docs/source-audits/2026-09-13-model-cord-snapshots/linked/fixture-front.html"
    )
    manifest_path.write_text(
        json.dumps({"schemaVersion": 1, "records": [record]}), encoding="utf-8"
    )

    with pytest.raises(CordAuditError, match="must not contain a symbolic link"):
        validate_cord_audit_manifest(load_cord_audit_manifest(manifest_path), inventory)


@pytest.mark.parametrize("reviewed_at", ["2026-02-30", "2026-13-01", "2026-00-01"])
def test_manifest_rejects_non_calendar_human_review_date(
    tmp_path: Path, reviewed_at: str
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["humanApproval"]["reviewedAt"] = reviewed_at  # type: ignore[index]

    with pytest.raises(CordAuditError, match="reviewedAt must be an ISO calendar date"):
        _validate(tmp_path, inventory, [record])


def test_excluded_record_requires_retained_source_evidence(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(CordAuditError, match="requires retained source evidence"):
        _validate(tmp_path, inventory, [_record("fixture.board", evidence=[])])


def test_excluded_record_rejects_documented_suspension_source_fact_without_metadata(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(
        CordAuditError, match="source fact documents suspended presentation"
    ):
        _validate(
            tmp_path,
            inventory,
            [_record("fixture.board", source_fact="documentedSuspension")],
        )


def test_manifest_rejects_unknown_record_keys(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["unreviewed"] = True

    with pytest.raises(CordAuditError, match="has unknown keys"):
        _validate(tmp_path, inventory, [record])


@pytest.mark.parametrize(
    ("field", "evidence_index"),
    [
        ("exactRevisionID", 0),
        ("sourceTier", 0),
        ("snapshotSHA256", 0),
        ("snapshotPath", 0),
    ],
)
def test_manifest_rejects_incomplete_evidence_provenance(
    tmp_path: Path, field: str, evidence_index: int
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    del record["evidence"][evidence_index][field]  # type: ignore[index]

    with pytest.raises(CordAuditError, match=field):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_incomplete_human_approval(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    del record["humanApproval"]["reviewer"]  # type: ignore[index]

    with pytest.raises(CordAuditError, match="humanApproval"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_unapproved_human_review(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["humanApproval"]["approved"] = False  # type: ignore[index]

    with pytest.raises(CordAuditError, match="approved"):
        _validate(tmp_path, inventory, [record])


def test_manifest_rejects_nonexistent_snapshot(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    manifest_path = _manifest_path(tmp_path, [record])
    (tmp_path / record["evidence"][0]["snapshotPath"]).unlink()  # type: ignore[index]

    with pytest.raises(CordAuditError, match="snapshot path does not name a regular file"):
        validate_cord_audit_manifest(load_cord_audit_manifest(manifest_path), inventory)


def test_manifest_rejects_mismatched_snapshot_digest(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    manifest_path = _manifest_path(tmp_path, [record])
    record["evidence"][0]["snapshotSHA256"] = "a" * 64  # type: ignore[index]
    manifest_path.write_text(
        json.dumps({"schemaVersion": 1, "records": [record]}), encoding="utf-8"
    )

    with pytest.raises(CordAuditError, match="snapshot SHA-256 does not match"):
        validate_cord_audit_manifest(load_cord_audit_manifest(manifest_path), inventory)


def test_manifest_rejects_non_string_topology_without_leaking_type_errors(
    tmp_path: Path,
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    record = _record("fixture.board")
    record["topology"] = []

    with pytest.raises(CordAuditError, match="topology must be null or one of"):
        _validate(tmp_path, inventory, [record])


def test_manifest_and_model_inventory_sets_must_be_equal(tmp_path: Path) -> None:
    inventory = _inventory(_model_package("fixture.board"))

    with pytest.raises(CordAuditError, match="manifest model package IDs must equal inventory"):
        _validate(tmp_path, inventory, [_record("unknown.board")])


def test_valid_represented_and_excluded_records_report_decisions(tmp_path: Path) -> None:
    inventory = _inventory(
        _model_package(
            "fixture.represented",
            suspension=BoardModelSingleCordSuspension(None, None, None, {}),  # type: ignore[arg-type]
        ),
        _model_package("fixture.excluded"),
        _raster_package("fixture.raster"),
    )

    report = _validate(
        tmp_path,
        inventory,
        [
            _record(
                "fixture.represented",
                decision="represented",
                topology="singleCord",
            ),
            _record("fixture.excluded"),
        ],
    )

    assert report.to_json() == {
        "modelPackageIDs": ["fixture.excluded", "fixture.represented"],
        "decisions": {"excluded": 1, "represented": 1},
    }


def test_cli_audit_cords_reports_model_coverage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    inventory = _inventory(_model_package("fixture.board"))
    manifest = _manifest_path(tmp_path, [_record("fixture.board")])
    observed_complete_inventory: list[bool] = []

    def discover(root: Path, *, require_complete_inventory: bool) -> BoardInventory:
        observed_complete_inventory.append(require_complete_inventory)
        return inventory

    monkeypatch.setattr(cli, "discover_board_packages", discover)

    assert cli.main(["audit-cords", "--root", str(tmp_path), "--manifest", str(manifest)]) == 0
    assert observed_complete_inventory == [True]
    assert json.loads(capsys.readouterr().out) == {
        "modelPackageIDs": ["fixture.board"],
        "decisions": {"excluded": 1},
    }


def test_production_manifest_excludes_new_model_only_packages_without_suspension() -> None:
    inventory = discover_board_packages(REPO_ROOT / "Hangboards", require_complete_inventory=True)
    manifest = load_cord_audit_manifest(PRODUCTION_MANIFEST)

    validate_cord_audit_manifest(manifest, inventory)

    records = {record.package_id: record for record in manifest.records}
    assert NEWLY_MODEL_ONLY_EXCLUSIONS <= set(records)
    for package_id in NEWLY_MODEL_ONLY_EXCLUSIONS:
        assert records[package_id].decision == "excluded"
        assert records[package_id].source_fact == "noDocumentedSuspension"
        assert records[package_id].topology is None
