from __future__ import annotations

from pathlib import Path

from hangboard_vectorizer.review_artifacts import discover_review_run, sha256_file
from hangboard_vectorizer.review_preview import (
    build_comparison_document,
    render_preview_bundle,
)
from review_fixtures import make_review_run, make_review_run_with_edit


def test_preview_bundle_is_deterministic_and_records_edited_hash(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path / "run")

    first = render_preview_bundle(discover_review_run(run), tmp_path / "first")
    second = render_preview_bundle(discover_review_run(run), tmp_path / "second")

    assert first["editedSha256"] == second["editedSha256"]
    assert first["editedSha256"] == sha256_file(
        run / "stages/02/attempt-0001/stage-2-regions.edited.json"
    )
    assert (
        tmp_path / "first/review-preview/edited.png"
    ).read_bytes() == (tmp_path / "second/review-preview/edited.png").read_bytes()
    assert (
        tmp_path / "first/review-preview/review-gallery.html"
    ).is_file()


def test_build_comparison_document_is_self_contained_and_read_only(tmp_path: Path) -> None:
    run = discover_review_run(make_review_run_with_edit(tmp_path / "run"))

    document = build_comparison_document(run)

    assert "data:image/png;base64," in document
    assert sha256_file(run.stage1_image) in document
    assert sha256_file(run.stage2_regions) in document
    assert sha256_file(run.edited_regions) in document
    assert "stage-2-human-corrections.json" in document
    assert "Save" not in document
    assert "Add region" not in document
    assert "Delete region" not in document


def test_build_comparison_document_requires_an_edited_artifact(tmp_path: Path) -> None:
    run = discover_review_run(make_review_run(tmp_path / "run"))

    try:
        build_comparison_document(run)
    except ValueError as error:
        assert str(error) == "edited regions artifact is missing"
    else:
        raise AssertionError("expected missing edited artifact to raise")
