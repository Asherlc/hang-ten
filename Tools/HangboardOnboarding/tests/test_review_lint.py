from __future__ import annotations

from pathlib import Path

import pytest

from hangboard_vectorizer.review_artifacts import discover_review_run
from hangboard_vectorizer.review_lint import lint_review
from review_fixtures import make_review_run_with_edit


def test_lint_accepts_valid_edited_regions_and_matching_delta(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path)

    report = lint_review(discover_review_run(run))

    assert report.passed is True
    assert report.issues == ()


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        (lambda doc: doc["canvas"].update(width=0), "canvas.width-positive"),
        (
            lambda doc: doc["regions"][0].update(contour=[[1, 2], [3, 4]]),
            "contour.min-points",
        ),
        (
            lambda doc: doc["regions"][0]["contour"][0].__setitem__(0, -1),
            "contour.out-of-bounds",
        ),
    ],
)
def test_lint_reports_specific_geometry_failures(
    tmp_path: Path, mutation, code: str
) -> None:
    run = make_review_run_with_edit(tmp_path, mutate_edited=mutation)

    report = lint_review(discover_review_run(run))

    assert report.passed is False
    assert any(issue.code == code for issue in report.issues)


def test_lint_rejects_modified_delta_that_does_not_match_baseline(
    tmp_path: Path,
) -> None:
    run = make_review_run_with_edit(tmp_path, mutate_corrections=True)

    report = lint_review(discover_review_run(run))

    assert any(issue.code == "corrections.modified-mismatch" for issue in report.issues)
