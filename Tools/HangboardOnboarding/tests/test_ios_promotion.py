from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from hangboard_vectorizer import ios_promotion
from hangboard_vectorizer.ios_promotion import (
    build_promotion_preview,
    read_promotion_profile,
    save_promotion_preview,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
ACCEPTED_RUN = (
    REPOSITORY_ROOT
    / "Tools/HangboardOnboarding/reference/metolius-compact-ii/accepted-run"
)
PROFILE_FIXTURE = Path(__file__).parent / "data/ios-promotion-profile.json"


def test_complete_approved_run_renders_the_known_native_contract(tmp_path: Path) -> None:
    """A missing board registration, geometry, or mapping must fail this contract."""
    run_root = _copied_run(tmp_path)
    repository_root = _repository_at_main(tmp_path)

    profile = read_promotion_profile(run_root)
    assert profile.board_id == "metolius.wood-grips.compact-ii"

    preview = build_promotion_preview(
        run_root,
        repository_root,
        profile,
        expected_base_ref="main",
    )

    assert [item.path for item in preview.files] == [
        "HangTen/Models/TrainingModels.swift",
        "HangTen/Views/MetoliusCompactIIDesign.swift",
        "HangTen/Models/PlanStorage.swift",
        "HangTen/Resources/PlanLibrary.json",
    ]
    assert preview.issues == ()
    assert "metolius.wood-grips.compact-ii" in preview.files[0].proposed_text
    assert "jug-left" in preview.files[1].proposed_text
    assert "BoardNormalizedPath" in preview.files[1].proposed_text
    assert "CGPoint(x: 0.001664, y: 0.097716)" in preview.files[1].proposed_text
    assert ".threeFingerPocket" in preview.files[0].proposed_text
    _assert_valid_semantic_hold_initializer(preview.files[2].proposed_text)


def test_preview_is_deterministic_and_can_be_saved_only_with_its_token(tmp_path: Path) -> None:
    """Changing proposed content or its token must prevent an accidental write."""
    run_root = _copied_run(tmp_path)
    repository_root = _repository_at_main(tmp_path)
    profile = read_promotion_profile(run_root)

    first = build_promotion_preview(run_root, repository_root, profile)
    second = build_promotion_preview(run_root, repository_root, profile)

    assert first == second
    with pytest.raises(ValueError, match="preview token"):
        save_promotion_preview(first, repository_root, expected_preview_token="stale")

    result = save_promotion_preview(
        first,
        repository_root,
        expected_preview_token=first.preview_token,
    )
    assert result.saved is True
    assert result.board_id == profile.board_id
    assert result.paths == tuple(item.path for item in first.files)


def test_save_rejects_tampered_proposed_content_even_with_the_original_token(tmp_path: Path) -> None:
    """The browser cannot alter a preview after its token has been issued."""
    run_root = _copied_run(tmp_path)
    repository_root = _repository_at_main(tmp_path)
    preview = build_promotion_preview(run_root, repository_root, read_promotion_profile(run_root))
    tampered_file = replace(preview.files[0], proposed_text=preview.files[0].proposed_text + "// tampered\n")
    tampered = replace(preview, files=(tampered_file, *preview.files[1:]))

    with pytest.raises(ValueError, match="preview token"):
        save_promotion_preview(
            tampered,
            repository_root,
            expected_preview_token=preview.preview_token,
        )


def test_save_rolls_back_every_target_when_a_later_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A write failure after the first replacement leaves no partial promotion."""
    run_root = _copied_run(tmp_path)
    repository_root = _repository_at_main(tmp_path)
    preview = build_promotion_preview(run_root, repository_root, read_promotion_profile(run_root))
    originals = {
        item.path: (repository_root / item.path).read_text(encoding="utf-8")
        for item in preview.files
    }
    real_replace = ios_promotion.os.replace
    staged_replacements = 0

    def fail_on_second_staged_replace(source: str | Path, destination: str | Path) -> None:
        nonlocal staged_replacements
        if "/staged/" in str(source):
            staged_replacements += 1
            if staged_replacements == 2:
                raise OSError("injected replacement failure")
        real_replace(source, destination)

    monkeypatch.setattr(ios_promotion.os, "replace", fail_on_second_staged_replace)

    with pytest.raises(OSError, match="injected replacement failure"):
        save_promotion_preview(
            preview,
            repository_root,
            expected_preview_token=preview.preview_token,
        )

    assert {
        path: (repository_root / path).read_text(encoding="utf-8")
        for path in originals
    } == originals
    assert not list(repository_root.glob(".hangboard-promotion-*"))


def test_generator_rejects_an_incomplete_run(tmp_path: Path) -> None:
    """Promotion cannot use a run that has not completed all accepted stages."""
    run_root = _copied_run(tmp_path)
    document = _read_json(run_root / "run.json")
    document["pipeline"] = {"currentStage": 3, "status": "in_progress"}
    _write_json(run_root / "run.json", document)

    with pytest.raises(ValueError, match="complete"):
        build_promotion_preview(run_root, _repository_at_main(tmp_path), read_promotion_profile(run_root))


def test_generator_rejects_duplicate_hold_ids(tmp_path: Path) -> None:
    """Duplicated semantic keys would make generated hold IDs ambiguous."""
    run_root = _copied_run(tmp_path)
    stage2_path = run_root / "stages/02/attempt-0001/stage-2-regions.json"
    stage2 = _read_json(stage2_path)
    stage2["regions"][1]["key"] = stage2["regions"][0]["key"]
    _write_json(stage2_path, stage2)

    with pytest.raises(ValueError, match="duplicate hold ID"):
        build_promotion_preview(run_root, _repository_at_main(tmp_path), read_promotion_profile(run_root))


def test_generator_rejects_a_missing_stage_3_path(tmp_path: Path) -> None:
    """Each approved semantic hold needs its exact Stage 3 geometry."""
    run_root = _copied_run(tmp_path)
    stage3_path = run_root / "stages/03/attempt-0001/stage-3-vector-regions.json"
    stage3 = _read_json(stage3_path)
    del stage3["regions"][0]["displayPath"]
    _write_json(stage3_path, stage3)

    with pytest.raises(ValueError, match="displayPath"):
        build_promotion_preview(run_root, _repository_at_main(tmp_path), read_promotion_profile(run_root))


def test_generator_rejects_a_profile_with_an_unsupported_swift_enum_value(tmp_path: Path) -> None:
    """A non-native hold type must not be guessed into a Swift enum case."""
    run_root = _copied_run(tmp_path)
    stage2_path = run_root / "stages/02/attempt-0001/stage-2-regions.json"
    stage2 = _read_json(stage2_path)
    stage2["regions"][0]["type"] = "pinch"
    _write_json(stage2_path, stage2)

    with pytest.raises(ValueError, match="unsupported Swift HoldKind"):
        build_promotion_preview(run_root, _repository_at_main(tmp_path), read_promotion_profile(run_root))


def test_generator_rejects_a_target_changed_relative_to_the_expected_base(tmp_path: Path) -> None:
    """Promotion must not overwrite a native file changed since its base revision."""
    run_root = _copied_run(tmp_path)
    repository_root = _repository_at_main(tmp_path)
    target = repository_root / "HangTen/Models/TrainingModels.swift"
    target.write_text(target.read_text(encoding="utf-8") + "\n// local change\n", encoding="utf-8")

    with pytest.raises(ValueError, match="changed relative to main"):
        build_promotion_preview(run_root, repository_root, read_promotion_profile(run_root))


def _copied_run(tmp_path: Path) -> Path:
    run_root = tmp_path / "accepted-run"
    shutil.copytree(ACCEPTED_RUN, run_root)
    shutil.copy2(PROFILE_FIXTURE, run_root / "ios-promotion-profile.json")
    return run_root


def _repository_at_main(tmp_path: Path) -> Path:
    repository_root = tmp_path / "repository"
    for relative_path in (
        "HangTen/Models/TrainingModels.swift",
        "HangTen/Views/MetoliusCompactIIDesign.swift",
        "HangTen/Models/PlanStorage.swift",
        "HangTen/Resources/PlanLibrary.json",
    ):
        source = REPOSITORY_ROOT / relative_path
        target = repository_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    _git(repository_root, "init", "--initial-branch=main")
    _git(repository_root, "config", "user.name", "Hang Ten Tests")
    _git(repository_root, "config", "user.email", "tests@example.invalid")
    _git(repository_root, "add", ".")
    _git(repository_root, "commit", "-m", "baseline")
    return repository_root


def _git(repository_root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repository_root), *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _assert_valid_semantic_hold_initializer(source: str) -> None:
    anchor = "private static let semanticHoldIDs: [String: [String]] = ["
    assert source.count(anchor) == 1
    opening = source.index(anchor) + len(anchor) - 1
    closing = _matching_delimiter(source, opening, "[", "]")
    assert not source[closing + 1:].startswith(" = [")
    assert source[closing + 1:].lstrip().startswith("static let document")


def _matching_delimiter(source: str, opening: int, left: str, right: str) -> int:
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == left:
            depth += 1
        elif source[index] == right:
            depth -= 1
            if depth == 0:
                return index
    raise AssertionError("unterminated Swift collection")
