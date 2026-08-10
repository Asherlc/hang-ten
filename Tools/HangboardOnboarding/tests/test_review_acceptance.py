from __future__ import annotations

import json
from pathlib import Path

import pytest

from hangboard_vectorizer.review_acceptance import (
    validate_acceptance,
    write_acceptance,
)
from hangboard_vectorizer.review_artifacts import discover_review_run, sha256_file
from hangboard_vectorizer.review_lint import lint_review, write_lint_report
from review_fixtures import make_review_run_with_edit


def test_acceptance_records_hashes_and_is_atomic(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path)

    path = write_acceptance(
        discover_review_run(run), "accepted", "asher", "Reviewed all regions"
    )

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["decision"] == "accepted"
    assert document["source"]["editedSha256"] == sha256_file(
        run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    )


def test_validate_acceptance_rejects_changed_edited_artifact(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path)

    write_acceptance(discover_review_run(run), "accepted", "asher", "Reviewed")
    edited = run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    edited.write_text(edited.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="edited artifact hash changed"):
        validate_acceptance(discover_review_run(run))


def test_acceptance_rejects_stale_passing_lint_after_corrections_change(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit(tmp_path)
    review_run = discover_review_run(run)
    write_lint_report(review_run, lint_review(review_run))

    corrections_path = run / "stages/02/attempt-0001/stage-2-human-corrections.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
    corrections["modified"][0]["notes"] = "stale-lint"
    corrections_path.write_text(
        json.dumps(corrections, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match="lint must pass before acceptance"):
        write_acceptance(discover_review_run(run), "accepted", "asher", "Reviewed")


@pytest.mark.parametrize("missing_key", ["stage1ImageSha256", "baselineSha256"])
def test_validate_acceptance_requires_mandatory_source_hashes(
    tmp_path: Path, missing_key: str
) -> None:
    run = make_review_run_with_edit(tmp_path)
    acceptance_path = write_acceptance(
        discover_review_run(run), "accepted", "asher", "Reviewed all regions"
    )
    document = json.loads(acceptance_path.read_text(encoding="utf-8"))
    del document["source"][missing_key]
    acceptance_path.write_text(
        json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match=missing_key):
        validate_acceptance(discover_review_run(run))


@pytest.mark.parametrize("invalid_key", ["stage1ImageSha256", "baselineSha256"])
def test_validate_acceptance_rejects_invalid_mandatory_hash_format(
    tmp_path: Path, invalid_key: str
) -> None:
    run = make_review_run_with_edit(tmp_path)
    acceptance_path = write_acceptance(
        discover_review_run(run), "accepted", "asher", "Reviewed all regions"
    )
    document = json.loads(acceptance_path.read_text(encoding="utf-8"))
    document["source"][invalid_key] = "abc123"
    acceptance_path.write_text(
        json.dumps(document, sort_keys=True) + "\n", encoding="utf-8"
    )

    with pytest.raises(ValueError, match=invalid_key):
        validate_acceptance(discover_review_run(run))
