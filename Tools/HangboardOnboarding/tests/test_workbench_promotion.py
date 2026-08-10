from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from hangboard_vectorizer.board_library import RepositoryBoardLibrary
from hangboard_vectorizer.ios_promotion import read_promotion_profile
from hangboard_vectorizer.workbench import WorkbenchService, WorkbenchServiceError
from hangboard_vectorizer.workbench_store import WorkbenchStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SOURCE = (
    REPOSITORY_ROOT
    / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
)
PROFILE_SOURCE = Path(__file__).parent / "data/ios-promotion-profile.json"
TARGETS = (
    "HangTen/Models/TrainingModels.swift",
    "HangTen/Views/MetoliusCompactIIDesign.swift",
    "HangTen/Models/PlanStorage.swift",
    "HangTen/Resources/PlanLibrary.json",
)


def test_preview_is_bound_to_the_active_revision_without_writing_checkout(
    tmp_path: Path,
) -> None:
    """Changing a revision check into a best-effort lookup must fail this test."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(tmp_path)
    before = _target_contents(repository_root)

    preview = service.preview_promotion(
        board_id,
        expected_revision_id=revision_id,
        profile=profile,
    )

    assert preview.board_id == profile.board_id
    assert preview.revision_token
    assert _target_contents(repository_root) == before

    with pytest.raises(WorkbenchServiceError, match="expected revision"):
        service.preview_promotion(
            board_id,
            expected_revision_id="revision-stale",
            profile=profile,
        )
    assert _target_contents(repository_root) == before


def test_save_rejects_a_stale_preview_token_without_writing_checkout(
    tmp_path: Path,
) -> None:
    """Removing token comparison would allow a browser to save another preview."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(tmp_path)
    preview = service.preview_promotion(
        board_id, expected_revision_id=revision_id, profile=profile
    )
    before = _target_contents(repository_root)

    with pytest.raises(WorkbenchServiceError, match="preview token"):
        service.save_promotion(
            board_id,
            expected_revision_id=revision_id,
            profile=profile,
            preview_token="stale-token",
        )

    assert _target_contents(repository_root) == before


def test_preview_rejects_dirty_native_targets_without_writing_other_targets(
    tmp_path: Path,
) -> None:
    """Removing the base fingerprint check would overwrite local native changes."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(tmp_path)
    dirty_path = repository_root / TARGETS[0]
    dirty_path.write_text(dirty_path.read_text(encoding="utf-8") + "// local change\n", encoding="utf-8")
    before = _target_contents(repository_root)

    with pytest.raises(WorkbenchServiceError, match="changed relative to main"):
        service.preview_promotion(
            board_id, expected_revision_id=revision_id, profile=profile
        )

    assert _target_contents(repository_root) == before


def _promotion_service(
    tmp_path: Path,
) -> tuple[WorkbenchService, str, str, Path, object]:
    repository_root = _repository(tmp_path)
    library = RepositoryBoardLibrary(repository_root)
    service = WorkbenchService(WorkbenchStore(tmp_path / "workspace"), library=library)
    view = service.open_library_board("metolius-wood-grips-compact-ii")
    shutil.copy2(PROFILE_SOURCE, view.run_root / "ios-promotion-profile.json")
    return (
        service,
        view.board_id,
        view.revision_id,
        repository_root,
        read_promotion_profile(view.run_root),
    )


def _repository(tmp_path: Path) -> Path:
    repository_root = tmp_path / "repository"
    shutil.copytree(PACKAGE_SOURCE, repository_root / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii")
    for relative in TARGETS:
        target = repository_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPOSITORY_ROOT / relative, target)
    _git(repository_root, "init", "--initial-branch=main")
    _git(repository_root, "config", "user.name", "Hang Ten Tests")
    _git(repository_root, "config", "user.email", "tests@example.invalid")
    _git(repository_root, "add", ".")
    _git(repository_root, "commit", "-m", "baseline")
    return repository_root


def _target_contents(repository_root: Path) -> dict[str, str]:
    return {
        relative: (repository_root / relative).read_text(encoding="utf-8")
        for relative in TARGETS
    }


def _git(repository_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
