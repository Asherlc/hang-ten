from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
IMPORTER = REPO_ROOT / "scripts" / "import-generated-board-catalog.py"
SOURCE_ROOT = REPO_ROOT / "docs" / "hangboard-generative-catalog"


def _primary_images(source_root: Path) -> dict[str, Path]:
    return {
        image.stem: image
        for image in source_root.glob("*.png")
        if "contact-sheet" not in image.name
    }


def _run_importer(source_root: Path, destination_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(IMPORTER),
            "--source",
            str(source_root),
            "--destination",
            str(destination_root),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def _empty_catalog(destination_root: Path) -> None:
    destination_root.mkdir()
    (destination_root / "catalog.json").write_text(
        json.dumps({"schemaVersion": 1, "boards": []}), encoding="utf-8"
    )


def test_importer_creates_draft_package_inventory_from_generated_catalog(tmp_path: Path) -> None:
    # Removing primary.png, its draft registry entry, or the provenance README must fail this test.
    destination_root = tmp_path / "Hangboards"
    _empty_catalog(destination_root)

    result = _run_importer(SOURCE_ROOT, destination_root)

    assert result.returncode == 0, result.stderr
    catalog = json.loads((destination_root / "catalog.json").read_text(encoding="utf-8"))
    entries_by_path = {entry["path"]: entry for entry in catalog["boards"]}
    expected_primary = _primary_images(SOURCE_ROOT)
    assert set(entries_by_path) == set(expected_primary)

    for slug, source in expected_primary.items():
        package_root = destination_root / slug
        imported_entry = entries_by_path[slug]
        assert imported_entry == {"id": slug, "path": slug, "status": "draft"}
        assert (package_root / "assets" / "primary.png").read_bytes() == source.read_bytes()
        assert "unreviewed-generated-catalog" in (package_root / "README.md").read_text(encoding="utf-8")

        outline = SOURCE_ROOT / "outlines" / f"{slug}.json"
        if outline.exists():
            assert (package_root / "review" / "outline.approx.json").read_bytes() == outline.read_bytes()
        flat = SOURCE_ROOT / "flat-illustrations" / f"{slug}-flat.png"
        if flat.exists():
            assert (package_root / "assets" / "flat.png").read_bytes() == flat.read_bytes()
        ai_v2 = SOURCE_ROOT / "ai-illustrations-v2" / f"{slug}-ai-v2.png"
        if ai_v2.exists():
            assert (package_root / "assets" / "ai-v2.png").read_bytes() == ai_v2.read_bytes()
        for forbidden in ("board.json", "evidence.json", "semantics.json", "artwork.json"):
            assert not (package_root / forbidden).exists()


def test_importer_preserves_approved_package_and_quarantines_generated_material(tmp_path: Path) -> None:
    # Replacing an approved registry entry or copying catalog primary art into assets is a bug.
    source_root = tmp_path / "source"
    source_root.mkdir()
    primary = source_root / "known-board.png"
    primary.write_bytes(b"unreviewed primary")
    destination_root = tmp_path / "Hangboards"
    destination_root.mkdir()
    approved_package = destination_root / "known-board"
    (approved_package / "assets").mkdir(parents=True)
    (approved_package / "assets" / "approved.png").write_bytes(b"approved asset")
    (destination_root / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {"id": "known.board", "path": "known-board", "status": "approved"}
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _run_importer(source_root, destination_root)

    assert result.returncode == 0, result.stderr
    catalog = json.loads((destination_root / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["boards"] == [
        {"id": "known.board", "path": "known-board", "status": "approved"}
    ]
    assert (approved_package / "assets" / "approved.png").read_bytes() == b"approved asset"
    assert not (approved_package / "assets" / "primary.png").exists()
    quarantined = approved_package / "review" / "unreviewed-generated-catalog" / "assets" / "primary.png"
    assert quarantined.read_bytes() == primary.read_bytes()


def test_importer_rejects_duplicate_variant_basenames(tmp_path: Path) -> None:
    # Selecting either duplicate would silently misclassify review material.
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "known-board.png").write_bytes(b"primary")
    first = source_root / "flat-illustrations" / "first"
    second = source_root / "flat-illustrations" / "second"
    first.mkdir(parents=True)
    second.mkdir()
    (first / "known-board-flat.png").write_bytes(b"first flat")
    (second / "known-board-flat.png").write_bytes(b"second flat")
    destination_root = tmp_path / "Hangboards"
    _empty_catalog(destination_root)

    result = _run_importer(source_root, destination_root)

    assert result.returncode != 0
    assert "duplicate generated-catalog source basename" in result.stderr


def test_importer_normalizes_legacy_shipped_entry_to_a_flat_draft_until_its_package_is_complete(tmp_path: Path) -> None:
    # Marking an incomplete legacy package approved would make status-only catalog validation fail.
    source_root = tmp_path / "source"
    source_root.mkdir()
    (source_root / "draft-board.png").write_bytes(b"draft primary")
    destination_root = tmp_path / "Hangboards"
    destination_root.mkdir()
    (destination_root / "legacy-board").mkdir()
    (destination_root / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "boards": [
                    {
                        "id": "legacy.board",
                        "path": "legacy-board/board.json",
                        "lifecycle": "shipped",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = _run_importer(source_root, destination_root)

    assert result.returncode == 0, result.stderr
    catalog = json.loads((destination_root / "catalog.json").read_text(encoding="utf-8"))
    assert {entry["id"]: entry for entry in catalog["boards"]}["legacy.board"] == {
        "id": "legacy.board",
        "path": "legacy-board",
        "status": "draft",
    }
