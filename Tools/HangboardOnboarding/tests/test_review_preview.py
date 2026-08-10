from __future__ import annotations

from pathlib import Path

import pytest

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
    first_gallery = tmp_path / "first/review-preview/review-gallery.html"
    second_gallery = tmp_path / "second/review-preview/review-gallery.html"
    assert first_gallery.read_bytes() == second_gallery.read_bytes()
    assert str((tmp_path / "first").resolve(strict=False)) not in first_gallery.read_text(
        encoding="utf-8"
    )


def test_preview_bundle_preserves_previous_output_when_publish_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = discover_review_run(make_review_run_with_edit(tmp_path / "run"))
    output = tmp_path / "preview-output"
    render_preview_bundle(run, output)
    sentinel = output / "review-preview/sentinel.txt"
    sentinel.write_text("keep me", encoding="utf-8")

    original_replace = Path.replace

    def failing_replace(self: Path, target: Path) -> Path:
        if (
            self.name == "review-preview"
            and self.parent.name.startswith(".review-preview.tmp-")
            and target.name == "review-preview"
        ):
            raise OSError("simulated publish failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", failing_replace)

    with pytest.raises(OSError, match="simulated publish failure"):
        render_preview_bundle(run, output)

    assert sentinel.read_text(encoding="utf-8") == "keep me"


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
