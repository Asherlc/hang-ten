from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _source_text(root: Path, suffixes: set[str]) -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in suffixes
        and "tests" not in path.parts
        and "node_modules" not in path.parts
        and ".venv" not in path.parts
        and path.name != "app.js"
    )


def test_production_has_no_legacy_plan_or_persistence_contract() -> None:
    sources = _source_text(REPOSITORY_ROOT / "HangTen", {".swift"})
    for prohibited in (
        "SemanticHoldMappingDefinition",
        "BoardMappingDefinition",
        "unknownHoldID",
        "fallbackFeatures",
        "case holdIDs",
        "case semantic",
    ):
        assert prohibited not in sources


def test_only_contact_native_model_and_suspension_clearance_tools_remain() -> None:
    model_tools = REPOSITORY_ROOT / "Tools" / "HangboardModels"
    assert {path.name for path in model_tools.iterdir() if path.is_file()} == {
        "contact_model_descriptor.py",
        "contact_model_package.py",
        "import_contact_model_source.py",
        "clean_model_meshes.py",
        "remove_mounting_bores.py",
        "simplify_display_models.py",
        "simplification_pilot.json",
        "simplification_requirements.txt",
        "verify_simplification_pilot.py",
        "usdz_readback.py",
        "mounting_bore_requirements.txt",
        "verify_metolius_climbers_edge.py",
        "verify_owl_climb_poker.py",
        "verify_the_hangboard.py",
        "verify_trango_rock_prodigy_training_center.py",
        "verify_yy_baguette_evo.py",
        "test_contact_model_descriptor.py",
        "test_contact_model_package.py",
        "test_import_contact_model_source.py",
        "test_verify_metolius_climbers_edge.py",
        "test_verify_owl_climb_poker.py",
        "test_verify_the_hangboard.py",
        "test_verify_trango_rock_prodigy_training_center.py",
        "test_verify_yy_baguette_evo.py",
        "check_production_cord_clearance.rb",
        "production_cord_clearance.swift",
    }


def test_obsolete_package_migration_scripts_are_absent() -> None:
    scripts = REPOSITORY_ROOT / "Tools" / "HangboardPackages" / "scripts"
    assert not (scripts / "migrate_unversioned_board_packages.py").exists()
    assert not (scripts / "migrate_to_schema_v2.py").exists()


def test_active_metadata_ledger_is_contact_native() -> None:
    ledger = (
        REPOSITORY_ROOT
        / "docs"
        / "source-audits"
        / "2026-08-25-hangboard-metadata-ledger.json"
    ).read_text(encoding="utf-8")
    assert '"contactIDs"' in ledger
    assert '"holdIDs"' not in ledger
