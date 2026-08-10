from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from hangboard_vectorizer import workbench_validation
from hangboard_vectorizer.board_library import RepositoryBoardLibrary
from hangboard_vectorizer.workbench import WorkbenchService, WorkbenchServiceError
from hangboard_vectorizer.workbench_store import WorkbenchStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SOURCE = (
    REPOSITORY_ROOT
    / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii"
)


def test_validation_reports_package_parity_and_bounded_plan_library_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dropping a readiness, parity, or timeout guard must fail this report."""
    service, board_id, revision_id, repository_root = _validation_service(tmp_path)
    calls: list[tuple[list[str], Path, float]] = []

    def successful_check(
        command: list[str], *, cwd: Path, timeout: float, **_kwargs: object
    ) -> CompletedProcess[str]:
        calls.append((command, cwd, timeout))
        return CompletedProcess(command, 0, "PlanLibrary.json matches the source-audited definitions\n", "")

    monkeypatch.setattr(workbench_validation.subprocess, "run", successful_check)

    report = service.validation_report(
        board_id, expected_revision_id=revision_id
    )

    assert report.overall_status == "passed"
    assert [check.check_id for check in report.checks] == [
        "package-readiness",
        "hold-id-parity",
        "plan-library",
    ]
    assert [check.status for check in report.checks] == ["passed", "passed", "passed"]
    assert calls == [
        (
            [str(repository_root / "scripts/export-plan-library.sh"), "--check"],
            repository_root,
            30.0,
        )
    ]
    assert service.get_validation_report(
        board_id, expected_revision_id=revision_id
    ) == report


def test_validation_reports_invalid_package_without_changing_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Treating invalid artifacts as ready would allow an unsafe promotion path."""
    service, board_id, revision_id, repository_root = _validation_service(tmp_path)
    view = service.get_board(board_id, revision_id=revision_id)
    run = view.run_root / "run.json"
    contents = run.read_text(encoding="utf-8")
    run.write_text(contents.replace('"complete"', '"failed"', 1), encoding="utf-8")
    script = repository_root / "scripts/export-plan-library.sh"
    before = script.read_text(encoding="utf-8")

    monkeypatch.setattr(
        workbench_validation.subprocess,
        "run",
        lambda *_args, **_kwargs: pytest.fail("validation must not run native checks after package failure"),
    )
    with pytest.raises(WorkbenchServiceError, match="complete approved run"):
        service.validation_report(board_id, expected_revision_id=revision_id)

    assert script.read_text(encoding="utf-8") == before


def _validation_service(tmp_path: Path) -> tuple[WorkbenchService, str, str, Path]:
    repository_root = tmp_path / "repository"
    shutil.copytree(PACKAGE_SOURCE, repository_root / "Tools/HangboardOnboarding/boards/metolius-wood-grips-compact-ii")
    (repository_root / "scripts").mkdir(parents=True)
    (repository_root / "scripts/export-plan-library.sh").write_text("#!/bin/zsh\n", encoding="utf-8")
    library = RepositoryBoardLibrary(repository_root)
    service = WorkbenchService(WorkbenchStore(tmp_path / "workspace"), library=library)
    view = service.open_library_board("metolius-wood-grips-compact-ii")
    return service, view.board_id, view.revision_id, repository_root
