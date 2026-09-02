from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from conftest import (
    write_board_package,
    write_multi_presentation_board_package,
    write_primary_only_draft,
)
from presentation_remediation_helpers import (
    empty_phase2_document as _empty_phase2_document,
    manifest as _manifest,
    record as _record,
    write_manifest as _write_manifest,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "hangboard-packages.sh"


def _run_cli(
    *args: str,
    environment_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HANGBOARD_PYTHON"] = sys.executable
    environment.update(environment_overrides or {})
    return subprocess.run(
        [str(SCRIPT_PATH), *args],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def _json_output(output: str) -> dict[str, object]:
    return json.loads(output[output.find("{") :])


def _write_chroma_config(context: Path, payload: object | None = None) -> Path:
    path = context / "chroma-config.json"
    path.write_text(
        json.dumps(
            payload
            if payload is not None
            else {
                "keyRGB": [0, 255, 0],
                "distanceThreshold": 36,
                "edgeDistanceThreshold": 72,
            }
        ),
        encoding="utf-8",
    )
    return path


def _source_record(path: Path, source_id: str = "fixture") -> dict[str, object]:
    return {
        "path": str(path),
        "sourceID": source_id,
        "url": f"https://manufacturer.example/{source_id}",
        "publisher": "Fixture Manufacturer",
        "role": "product",
        "revision": "fixture-revision",
        "reviewedAt": "2026-09-02",
    }


def _source_manifest(context: Path, records: list[dict[str, object]]) -> Path:
    path = context / "sources" / "index.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"sources": records}), encoding="utf-8")
    return path


def test_cord_assets_cli_rejects_paths_outside_owner_context(tmp_path: Path) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-assets"
    context.mkdir(parents=True)
    raw = tmp_path / "raw.png"
    Image.new("RGB", (3, 3), (0, 255, 0)).save(raw, format="PNG")
    config = _write_chroma_config(context)
    pseudo = tmp_path / "not.context" / "joyful-donkey-pseudo" / "out.png"

    result = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(pseudo),
        "--config",
        str(config),
        "--report",
        str(context / "report.json"),
    )

    assert result.returncode == 1
    assert "owner-named .context" in result.stderr


def test_cord_assets_literal_p3_lock_and_atlas_share_one_frozen_manifest(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-assets"
    context.mkdir(parents=True)
    source = tmp_path / "external-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source)])

    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))

    assert locked.returncode == 0, locked.stderr
    artifact = json.loads(manifest.read_text(encoding="utf-8"))
    assert set(artifact) == {
        "schemaVersion",
        "toolVersion",
        "kind",
        "digestVersion",
        "sourceLockSHA256",
        "sources",
    }
    assert artifact["kind"] == "cordSourceLock"
    assert len(artifact["sourceLockSHA256"]) == 64
    locked_record = artifact["sources"][0]
    assert Path(locked_record["originalPath"]) == source.resolve()
    cache = Path(locked_record["cachePath"])
    assert cache.is_relative_to(context.resolve())
    assert cache.read_bytes() == source.read_bytes()

    atlas_root = context / "atlases"
    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(atlas_root),
    )

    assert atlas.returncode == 0, atlas.stderr
    atlas_report = json.loads((atlas_root / "index.json").read_text(encoding="utf-8"))
    assert atlas_report["verification"] == {"valid": True, "verified_panels": 1}
    assert atlas_report["index"]["sources"] == artifact["sources"]


def test_cord_assets_lock_preflights_report_before_freezing_manifest(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-lock-preflight"
    context.mkdir(parents=True)
    source = tmp_path / "preflight-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "preflight")])
    original_manifest = manifest.read_bytes()
    pseudo_report = (
        tmp_path / "not.context" / "joyful-donkey-pseudo" / "lock-report.json"
    )

    result = _run_cli(
        "cord-assets",
        "lock",
        "--manifest",
        str(manifest),
        "--report",
        str(pseudo_report),
    )

    assert result.returncode == 1
    assert "owner-named .context" in result.stderr
    assert manifest.read_bytes() == original_manifest


def test_cord_assets_lock_rejects_invalid_report_leaf_before_any_artifact_changes(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-lock-leaf-preflight"
    context.mkdir(parents=True)
    source = tmp_path / "leaf-preflight-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "leaf-preflight")])
    original_manifest = manifest.read_bytes()
    report_directory = context / "report-directory"
    report_directory.mkdir()

    result = _run_cli(
        "cord-assets",
        "lock",
        "--manifest",
        str(manifest),
        "--report",
        str(report_directory),
    )

    assert result.returncode == 1
    assert (
        result.stderr
        == "error: output target must be absent or a regular file: report-directory\n"
    )
    assert manifest.read_bytes() == original_manifest
    assert not (context / "sources" / "locked").exists()


def test_cord_assets_lock_rejects_manifest_report_alias_before_freezing(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-lock-alias"
    context.mkdir(parents=True)
    source = tmp_path / "lock-alias-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "lock-alias")])
    original_manifest = manifest.read_bytes()

    result = _run_cli(
        "cord-assets",
        "lock",
        "--manifest",
        str(manifest),
        "--report",
        str(manifest),
    )

    assert result.returncode == 1
    assert "path roles alias" in result.stderr
    assert manifest.read_bytes() == original_manifest
    assert not (context / "sources" / "locked").exists()


def test_cord_assets_atlas_fails_if_original_changes_after_lock(tmp_path: Path) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-mutable-original"
    context.mkdir(parents=True)
    source = tmp_path / "mutable-original.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "mutable-original")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    Image.new("RGB", (3, 3), (40, 50, 60)).save(source, format="PNG")

    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(context / "atlases"),
    )

    assert atlas.returncode == 1
    assert atlas.stderr == "error: original source hash mismatch: mutable-original\n"


def test_cord_assets_atlas_fails_if_frozen_cache_changes_after_lock(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-mutable-cache"
    context.mkdir(parents=True)
    source = tmp_path / "cache-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "mutable-cache")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    artifact = json.loads(manifest.read_text(encoding="utf-8"))
    cache = Path(artifact["sources"][0]["cachePath"])
    Image.new("RGB", (3, 3), (40, 50, 60)).save(cache, format="PNG")

    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(context / "atlases"),
    )

    assert atlas.returncode == 1
    assert atlas.stderr == "error: locked source hash mismatch: mutable-cache\n"


def test_cord_assets_atlas_rejects_valid_value_frozen_provenance_tamper(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-provenance-tamper"
    context.mkdir(parents=True)
    source = tmp_path / "provenance-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "provenance")])
    assert _run_cli("cord-assets", "lock", "--manifest", str(manifest)).returncode == 0
    artifact = json.loads(manifest.read_text(encoding="utf-8"))
    artifact["sources"][0]["url"] = "https://different.example/valid-revision"
    manifest.write_text(json.dumps(artifact), encoding="utf-8")

    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(context / "atlases"),
    )

    assert atlas.returncode == 1
    assert "source lock digest mismatch" in atlas.stderr
    assert not (context / "atlases").exists()


def test_cord_assets_atlas_rejects_wrong_typed_frozen_schema_version(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-schema-type"
    context.mkdir(parents=True)
    source = tmp_path / "schema-type-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "schema-type")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    artifact = json.loads(manifest.read_text(encoding="utf-8"))
    artifact["schemaVersion"] = True
    manifest.write_text(json.dumps(artifact), encoding="utf-8")

    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(context / "atlases"),
    )

    assert atlas.returncode == 1
    assert (
        atlas.stderr
        == "error: locked source manifest.schemaVersion must be an integer\n"
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        (42, "manifest must be a JSON object"),
        ({"sources": [], "unknown": True}, "manifest has unknown fields"),
        ({"sources": [{"sourceID": "missing-fields"}]}, "sources[0] is missing fields"),
    ],
)
def test_cord_assets_lock_rejects_malformed_manifest_with_concise_error(
    tmp_path: Path, payload: object, message: str
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-bad-manifest"
    context.mkdir(parents=True)
    manifest = context / "manifest.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    result = _run_cli(
        "cord-assets",
        "lock",
        "--manifest",
        str(manifest),
        "--report",
        str(context / "report.json"),
    )

    assert result.returncode == 1
    assert result.stderr == f"error: {message}\n"
    assert "Traceback" not in result.stderr


def test_cord_assets_lock_rejects_duplicate_and_escaping_source_ids(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-source-ids"
    context.mkdir(parents=True)
    source = tmp_path / "source-id.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    duplicate_manifest = _source_manifest(
        context,
        [_source_record(source, "same"), _source_record(source, "same")],
    )

    duplicate = _run_cli("cord-assets", "lock", "--manifest", str(duplicate_manifest))

    assert duplicate.returncode == 1
    assert duplicate.stderr == "error: duplicate source ID: same\n"

    escape_context = tmp_path / ".context" / "joyful-donkey-cli-source-id-escape"
    escape_context.mkdir(parents=True)
    escape_manifest = _source_manifest(
        escape_context, [_source_record(source, "../../../escape")]
    )
    escape = _run_cli("cord-assets", "lock", "--manifest", str(escape_manifest))

    assert escape.returncode == 1
    assert escape.stderr == "error: sources[0].sourceID must be a safe path component\n"


def test_cord_assets_atlas_rejects_preexisting_page_symlink(tmp_path: Path) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-page-symlink"
    context.mkdir(parents=True)
    source = tmp_path / "page-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "page-source")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    output = context / "atlases"
    output.mkdir()
    unrelated = tmp_path / "unrelated.png"
    unrelated.write_bytes(b"unrelated")
    (output / "page-01.png").symlink_to(unrelated)

    atlas = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
    )

    assert atlas.returncode == 1
    assert "symlink" in atlas.stderr
    assert unrelated.read_bytes() == b"unrelated"


def test_cord_assets_atlas_rejects_manifest_report_alias_before_pages_change(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-atlas-alias"
    context.mkdir(parents=True)
    source = tmp_path / "atlas-alias-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "atlas-alias")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    frozen_manifest = manifest.read_bytes()
    output = context / "atlases"

    result = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(manifest),
    )

    assert result.returncode == 1
    assert "path roles alias" in result.stderr
    assert manifest.read_bytes() == frozen_manifest
    assert not output.exists()


def test_cord_assets_atlas_rejects_invalid_report_before_pages_change(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-atlas-report-leaf"
    context.mkdir(parents=True)
    source = tmp_path / "atlas-report-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "atlas-report")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    output = context / "atlases"
    invalid_report = context / "report-directory"
    invalid_report.mkdir()

    result = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(invalid_report),
    )

    assert result.returncode == 1
    assert "output target must be absent or a regular file" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    "relative_report",
    ["report.json", "page-99.png", "nested/report.json"],
)
def test_cord_assets_atlas_rejects_custom_report_below_output_before_mutation(
    tmp_path: Path, relative_report: str
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-atlas-report-inside"
    context.mkdir(parents=True)
    source = tmp_path / "atlas-report-inside-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "report-inside")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    before = {
        str(path.relative_to(context)): path.read_bytes()
        for path in sorted(context.rglob("*"))
        if path.is_file()
    }
    output = context / "atlases"

    result = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(output / relative_report),
    )

    assert result.returncode == 1
    assert "custom atlas report must be outside the atlas output root" in result.stderr
    assert not output.exists()
    assert {
        str(path.relative_to(context)): path.read_bytes()
        for path in sorted(context.rglob("*"))
        if path.is_file()
    } == before


def test_cord_assets_atlas_rejects_report_ancestor_of_output_before_mutation(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-atlas-report-ancestor"
    context.mkdir(parents=True)
    source = tmp_path / "atlas-report-ancestor-source.png"
    Image.new("RGB", (3, 3), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, "report-ancestor")])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    report = context / "atlas-report"
    output = report / "pages"

    result = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(report),
    )

    assert result.returncode == 1
    assert "custom atlas report must be outside the atlas output root" in result.stderr
    assert not report.exists()


@pytest.mark.parametrize("report_kind", ["canonical", "external"])
def test_cord_assets_atlas_allows_identical_rebuild_with_coherent_report_location(
    tmp_path: Path, report_kind: str
) -> None:
    context = tmp_path / ".context" / f"joyful-donkey-cli-atlas-{report_kind}"
    context.mkdir(parents=True)
    source = tmp_path / f"atlas-{report_kind}-source.png"
    Image.new("RGB", (7, 5), (4, 5, 6)).save(source, format="PNG")
    manifest = _source_manifest(context, [_source_record(source, report_kind)])
    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr
    output = context / "atlases"
    report = (
        output / "index.json"
        if report_kind == "canonical"
        else context / "reports" / "atlas.json"
    )

    first = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(report),
    )
    assert first.returncode == 0, first.stderr
    first_index = (output / "index.json").read_bytes()
    first_page = (output / "page-01.png").read_bytes()

    rebuilt = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(output),
        "--report",
        str(report),
    )

    assert rebuilt.returncode == 0, rebuilt.stderr
    assert (output / "index.json").read_bytes() == first_index
    assert (output / "page-01.png").read_bytes() == first_page
    assert report.is_file()


def test_cord_assets_atlas_rebuild_removes_stale_page_and_rejects_unknown_files(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-atlas-rebuild"
    context.mkdir(parents=True)
    sources = []
    for number in range(2):
        source = tmp_path / f"atlas-rebuild-{number}.png"
        Image.new("RGB", (2000, 1100), (number + 1, 4, 5)).save(source, format="PNG")
        sources.append(source)
    first_manifest = _source_manifest(
        context,
        [
            _source_record(path, f"rebuild-{number}")
            for number, path in enumerate(sources)
        ],
    )
    assert (
        _run_cli("cord-assets", "lock", "--manifest", str(first_manifest)).returncode
        == 0
    )
    output = context / "atlases"
    first = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(first_manifest),
        "--output-root",
        str(output),
    )
    assert first.returncode == 0, first.stderr
    assert (output / "page-02.png").is_file()

    second_manifest = context / "sources" / "single.json"
    second_manifest.write_text(
        json.dumps({"sources": [_source_record(sources[0], "rebuild-0")]}),
        encoding="utf-8",
    )
    assert (
        _run_cli("cord-assets", "lock", "--manifest", str(second_manifest)).returncode
        == 0
    )
    rebuilt = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(second_manifest),
        "--output-root",
        str(output),
    )
    assert rebuilt.returncode == 0, rebuilt.stderr
    assert not (output / "page-02.png").exists()

    unknown = output / "notes.txt"
    unknown.write_text("keep", encoding="utf-8")
    before_index = (output / "index.json").read_bytes()
    before_page = (output / "page-01.png").read_bytes()
    rejected = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(second_manifest),
        "--output-root",
        str(output),
    )
    assert rejected.returncode == 1
    assert "unknown atlas output" in rejected.stderr
    assert unknown.read_text(encoding="utf-8") == "keep"
    assert (output / "index.json").read_bytes() == before_index
    assert (output / "page-01.png").read_bytes() == before_page


def test_cord_assets_literal_p6_key_and_inspect_resolve_declared_canvas(
    tmp_path: Path,
) -> None:
    board_root = tmp_path / "Hangboards" / "fixture-board"
    write_board_package(board_root)
    context = tmp_path / ".context" / "joyful-donkey-cli-p6"
    context.mkdir(parents=True)
    raw = tmp_path / "candidate-raw.png"
    image = Image.new("RGBA", (40, 20), (0, 255, 0, 255))
    for x in range(15, 25):
        for y in range(7, 13):
            image.putpixel((x, y), (90, 80, 70, 255))
    image.save(raw, format="PNG")
    config = _write_chroma_config(context)
    output = context / "candidate-rgba.png"
    key_report = context / "candidate-report.json"

    keyed = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(output),
        "--config",
        str(config),
        "--report",
        str(key_report),
    )
    assert keyed.returncode == 0, keyed.stderr
    inspect_report = context / "candidate-inspection.json"
    inspected = _run_cli(
        "cord-assets",
        "inspect",
        "--image",
        str(output),
        "--expected-from",
        f"{board_root / 'board.json'}:primary",
        "--config",
        str(config),
        "--report",
        str(inspect_report),
    )

    assert inspected.returncode == 0, inspected.stderr
    report = json.loads(inspect_report.read_text(encoding="utf-8"))
    assert (report["width"], report["height"]) == (40, 20)
    assert report["config"] == {
        "keyRGB": [0, 255, 0],
        "distanceThreshold": 36,
        "edgeDistanceThreshold": 72,
    }


@pytest.mark.parametrize(
    "collision",
    ["input-hardlink", "output", "config"],
)
def test_cord_assets_key_preflights_all_role_aliases_before_mutation(
    tmp_path: Path, collision: str
) -> None:
    context = tmp_path / ".context" / f"joyful-donkey-cli-key-alias-{collision}"
    context.mkdir(parents=True)
    raw = context / "candidate-raw.png"
    image = Image.new("RGB", (9, 9), (0, 255, 0))
    image.putpixel((4, 4), (90, 80, 70))
    image.save(raw, format="PNG")
    raw_before = raw.read_bytes()
    config = _write_chroma_config(context)
    config_before = config.read_bytes()
    output = context / "candidate-rgba.png"
    if collision == "input-hardlink":
        report = context / "candidate-report.json"
        os.link(raw, report)
    elif collision == "output":
        report = output
    else:
        report = config

    result = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(output),
        "--config",
        str(config),
        "--report",
        str(report),
    )

    assert result.returncode == 1
    assert "path roles alias" in result.stderr
    assert raw.read_bytes() == raw_before
    assert config.read_bytes() == config_before
    assert not output.exists()


def test_cord_assets_key_rejects_invalid_output_leaf_before_report_changes(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-key-output-leaf"
    context.mkdir(parents=True)
    raw = context / "raw.png"
    Image.new("RGB", (9, 9), (0, 255, 0)).save(raw, format="PNG")
    config = _write_chroma_config(context)
    output_directory = context / "output-directory"
    output_directory.mkdir()
    report = context / "report.json"

    result = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(output_directory),
        "--config",
        str(config),
        "--report",
        str(report),
    )

    assert result.returncode == 1
    assert "output target must be absent or a regular file" in result.stderr
    assert output_directory.is_dir()
    assert not report.exists()


def test_cord_assets_inspect_preflights_image_report_hardlink_alias(
    tmp_path: Path,
) -> None:
    board_root = tmp_path / "Hangboards" / "fixture-board"
    write_board_package(board_root)
    context = tmp_path / ".context" / "joyful-donkey-cli-inspect-alias"
    context.mkdir(parents=True)
    accepted = context / "accepted.png"
    image = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    image.putpixel((20, 10), (90, 80, 70, 255))
    image.save(accepted, format="PNG")
    accepted_before = accepted.read_bytes()
    report = context / "inspection.json"
    os.link(accepted, report)
    config = _write_chroma_config(context)

    result = _run_cli(
        "cord-assets",
        "inspect",
        "--image",
        str(accepted),
        "--expected-from",
        f"{board_root / 'board.json'}:primary",
        "--config",
        str(config),
        "--report",
        str(report),
    )

    assert result.returncode == 1
    assert "path roles alias" in result.stderr
    assert accepted.read_bytes() == accepted_before


def test_cord_assets_inspect_rejects_invalid_report_leaf_without_mutation(
    tmp_path: Path,
) -> None:
    board_root = tmp_path / "Hangboards" / "fixture-board"
    write_board_package(board_root)
    context = tmp_path / ".context" / "joyful-donkey-cli-inspect-report-leaf"
    context.mkdir(parents=True)
    accepted = context / "accepted.png"
    image = Image.new("RGBA", (40, 20), (0, 0, 0, 0))
    image.putpixel((20, 10), (90, 80, 70, 255))
    image.save(accepted, format="PNG")
    accepted_before = accepted.read_bytes()
    report_directory = context / "report-directory"
    report_directory.mkdir()
    config = _write_chroma_config(context)

    result = _run_cli(
        "cord-assets",
        "inspect",
        "--image",
        str(accepted),
        "--expected-from",
        f"{board_root / 'board.json'}:primary",
        "--config",
        str(config),
        "--report",
        str(report_directory),
    )

    assert result.returncode == 1
    assert "output target must be absent or a regular file" in result.stderr
    assert accepted.read_bytes() == accepted_before


def test_cord_assets_key_requires_explicit_strict_config(tmp_path: Path) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-required-config"
    context.mkdir(parents=True)
    raw = tmp_path / "required-config.png"
    Image.new("RGB", (3, 3), (0, 255, 0)).save(raw, format="PNG")

    missing = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(context / "output.png"),
        "--report",
        str(context / "report.json"),
    )

    assert missing.returncode == 2
    assert "--config" in missing.stderr

    malformed = _write_chroma_config(context, 42)
    invalid = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(context / "invalid-output.png"),
        "--config",
        str(malformed),
        "--report",
        str(context / "invalid-report.json"),
    )

    assert invalid.returncode == 1
    assert invalid.stderr == "error: chroma config must be a JSON object\n"
    assert "Traceback" not in invalid.stderr


def test_cord_assets_config_rejects_unknown_fields_and_non_integer_values(
    tmp_path: Path,
) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-config-schema"
    context.mkdir(parents=True)
    raw = tmp_path / "config-schema.png"
    Image.new("RGB", (3, 3), (0, 255, 0)).save(raw, format="PNG")
    bad = _write_chroma_config(
        context,
        {
            "keyRGB": [0, 255, 0],
            "distanceThreshold": True,
            "edgeDistanceThreshold": 72,
            "unknown": "field",
        },
    )

    result = _run_cli(
        "cord-assets",
        "key",
        "--input",
        str(raw),
        "--output",
        str(context / "output.png"),
        "--config",
        str(bad),
        "--report",
        str(context / "report.json"),
    )

    assert result.returncode == 1
    assert result.stderr.startswith("error: chroma config ")
    assert "Traceback" not in result.stderr


def test_cord_assets_cli_refuses_a_real_sixth_atlas_page(tmp_path: Path) -> None:
    context = tmp_path / ".context" / "joyful-donkey-cli-overflow"
    context.mkdir(parents=True)
    records = []
    for number in range(6):
        image = context / f"source-{number}.png"
        Image.new("RGB", (2000, 1100), (number, 255 - number, 0)).save(
            image, format="PNG"
        )
        records.append(
            {
                "path": str(image),
                "sourceID": f"source-{number}",
                "url": f"https://example.com/{number}",
                "publisher": "Fixture",
                "role": "product",
                "revision": "fixture",
                "reviewedAt": "2026-09-02",
            }
        )
    manifest = context / "sources.json"
    manifest.write_text(json.dumps({"sources": records}), encoding="utf-8")

    locked = _run_cli("cord-assets", "lock", "--manifest", str(manifest))
    assert locked.returncode == 0, locked.stderr

    result = _run_cli(
        "cord-assets",
        "atlas",
        "--manifest",
        str(manifest),
        "--output-root",
        str(context / "atlases"),
        "--max-pages",
        "5",
    )

    assert result.returncode == 1
    assert "requires more than 5 atlas pages; limit is 5" in result.stderr


def _write_audit_ledger(
    path: Path, *, hold_id: str = "hold-left", kind_outcome: str = "verified"
) -> Path:
    ledger = path / "metadata-ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "reviewedBoardIDs": ["fixture.board"],
                "sloperOnlyBoardIDs": [],
                "records": [
                    {
                        "boardID": "fixture.board",
                        "holdIDs": [hold_id],
                        "field": "kind",
                        "outcome": kind_outcome,
                        "reviewedAt": "2026-08-25",
                        "source": {
                            "kind": "manufacturer",
                            "url": "https://example.com/fixture-source",
                            "label": "Fixture manufacturer source",
                        },
                        "value": "jug",
                        **(
                            {"reason": "Fixture adapted role."}
                            if kind_outcome == "adapted"
                            else {}
                        ),
                    },
                    *[
                        {
                            "boardID": "fixture.board",
                            "holdIDs": [hold_id],
                            "field": field,
                            "outcome": "unavailable",
                            "reviewedAt": "2026-08-25",
                            "source": {
                                "kind": "manufacturer",
                                "url": "https://example.com/fixture-source",
                                "label": "Fixture manufacturer source",
                            },
                            "reason": "The manufacturer source does not establish this value.",
                        }
                        for field in (
                            "sizeMillimeters",
                            "depthRangeMillimeters",
                            "fingerCapacity",
                            "handCapacity",
                            "gripType",
                            "features",
                        )
                    ],
                    {
                        "boardID": "fixture.board",
                        "holdIDs": [hold_id],
                        "field": "sloper",
                        "outcome": "notApplicable",
                        "reviewedAt": "2026-08-25",
                        "source": {
                            "kind": "manufacturer",
                            "url": "https://example.com/fixture-source",
                            "label": "Fixture manufacturer source",
                        },
                        "reason": "The hold is not a sloper.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    return ledger


def test_package_cli_reports_directly_discovered_boards_and_drafts(
    tmp_path: Path,
) -> None:
    write_board_package(tmp_path / "package-board", board_id="fixture.board")
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli("status", "--root", str(tmp_path))

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "boards": [{"id": "fixture.board", "path": "package-board"}],
        "drafts": ["draft-board"],
    }


def test_package_cli_final_inventory_rejects_drafts(tmp_path: Path) -> None:
    write_primary_only_draft(tmp_path / "draft-board")

    result = _run_cli(
        "validate",
        "--root",
        str(tmp_path),
        "--final-inventory",
    )

    assert result.returncode == 1
    assert "missing board.json" in result.stderr


def test_package_cli_audit_metadata_reports_coverage(tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path)

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "reviewedBoardIDs": ["fixture.board"],
        "sloperOnlyBoardIDs": [],
        "fields": {
            "kind": {
                "populated": 1,
                "verified": 1,
                "adapted": 0,
                "unavailable": 0,
                "notApplicable": 0,
            },
            **{
                field: {
                    "populated": 0,
                    "verified": 0,
                    "adapted": 0,
                    "unavailable": 1,
                    "notApplicable": 0,
                }
                for field in (
                    "sizeMillimeters",
                    "depthRangeMillimeters",
                    "fingerCapacity",
                    "handCapacity",
                    "gripType",
                    "features",
                )
            },
            "sloper": {
                "populated": 0,
                "verified": 0,
                "adapted": 0,
                "unavailable": 0,
                "notApplicable": 1,
            },
        },
        "boards": [
            {
                "boardID": "fixture.board",
                "populated": 1,
                "verified": 1,
                "adapted": 0,
                "unavailable": 6,
                "notApplicable": 1,
                "unaccountedFields": 0,
            }
        ],
    }


def test_package_cli_audit_metadata_reports_nonzero_adapted_coverage(
    tmp_path: Path,
) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path, kind_outcome="adapted")

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 0, result.stderr
    report = _json_output(result.stdout)
    assert report["fields"]["kind"]["adapted"] == 1
    assert report["boards"] == [
        {
            "boardID": "fixture.board",
            "populated": 1,
            "verified": 0,
            "adapted": 1,
            "unavailable": 6,
            "notApplicable": 1,
            "unaccountedFields": 0,
        }
    ]


def test_package_cli_audit_metadata_rejects_unknown_hold(tmp_path: Path) -> None:
    packages = tmp_path / "packages"
    write_board_package(packages / "package-board", board_id="fixture.board")
    ledger = _write_audit_ledger(tmp_path, hold_id="unknown-hold")

    result = _run_cli(
        "audit-metadata", "--root", str(packages), "--ledger", str(ledger)
    )

    assert result.returncode == 1
    assert result.stderr == "error: unknown hold ID: unknown-hold\n"


def test_package_cli_audit_presentations_reports_selected_lane(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    write_multi_presentation_board_package(boards / "fixture-board")
    manifest = _write_manifest(
        tmp_path,
        _manifest(
            package_ids=["fixture.board"],
            records=[
                _record(
                    boards,
                    "fixture-board",
                    "fixture.board",
                    "front",
                    "assets/primary.png",
                ),
                _record(
                    boards, "fixture-board", "fixture.board", "back", "assets/back.png"
                ),
            ],
        ),
    )

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--package-id",
        "fixture.board",
    )

    assert result.returncode == 0, result.stderr
    assert _json_output(result.stdout) == {
        "decisions": {"keep": 2},
        "evidenceBlockedAssets": [],
        "packageCount": 1,
        "packageIDs": ["fixture.board"],
        "presentationCount": 2,
    }


def test_package_cli_audit_presentations_prints_domain_error_first_line(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "fixture-board")
    record = _record(
        boards, "fixture-board", "fixture.board", "primary", "assets/primary.png"
    )
    record["decision"] = "not-a-decision"
    manifest = _write_manifest(
        tmp_path, _manifest(package_ids=["fixture.board"], records=[record])
    )

    result = _run_cli(
        "audit-presentations", "--root", str(boards), "--manifest", str(manifest)
    )

    assert result.returncode == 1
    assert (
        result.stderr.splitlines()[0]
        == "error: records[0].decision must be one of ['edit', 'keep', 'regenerate', 'removeUnsupportedPresentation', 'splitPhysicalRevision']"
    )


def test_package_cli_final_presentation_audit_requires_completed_phase1_checks(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    write_board_package(boards / "fixture-board")
    record = _record(
        boards, "fixture-board", "fixture.board", "primary", "assets/primary.png"
    )
    manifest = _write_manifest(
        tmp_path, _manifest(package_ids=["fixture.board"], records=[record])
    )

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--final-validation",
    )

    assert result.returncode == 1
    assert result.stderr == (
        "error: final Phase 1 validation requires all phase1Checks passed\n"
    )


def test_package_cli_phase2_preflight_prints_extended_report(tmp_path: Path) -> None:
    boards = tmp_path / "Hangboards"
    boards.mkdir()
    manifest = _write_manifest(tmp_path, _empty_phase2_document())

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--phase2-preflight",
    )

    assert result.returncode == 0, result.stderr
    report = _json_output(result.stdout)
    assert report["phase"] == "assetRemediation"
    assert report["canvasClassCount"] == 0
    assert report["canvasCoveredRepairCount"] == 0
    assert report["capabilityProbeArtifactCount"] == 0


def test_package_cli_phase2_final_rejects_transient_file_arguments(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    boards.mkdir()
    manifest = _write_manifest(tmp_path, _empty_phase2_document())
    path = tmp_path / "candidate.png"
    path.write_bytes(b"fixture")

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--phase2-final",
        "--candidate-file",
        "0" * 64,
        str(path),
    )

    assert result.returncode == 1
    assert "final Phase 2 validation rejects transient files" in result.stderr


def test_package_cli_phase2_rejects_duplicate_transient_sha_and_nonpartial_batch(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    boards.mkdir()
    manifest = _write_manifest(tmp_path, _empty_phase2_document())
    path = tmp_path / "candidate.png"
    path.write_bytes(b"fixture")

    duplicate = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--phase2-preflight",
        "--candidate-file",
        "0" * 64,
        str(path),
        "--candidate-file",
        "0" * 64,
        str(path),
    )
    assert duplicate.returncode == 1
    assert "duplicate --candidate-file SHA-256 key" in duplicate.stderr

    batch = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--phase2-preflight",
        "--batch-id",
        "portable",
    )
    assert batch.returncode == 1
    assert "--batch-id is legal only with --phase2-partial" in batch.stderr


def test_package_cli_reports_truncated_candidate_png_as_a_domain_error(
    tmp_path: Path,
) -> None:
    boards = tmp_path / "Hangboards"
    boards.mkdir()
    candidate = tmp_path / "truncated.png"
    candidate.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR")
    digest = "0" * 64
    document = _empty_phase2_document()
    document["phase2"]["capabilityProbeCheck"]["artifacts"] = [
        {
            "id": "probe-attempt-1",
            "behaviorProbeID": "probe",
            "attempt": 1,
            "returnedOutputPath": str(tmp_path / "returned.png"),
            "transientOutputPath": str(candidate),
            "sha256": digest,
            "widthPixels": 1,
            "heightPixels": 1,
            "canvasResult": "exactCanvas",
            "disposition": "capabilityProbeRejected",
            "productionUse": "forbidden",
            "reason": "Fixture probe output.",
            "provenance": {
                "tool": "builtInImageGen",
                "untouchedModelOutput": True,
                "postProcessing": "none",
            },
            "byteVerification": {
                "status": "pending",
                "checkedAt": None,
                "command": None,
                "observedSHA256": None,
            },
            "recordedAt": "2026-08-31T00:00:00+00:00",
            "deletionVerifiedAt": None,
        }
    ]
    manifest = _write_manifest(tmp_path, document)

    result = _run_cli(
        "audit-presentations",
        "--root",
        str(boards),
        "--manifest",
        str(manifest),
        "--phase2-preflight",
        "--candidate-file",
        digest,
        str(candidate),
    )

    assert result.returncode == 1
    assert result.stderr == f"error: asset is not a PNG: {candidate}\n"


def test_wrapper_rejects_python_3_11_3_before_validation(tmp_path: Path) -> None:
    package_root = tmp_path / "packages"
    write_board_package(package_root / "package-board", board_id="fixture.board")
    version_override = tmp_path / "python-version"
    version_override.mkdir()
    (version_override / "sitecustomize.py").write_text(
        "import sys\nsys.version_info = (3, 11, 3, 'final', 0)\n",
        encoding="utf-8",
    )

    result = _run_cli(
        "status",
        "--root",
        str(package_root),
        environment_overrides={"PYTHONPATH": str(version_override)},
    )

    assert result.returncode == 69
    assert result.stderr == (
        "Hangboard package validation requires Python 3.11.4 or newer.\n"
    )


def _write_wrapper_fixture(
    tmp_path: Path,
) -> tuple[Path, Path, Path, Path, dict[str, str]]:
    repository = tmp_path / "repository"
    script = repository / "scripts" / "hangboard-packages.sh"
    script.parent.mkdir(parents=True)
    script.write_bytes(SCRIPT_PATH.read_bytes())
    script.chmod(0o755)

    pyproject = repository / "Tools" / "HangboardPackages" / "pyproject.toml"
    pyproject.parent.mkdir(parents=True)
    pyproject.write_text("[project]\nname = 'fixture'\n", encoding="utf-8")

    environment_bin = repository / ".context" / "hangboard-packages-venv" / "bin"
    environment_bin.mkdir(parents=True)
    python = environment_bin / "python"
    python.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = '-m' ] && [ \"$2\" = 'pip' ]; then\n"
        '  printf \'%s\\n\' "$*" >> "$FAKE_PIP_LOG"\n'
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    python.chmod(0o755)
    entry_point = environment_bin / "hangboard-packages"
    entry_point.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    entry_point.chmod(0o755)
    pip_log = tmp_path / "pip.log"
    environment = {
        **os.environ,
        "FAKE_PIP_LOG": str(pip_log),
        "HANGBOARD_PYTHON": str(python),
    }
    return script, pyproject, entry_point, pip_log, environment


def test_wrapper_reinstalls_when_pyproject_is_newer_than_entry_point(
    tmp_path: Path,
) -> None:
    script, _, entry_point, pip_log, environment = _write_wrapper_fixture(tmp_path)
    os.utime(entry_point, (1, 1))

    result = subprocess.run(
        [str(script), "status"],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert "-m pip install --disable-pip-version-check -e" in pip_log.read_text(
        encoding="utf-8"
    )


def test_wrapper_keeps_install_when_pyproject_is_not_newer_than_entry_point(
    tmp_path: Path,
) -> None:
    script, pyproject, entry_point, pip_log, environment = _write_wrapper_fixture(
        tmp_path
    )
    os.utime(pyproject, ns=(entry_point.stat().st_mtime_ns,) * 2)

    result = subprocess.run(
        [str(script), "status"],
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert not pip_log.exists()
