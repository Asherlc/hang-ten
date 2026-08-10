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
    / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
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


@pytest.mark.parametrize("ratio", (float("nan"), float("inf"), float("-inf")))
def test_profile_reader_rejects_non_finite_aspect_ratios(tmp_path: Path, ratio: float) -> None:
    """Non-finite ratios must not reach native layout generation."""
    run_root = _copied_run(tmp_path)
    profile = _read_json(run_root / "ios-promotion-profile.json")
    profile["aspectRatio"] = ratio
    _write_json(run_root / "ios-promotion-profile.json", profile)

    with pytest.raises(ValueError, match="finite positive"):
        read_promotion_profile(run_root)


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


def test_default_preview_rejects_worktree_native_target_drift(tmp_path: Path) -> None:
    """Promotion must fail closed when native targets drift from the main baseline."""
    run_root = _copied_run(tmp_path)

    with pytest.raises(ValueError, match="(changed relative to main|cannot verify target against main)"):
        build_promotion_preview(run_root, REPOSITORY_ROOT, read_promotion_profile(run_root))


def test_render_plan_library_rewrites_only_the_exact_board_id_value() -> None:
    """Substring matches in notes, URLs, or identifiers must stay untouched."""
    current = json.dumps(
        {
            "boardMappings": [
                {
                    "boardID": "metolius.wood-grips-compact-ii",
                    "identifier": "board-metolius.wood-grips-compact-ii-bundle",
                    "notes": [
                        "keep metolius.wood-grips-compact-ii-beta",
                        "legacy metolius.wood-grips-compact-ii note",
                    ],
                    "semanticHolds": {
                        "outer-jugs": {"holdIDs": ["jug-left", "jug-right"]},
                    },
                    "sourceURL": (
                        "https://example.com/boards/"
                        "metolius.wood-grips-compact-ii?boardID=metolius.wood-grips-compact-ii"
                    ),
                }
            ]
        },
        indent=2,
    )

    proposed = ios_promotion._render_plan_library(
        current,
        "metolius.wood-grips-compact-iii",
        {"outer-jugs": ("jug-left", "jug-right")},
    )
    document = json.loads(proposed)
    mapping = document["boardMappings"][0]

    assert mapping["boardID"] == "metolius.wood-grips-compact-iii"
    assert mapping["identifier"] == "board-metolius.wood-grips-compact-ii-bundle"
    assert mapping["notes"] == [
        "keep metolius.wood-grips-compact-ii-beta",
        "legacy metolius.wood-grips-compact-ii note",
    ]
    assert (
        mapping["sourceURL"]
        == "https://example.com/boards/metolius.wood-grips-compact-ii?boardID=metolius.wood-grips-compact-ii"
    )


def test_render_plan_library_does_not_require_the_old_board_id_elsewhere_in_document() -> None:
    """The mapping's exact boardID value is the only old-ID reference that must matter."""
    current = json.dumps(
        {
            "boardMappings": [
                {
                    "boardID": "metolius.wood-grips-compact-ii",
                    "semanticHolds": {
                        "outer-jugs": {"holdIDs": ["jug-left", "jug-right"]},
                    },
                }
            ]
        },
        indent=2,
    )

    proposed = ios_promotion._render_plan_library(
        current,
        "metolius.wood-grips-compact-iii",
        {"outer-jugs": ("jug-left", "jug-right")},
    )

    assert json.loads(proposed)["boardMappings"][0]["boardID"] == "metolius.wood-grips-compact-iii"


@pytest.mark.parametrize("expected_base_ref", ["", "-bad", "bad ref", "bad..ref"])
def test_assert_targets_at_base_rejects_invalid_git_refs_before_diff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, expected_base_ref: str
) -> None:
    """Invalid refs must fail before any git diff invocation is attempted."""
    repository_root = _repository_at_main(tmp_path)
    real_run = ios_promotion.subprocess.run
    diff_calls: list[list[str]] = []

    def run_spy(*args: object, **kwargs: object):
        command = args[0]
        assert isinstance(command, list)
        if len(command) >= 4 and command[2] == "diff":
            diff_calls.append(command)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(ios_promotion.subprocess, "run", run_spy)

    with pytest.raises(ValueError):
        ios_promotion._assert_targets_at_base(repository_root, expected_base_ref)

    assert diff_calls == []


def test_assert_targets_at_base_accepts_a_valid_git_ref(tmp_path: Path) -> None:
    """A valid base ref should preserve the existing diff-based verification path."""
    repository_root = _repository_at_main(tmp_path)

    ios_promotion._assert_targets_at_base(repository_root, "main")


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
