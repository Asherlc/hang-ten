from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from hangboard_vectorizer.review_artifacts import discover_review_run
from hangboard_vectorizer.review_lint import lint_review
from review_fixtures import make_review_run, make_review_run_with_edit


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


def test_lint_accepts_documents_emitted_by_editor_model(tmp_path: Path) -> None:
    run = make_review_run(tmp_path / "run")
    stage2_dir = run / "stages/02/attempt-0001"
    editor_model = Path(__file__).resolve().parents[2] / "hold-highlight-editor/editor-model.js"
    script = """
const fs = require("node:fs");
const model = require(process.argv[1]);
const stage2Dir = process.argv[2];
const baselineDocument = JSON.parse(fs.readFileSync(`${stage2Dir}/stage-2-regions.json`, "utf8"));
const normalized = model.normalizePipelineDocument(baselineDocument, baselineDocument.canvas);
const modified = JSON.parse(JSON.stringify(normalized.regions[0]));
modified.contour[1][0] = 13;
const added = JSON.parse(JSON.stringify(normalized.regions[0]));
added.id = 2;
added.key = "right";
added.type = "pocket";
added.metadata.mode = "aperture";
added.contour = [[18, 3], [27, 3], [27, 8], [18, 8]];
const regions = [modified, added];
fs.writeFileSync(
  `${stage2Dir}/stage-2-regions.edited.json`,
  `${JSON.stringify(model.buildEditedDocument({
    canvas: normalized.canvas,
    regions,
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  }))}\n`,
);
fs.writeFileSync(
  `${stage2Dir}/stage-2-human-corrections.json`,
  `${JSON.stringify(model.buildCorrectionsDocument({
    baselineRegions: normalized.regions,
    regions,
    imageName: "stage-1-auto-rgba.png",
    regionsName: "stage-2-regions.json",
  }))}\n`,
);
"""
    subprocess.run(
        ["node", "-e", script, str(editor_model), str(stage2_dir)],
        check=True,
        capture_output=True,
        text=True,
    )

    report = lint_review(discover_review_run(run))

    assert report.passed is True, report.issues


def test_lint_rejects_an_omitted_modified_correction(tmp_path: Path) -> None:
    run = make_review_run_with_edit(tmp_path / "run")
    corrections_path = run / "stages/02/attempt-0001/stage-2-human-corrections.json"
    corrections = json.loads(corrections_path.read_text(encoding="utf-8"))
    corrections["modified"] = []
    corrections["summary"]["modified"] = 0
    corrections_path.write_text(json.dumps(corrections) + "\n", encoding="utf-8")

    report = lint_review(discover_review_run(run))

    assert any(issue.code == "corrections.modified-missing" for issue in report.issues)
