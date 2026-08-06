from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboarding_run import (
    OnboardingStateError,
    approve_stage,
    cached_source_path,
    read_status,
    replace_pending_checkpoint,
    start_run,
)


def test_replace_pending_checkpoint_selects_new_attempt_and_preserves_old(tmp_path: Path) -> None:
    run = _started_run(tmp_path)
    old = read_status(run)
    edited = _make_checkpoint(run.parent, stage=0, artifact_name="edited-stage-0")

    result = replace_pending_checkpoint(run, edited)

    assert result["status"] == "awaiting_approval"
    assert result["review"].endswith("stages/00/attempt-0002/stage-0-review.png")
    assert (run / old["review"]).is_file()
    assert read_status(run)["review"] == result["review"]


def test_replace_pending_checkpoint_rejects_approved_or_wrong_stage(tmp_path: Path) -> None:
    run = _started_run(tmp_path)
    approve_stage(run, 0)

    with pytest.raises(OnboardingStateError, match="not awaiting approval"):
        replace_pending_checkpoint(run, _make_checkpoint(run.parent, stage=0, artifact_name="edited-stage-0"))


def test_cached_source_path_returns_the_validated_cached_input(tmp_path: Path) -> None:
    run = _started_run(tmp_path)

    assert cached_source_path(run) == run / "inputs/source.png"


def _started_run(tmp_path: Path) -> Path:
    source = tmp_path / "source.png"
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    run = tmp_path / "run"
    start_run(
        "Example Board",
        str(source),
        run,
        runners={0: _StubStage0Runner()},
        workspace_root=tmp_path,
    )
    return run


class _StubStage0Runner:
    stage = 0

    def run(self, _context: object, artifact_root: Path) -> StageCheckpoint:
        return _make_checkpoint(
            artifact_root.parent, stage=0, artifact_name=artifact_root.name
        )


def _make_checkpoint(
    temporary_root: Path, *, stage: int, artifact_name: str
) -> StageCheckpoint:
    artifact_root = temporary_root / artifact_name
    artifact_root.mkdir()
    review = artifact_root / f"stage-{stage}-review.png"
    Image.new("RGB", (4, 4), (120, 80, 40)).save(review)
    candidate = artifact_root / f"stage-{stage}-candidate.json"
    candidate.write_text(
        json.dumps({"profile": {}, "registered": {}, "stage": stage}) + "\n",
        encoding="utf-8",
    )
    hashes = {
        candidate.name: sha256(candidate.read_bytes()).hexdigest(),
        review.name: sha256(review.read_bytes()).hexdigest(),
    }
    (artifact_root / "candidate-hashes.json").write_text(
        json.dumps(hashes, sort_keys=True) + "\n", encoding="utf-8"
    )
    return StageCheckpoint(
        stage=stage,
        artifact_root=artifact_root,
        candidate_hashes=hashes,
        review_path=review,
        machine_passed=True,
    )
