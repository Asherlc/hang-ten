from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image
import pytest

from hangboard_vectorizer import onboarding_run
from hangboard_vectorizer.generic_stage0 import StageCheckpoint
from hangboard_vectorizer.onboarding_run import (
    OnboardingStateError,
    approve_stage,
    cached_source_path,
    read_status,
    replace_pending_checkpoint,
    resume_run,
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


def test_replace_pending_checkpoint_directly_rejects_the_wrong_stage(
    tmp_path: Path,
) -> None:
    run = _started_run(tmp_path)

    with pytest.raises(OnboardingStateError, match="does not match pending stage 0"):
        replace_pending_checkpoint(
            run,
            _make_checkpoint(run.parent, stage=1, artifact_name="edited-stage-1"),
        )


def test_failed_stage_attempt_is_durable_across_restart_and_retry(
    tmp_path: Path,
) -> None:
    run = _started_run(tmp_path)
    approve_stage(run, 0)

    with pytest.raises(RuntimeError, match="private runner detail"):
        resume_run(run, runners={1: _FailingStage1Runner()})

    failed_status = read_status(run)
    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    failure = manifest["failedAttempts"][0]
    failure_root = run / failure["artifactRoot"]
    evidence_before = {
        path.name: path.read_bytes() for path in failure_root.iterdir() if path.is_file()
    }
    assert failed_status == {
        "run": str(run),
        "stage": 0,
        "status": "failed",
        "nextAction": "retry-stage-1",
    }
    assert failure["stage"] == 1
    assert failure["attempt"] == 1
    assert failure["status"] == "failed"
    assert failure_root.joinpath(failure["logPath"]).is_file()
    failure_text = failure_root.joinpath(failure["logPath"]).read_text()
    assert str(tmp_path) not in failure_text
    assert "/tmp/private-source.png" not in failure_text

    retried = resume_run(run, runners={1: _SuccessfulStage1Runner()})

    assert retried["review"].endswith("stages/01/attempt-0002/stage-1-review.png")
    assert {
        path.name: path.read_bytes() for path in failure_root.iterdir() if path.is_file()
    } == evidence_before


def test_failed_stage0_start_is_durable_and_retryable_from_cached_source(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    run = tmp_path / "run"

    with pytest.raises(RuntimeError, match="private runner detail"):
        start_run(
            "Example Board",
            str(source),
            run,
            runners={0: _FailingStage0Runner()},
            workspace_root=tmp_path,
        )

    failed_status = read_status(run)
    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    failure = manifest["failedAttempts"][0]
    failure_log = run / failure["artifactRoot"] / failure["logPath"]
    evidence_before = failure_log.read_bytes()
    assert failed_status == {
        "run": str(run),
        "stage": 0,
        "status": "failed",
        "nextAction": "retry-stage-0",
    }
    assert failure == {
        "artifactRoot": "stages/00/attempt-0001",
        "attempt": 1,
        "error": "stage execution failed",
        "errorKind": "RuntimeError",
        "logPath": "stage-0-failure.log",
        "logSha256": sha256(evidence_before).hexdigest(),
        "stage": 0,
        "status": "failed",
    }
    assert str(tmp_path) not in evidence_before.decode("utf-8")
    assert "/tmp/private-source.png" not in evidence_before.decode("utf-8")

    retried = resume_run(run, runners={0: _StubStage0Runner()})

    assert retried["status"] == "awaiting_approval"
    assert retried["review"].endswith(
        "stages/00/attempt-0002/stage-0-review.png"
    )
    assert failure_log.read_bytes() == evidence_before


def test_malformed_stage0_checkpoint_is_published_as_retryable_failure(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    run = tmp_path / "run"

    with pytest.raises(
        OnboardingStateError, match="required evidence is missing"
    ):
        start_run(
            "Example Board",
            str(source),
            run,
            runners={0: _MalformedStage0Runner()},
            workspace_root=tmp_path,
        )

    assert cached_source_path(run).read_bytes() == source.read_bytes()
    assert read_status(run) == {
        "run": str(run),
        "stage": 0,
        "status": "failed",
        "nextAction": "retry-stage-0",
    }
    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    failure = manifest["failedAttempts"][0]
    failure_log = run / failure["artifactRoot"] / "stage-0-failure.log"
    assert failure["errorKind"] == "OnboardingStateError"
    assert failure["error"] == "stage execution failed"
    assert failure_log.is_file()
    assert str(tmp_path) not in failure_log.read_text(encoding="utf-8")


def test_failure_evidence_redacts_short_secret_messages(tmp_path: Path) -> None:
    run = _started_run(tmp_path)
    approve_stage(run, 0)

    with pytest.raises(RuntimeError, match="Authorization: Bearer"):
        resume_run(run, runners={1: _SecretFailingStage1Runner()})

    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    failure = manifest["failedAttempts"][0]
    failure_log = run / failure["artifactRoot"] / failure["logPath"]
    assert failure["error"] == "stage execution failed"
    assert "secret-token" not in failure_log.read_text(encoding="utf-8")


def test_failed_stage_after_artifact_publication_removes_rejected_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run = _started_run(tmp_path)
    approve_stage(run, 0)
    actual_validate_checkpoint = onboarding_run._validate_checkpoint

    def reject_published_stage(
        root: Path,
        record: Mapping[str, object],
        *,
        require_artifact_layout: bool = True,
    ) -> None:
        if (
            record.get("stage") == 1
            and record.get("artifactRoot") == "stages/01/attempt-0001"
            and require_artifact_layout
        ):
            raise OnboardingStateError("post-publication validation failed")
        actual_validate_checkpoint(
            root,
            record,
            require_artifact_layout=require_artifact_layout,
        )

    monkeypatch.setattr(
        onboarding_run,
        "_validate_checkpoint",
        reject_published_stage,
    )

    with pytest.raises(OnboardingStateError, match="post-publication"):
        resume_run(run, runners={1: _SuccessfulStage1Runner()})

    artifact_root = run / "stages/01/attempt-0001"
    assert {path.name for path in artifact_root.iterdir()} == {
        "stage-1-failure.log"
    }


def test_failed_stage0_manifest_requires_failure_attempt_evidence(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.png"
    Image.new("RGB", (512, 512), (45, 65, 85)).save(source)
    run = tmp_path / "run"
    with pytest.raises(RuntimeError, match="private runner detail"):
        start_run(
            "Example Board",
            str(source),
            run,
            runners={0: _FailingStage0Runner()},
            workspace_root=tmp_path,
        )
    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    manifest["failedAttempts"] = []
    (run / "run.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        OnboardingStateError, match="failed run attempt evidence is missing"
    ):
        read_status(run)


def test_cached_source_path_returns_the_validated_cached_input(tmp_path: Path) -> None:
    run = _started_run(tmp_path)

    assert cached_source_path(run) == run / "inputs/source.png"


def test_cached_source_path_rejects_a_symlink_escape(tmp_path: Path) -> None:
    run = _started_run(tmp_path)
    cached = run / "inputs/source.png"
    cached.unlink()
    cached.symlink_to(tmp_path / "source.png")

    with pytest.raises(OnboardingStateError, match="escapes the run"):
        cached_source_path(run)


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


class _FailingStage1Runner:
    stage = 1

    def run(self, _context: object, _artifact_root: Path) -> StageCheckpoint:
        raise RuntimeError("private runner detail at /tmp/private-source.png")


class _FailingStage0Runner:
    stage = 0

    def run(self, _context: object, _artifact_root: Path) -> StageCheckpoint:
        raise RuntimeError("private runner detail at /tmp/private-source.png")


class _SecretFailingStage1Runner:
    stage = 1

    def run(self, _context: object, _artifact_root: Path) -> StageCheckpoint:
        raise RuntimeError("Authorization: Bearer secret-token")


class _MalformedStage0Runner:
    stage = 0

    def run(self, _context: object, artifact_root: Path) -> StageCheckpoint:
        artifact_root.mkdir(parents=True)
        return StageCheckpoint(
            stage=0,
            artifact_root=artifact_root,
            candidate_hashes={},
            review_path=artifact_root / "missing-review.png",
            machine_passed=True,
        )


class _SuccessfulStage1Runner:
    stage = 1

    def run(self, _context: object, artifact_root: Path) -> StageCheckpoint:
        return _make_checkpoint(
            artifact_root.parent, stage=1, artifact_name=artifact_root.name
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
