from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from hangboard_vectorizer.board_library import RepositoryBoardLibrary
from hangboard_vectorizer.ios_promotion import read_promotion_profile
from hangboard_vectorizer.workbench_promotion import profile_from_payload
import hangboard_vectorizer.workbench as workbench_module
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


@pytest.mark.parametrize("ratio", (float("nan"), float("inf"), float("-inf")))
def test_profile_payload_rejects_non_finite_aspect_ratios(ratio: float) -> None:
    """The browser adapter must not admit ratios that JSON decoders can represent."""
    payload = json.loads(PROFILE_SOURCE.read_text(encoding="utf-8"))
    payload["aspectRatio"] = ratio

    with pytest.raises(ValueError, match="finite positive"):
        profile_from_payload(payload)


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


def test_preview_accepts_the_canonical_ios_profile_without_rewriting_its_board_id(
    tmp_path: Path,
) -> None:
    """Using direct namespace equality would reject the canonical iOS profile."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(
        tmp_path, use_fixture_profile=True
    )
    before = _target_contents(repository_root)

    preview = service.preview_promotion(
        board_id,
        expected_revision_id=revision_id,
        profile=profile,
    )

    assert profile.board_id == "metolius.wood-grips.compact-ii"
    assert preview.board_id == profile.board_id
    assert _target_contents(repository_root) == before


def test_preview_rejects_a_legacy_profile_alias_that_collides_in_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Collapsing dotted repository IDs to hyphens must fail closed on ambiguity."""
    repository_root = _repository(tmp_path)
    source = repository_root / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
    collision = repository_root / "Tools/HangboardOnboarding/boards/metolius.wood-grips.compact-ii"
    shutil.copytree(source, collision)
    run_path = collision / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run["product"]["key"] = "metolius.wood-grips.compact-ii"
    run_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    library = RepositoryBoardLibrary(repository_root)
    service = WorkbenchService(WorkbenchStore(tmp_path / "workspace"), library=library)
    view = service.open_library_board("metolius-wood-grips-compact-ii")
    shutil.copy2(PROFILE_SOURCE, view.run_root / "ios-promotion-profile.json")
    profile = read_promotion_profile(view.run_root)

    def generation_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("promotion generation must not run")

    monkeypatch.setattr(workbench_module, "preview_for_revision", generation_must_not_run)

    with pytest.raises(WorkbenchServiceError, match="profile board ID"):
        service.preview_promotion(
            view.board_id,
            expected_revision_id=view.revision_id,
            profile=profile,
        )


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


def test_save_promotion_keeps_preview_revision_token_as_the_content_hash(
    tmp_path: Path,
) -> None:
    """The saved result may override revision_id, but the preview token stays hashed."""
    service, board_id, revision_id, _repository_root, profile = _promotion_service(tmp_path)
    preview = service.preview_promotion(
        board_id, expected_revision_id=revision_id, profile=profile
    )

    int(preview.revision_token, 16)
    assert preview.revision_token != revision_id

    saved = service.save_promotion(
        board_id,
        expected_revision_id=revision_id,
        profile=profile,
        preview_token=preview.preview_token,
    )

    assert saved.revision_id == revision_id
    assert preview.revision_token != saved.revision_id


def test_preview_rejects_a_profile_for_another_repository_board_before_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing the identity gate would generate native output for another board."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(tmp_path)
    before = _target_contents(repository_root)
    other_board_profile = replace(profile, board_id="another-board")

    def generation_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("promotion generation must not run")

    monkeypatch.setattr(workbench_module, "preview_for_revision", generation_must_not_run)

    with pytest.raises(WorkbenchServiceError, match="profile board ID"):
        service.preview_promotion(
            board_id,
            expected_revision_id=revision_id,
            profile=other_board_profile,
        )

    assert _target_contents(repository_root) == before


def test_save_rejects_a_profile_for_another_repository_board_before_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing the identity gate would save active geometry under another identity."""
    service, board_id, revision_id, repository_root, profile = _promotion_service(tmp_path)
    before = _target_contents(repository_root)
    other_board_profile = replace(profile, board_id="another-board")

    def generation_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("promotion generation must not run")

    monkeypatch.setattr(workbench_module, "preview_for_revision", generation_must_not_run)

    with pytest.raises(WorkbenchServiceError, match="profile board ID"):
        service.save_promotion(
            board_id,
            expected_revision_id=revision_id,
            profile=other_board_profile,
            preview_token="preview-token",
        )

    assert _target_contents(repository_root) == before


def test_promotion_preview_cache_is_scoped_to_the_active_revision(tmp_path: Path) -> None:
    """Returning a cache entry after a revision change would expose stale geometry."""
    service, board_id, revision_id, _repository_root, profile = _promotion_service(tmp_path)

    assert (
        service.get_promotion_preview(
            board_id, expected_revision_id=revision_id
        )
        is None
    )
    preview = service.preview_promotion(
        board_id, expected_revision_id=revision_id, profile=profile
    )
    assert service.get_promotion_preview(
        board_id, expected_revision_id=revision_id
    ) == preview

    next_revision = service.store.create_revision(board_id)
    service.store.activate_revision(board_id, next_revision.id)

    assert service.get_promotion_preview(
        board_id, expected_revision_id=next_revision.id
    ) is None
    with pytest.raises(WorkbenchServiceError, match="expected revision"):
        service.get_promotion_preview(
            board_id, expected_revision_id=revision_id
        )


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
    tmp_path: Path, *, use_fixture_profile: bool = False
) -> tuple[WorkbenchService, str, str, Path, object]:
    repository_root = _repository(tmp_path)
    library = RepositoryBoardLibrary(repository_root)
    service = WorkbenchService(WorkbenchStore(tmp_path / "workspace"), library=library)
    view = service.open_library_board("metolius-wood-grips-compact-ii")
    shutil.copy2(PROFILE_SOURCE, view.run_root / "ios-promotion-profile.json")
    profile = read_promotion_profile(view.run_root)
    if not use_fixture_profile:
        profile = replace(profile, board_id="metolius-wood-grips-compact-ii")
    return (
        service,
        view.board_id,
        view.revision_id,
        repository_root,
        profile,
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
