from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Callable

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
VERIFIER = REPOSITORY_ROOT / "scripts/verify-sloper-metadata-migration.py"


def _run_git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def _board_document() -> dict[str, Any]:
    return {
        "id": "fixture.board",
        "manufacturer": "Fixture Maker",
        "name": "Fixture Board",
        "holds": [
            {
                "id": "sloper-left",
                "name": "Left sloper",
                "kind": "sloper",
                "geometry": [{"frame": {"x": 0.1, "y": 0.2}}],
            },
            {
                "id": "sloper-right",
                "name": "Right sloper",
                "kind": "sloper",
                "sloper": {"type": "round"},
                "geometry": [{"frame": {"x": 0.7, "y": 0.2}}],
            },
        ],
    }


def _initialize_repository(tmp_path: Path) -> tuple[Path, str, dict[str, Any]]:
    repository = tmp_path / "repository"
    repository.mkdir()
    _run_git(repository, "init", "--quiet")
    _run_git(repository, "config", "user.name", "Verifier Test")
    _run_git(repository, "config", "user.email", "verifier@example.com")
    _run_git(repository, "config", "commit.gpgsign", "false")
    document = _board_document()
    _write_json(repository / "Hangboards/fixture/board.json", document)
    _write_json(
        repository / "HangTen/Resources/PlanLibrary.json",
        {"plans": [{"id": "fixture-plan"}]},
    )
    _run_git(repository, "add", ".")
    _run_git(repository, "commit", "--quiet", "-m", "base")
    base = _run_git(repository, "rev-parse", "HEAD").stdout.strip()
    return repository, base, document


def _commit_head(repository: Path) -> str:
    _run_git(repository, "add", "--all")
    _run_git(repository, "commit", "--quiet", "-m", "head")
    return _run_git(repository, "rev-parse", "HEAD").stdout.strip()


def _run_verifier(
    repository: Path, base: str, head: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VERIFIER), base, head],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_allows_only_new_hold_sloper_values(tmp_path: Path) -> None:
    repository, base, document = _initialize_repository(tmp_path)
    document["holds"][0]["sloper"] = {"type": "flat", "angleDegrees": 20}
    _write_json(repository / "Hangboards/fixture/board.json", document)
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Verified sloper-only board JSON changes in 1 file.\n"


def test_uses_merge_base_when_base_and_head_have_diverged(tmp_path: Path) -> None:
    repository, base, base_document = _initialize_repository(tmp_path)
    _run_git(repository, "branch", "target", base)
    _run_git(repository, "switch", "--quiet", "target")

    document = copy.deepcopy(base_document)
    document["name"] = "Target branch board name"
    _write_json(repository / "Hangboards/fixture/board.json", document)
    _commit_head(repository)

    _run_git(repository, "switch", "--quiet", "--detach", base)
    document = copy.deepcopy(base_document)
    document["holds"][0]["sloper"] = {"type": "flat"}
    _write_json(repository / "Hangboards/fixture/board.json", document)
    head = _commit_head(repository)

    result = _run_verifier(repository, "target", head)

    assert result.returncode == 0, result.stderr
    assert result.stdout == "Verified sloper-only board JSON changes in 1 file.\n"


def _change_geometry(document: dict[str, Any]) -> None:
    document["holds"][0]["geometry"][0]["frame"]["x"] = 0.2


def _change_hold_order(document: dict[str, Any]) -> None:
    document["holds"].reverse()


def _change_non_sloper_metadata(document: dict[str, Any]) -> None:
    document["holds"][0]["name"] = "Renamed sloper"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (_change_geometry, "holds[0].geometry[0].frame.x changed"),
        (_change_hold_order, "hold identity/order changed at holds[0]"),
        (_change_non_sloper_metadata, "holds[0].name changed"),
    ],
)
def test_rejects_non_sloper_board_json_mutations(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    repository, base, base_document = _initialize_repository(tmp_path)
    document = copy.deepcopy(base_document)
    document["holds"][0]["sloper"] = {"type": "flat"}
    mutation(document)
    _write_json(repository / "Hangboards/fixture/board.json", document)
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 1
    assert f"Hangboards/fixture/board.json: {message}" in result.stderr


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda document: document["holds"][1].update(
                {"sloper": {"type": "flat"}}
            ),
            "pre-existing holds[1].sloper changed",
        ),
        (
            lambda document: document["holds"][1].pop("sloper"),
            "pre-existing holds[1].sloper was removed",
        ),
    ],
)
def test_rejects_changes_to_pre_existing_sloper_values(
    tmp_path: Path,
    mutation: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    repository, base, base_document = _initialize_repository(tmp_path)
    document = copy.deepcopy(base_document)
    mutation(document)
    _write_json(repository / "Hangboards/fixture/board.json", document)
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 1
    assert f"Hangboards/fixture/board.json: {message}" in result.stderr


def test_rejects_invalid_board_json(tmp_path: Path) -> None:
    repository, base, _ = _initialize_repository(tmp_path)
    board_path = repository / "Hangboards/fixture/board.json"
    board_path.write_text('{"holds": [', encoding="utf-8")
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 1
    assert "Hangboards/fixture/board.json: head JSON is invalid" in result.stderr


def test_rejects_missing_board_json(tmp_path: Path) -> None:
    repository, base, _ = _initialize_repository(tmp_path)
    (repository / "Hangboards/fixture/board.json").unlink()
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 1
    assert "Hangboards/fixture/board.json: missing at head" in result.stderr


def test_rejects_training_plan_source_path_in_diff(tmp_path: Path) -> None:
    repository, base, _ = _initialize_repository(tmp_path)
    _write_json(
        repository / "HangTen/Resources/PlanLibrary.json",
        {"plans": [{"id": "changed-plan"}]},
    )
    head = _commit_head(repository)

    result = _run_verifier(repository, base, head)

    assert result.returncode == 1
    assert (
        "HangTen/Resources/PlanLibrary.json: training-plan source path changed"
        in result.stderr
    )
