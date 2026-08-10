from __future__ import annotations

import json
from pathlib import Path

import pytest

from hangboard_vectorizer.review_acceptance import (
    validate_acceptance,
    write_acceptance,
)
from hangboard_vectorizer.review_artifacts import discover_review_run, sha256_file
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
