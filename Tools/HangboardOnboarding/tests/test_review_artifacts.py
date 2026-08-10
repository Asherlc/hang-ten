from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tomllib

import pytest

from hangboard_vectorizer.review_artifacts import (
    discover_review_run,
    inspect_run,
    load_json,
    review_state,
    sha256_file,
)
from review_fixtures import (
    make_review_run,
    make_review_run_with_edit,
)


def test_discover_review_run_requires_one_stage_image_and_region_document(
    tmp_path: Path,
) -> None:
    run = make_review_run(tmp_path)
    discovered = discover_review_run(run)
    assert discovered.stage1_image.name == "stage-1-auto-rgba.png"
    assert discovered.stage2_regions.name == "stage-2-regions.json"
    assert discovered.edited_regions is None


def test_make_review_run_with_edit_is_discoverable_and_reports_edited_state(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit(tmp_path)
    discovered = discover_review_run(run)

    assert discovered.edited_regions is not None
    assert discovered.corrections is not None
    assert review_state(discovered) == "edited"


def test_discover_review_run_rejects_ambiguous_stage_two_documents(
    tmp_path: Path,
) -> None:
    run = make_review_run(tmp_path)
    duplicate = run / "stages/02/attempt-0002/stage-2-regions.json"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one stage-2-regions.json"):
        discover_review_run(run)


def test_discover_review_run_rejects_non_directory_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="review run root must be a directory"):
        discover_review_run(tmp_path / "missing-run")


def test_sha256_file_hashes_exact_bytes(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    path.write_bytes(b"artifact")
    assert sha256_file(path) == hashlib.sha256(b"artifact").hexdigest()


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        (None, "review acceptance is missing"),
        ("[1,2,3]", "review acceptance must be a JSON object"),
        ("{", "review acceptance is not valid JSON"),
    ],
)
def test_load_json_rejects_missing_invalid_and_non_object_values(
    tmp_path: Path,
    raw: str | None,
    match: str,
) -> None:
    path = tmp_path / "stage-2-review-acceptance.json"
    if raw is not None:
        path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError, match=match):
        load_json(path, "review acceptance")


def test_review_state_tracks_review_artifact_progression(tmp_path: Path) -> None:
    automatic = discover_review_run(make_review_run(tmp_path / "automatic"))
    assert review_state(automatic) == "automatic"

    edited = discover_review_run(make_review_run_with_edit(tmp_path / "edited"))
    assert review_state(edited) == "edited"

    linted_root = make_review_run_with_edit(tmp_path / "linted")
    lint_report = (
        linted_root / "stages/02/attempt-0001/lint-report.json"
    )
    lint_report.write_text(json.dumps({"passed": True}, sort_keys=True), encoding="utf-8")
    linted = discover_review_run(linted_root)
    assert review_state(linted) == "lint-passed"


def test_inspect_run_returns_relative_paths_hashes_state_and_next_action(
    tmp_path: Path,
) -> None:
    run_root = make_review_run_with_edit(tmp_path)
    lint_report = run_root / "stages/02/attempt-0001/lint-report.json"
    lint_report.write_text(
        json.dumps({"passed": True, "issues": []}, sort_keys=True), encoding="utf-8"
    )

    run = discover_review_run(run_root)
    inspected = inspect_run(run)

    assert inspected["state"] == "lint-passed"
    assert inspected["nextAction"] == "accept"
    assert inspected["artifacts"] == {
        "stage1Image": "stages/01/attempt-0001/stage-1-auto-rgba.png",
        "stage2Regions": "stages/02/attempt-0001/stage-2-regions.json",
        "editedRegions": "stages/02/attempt-0001/stage-2-regions.edited.json",
        "corrections": "stages/02/attempt-0001/stage-2-human-corrections.json",
        "lintReport": "stages/02/attempt-0001/lint-report.json",
        "acceptance": None,
        "promotionReport": None,
    }
    assert inspected["hashes"] == {
        "stage1Image": sha256_file(run.stage1_image),
        "stage2Regions": sha256_file(run.stage2_regions),
        "editedRegions": sha256_file(run.edited_regions),
        "corrections": sha256_file(run.corrections),
        "lintReport": sha256_file(run.lint_report),
    }


def test_pyproject_registers_only_review_script_for_task_one() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = project["project"]["scripts"]
    assert scripts["hangboard-review"] == "hangboard_vectorizer.review_cli:main"
    assert "hangboard-promote" not in scripts
    assert "hangboard-release-check" not in scripts
