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


def test_workbench_has_no_older_schema_adapter_or_hold_wire_contract() -> None:
    workbench = REPOSITORY_ROOT / "Tools" / "HangboardWorkbench"
    sources = _source_text(workbench, {".py", ".ts", ".tsx"})
    for prohibited in (
        "_schema_v2",
        "_legacy_editor",
        "_schema_v2_board",
        "holdGeometry",
        "holdID",
        'board["holds"]',
        "board['holds']",
        "schemaVersion == 2",
    ):
        assert prohibited not in sources


def test_only_contact_native_model_tools_remain() -> None:
    model_tools = REPOSITORY_ROOT / "Tools" / "HangboardModels"
    assert {path.name for path in model_tools.iterdir() if path.is_file()} == {
        "contact_model_descriptor.py",
        "contact_model_package.py",
        "import_contact_model_source.py",
        "verify_yy_baguette_evo.py",
        "test_contact_model_descriptor.py",
        "test_contact_model_package.py",
        "test_import_contact_model_source.py",
        "test_verify_yy_baguette_evo.py",
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
