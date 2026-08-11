from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_checks_the_generated_board_library() -> None:
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Verify generated board library" in workflow
    assert "working-directory: ${{ github.workspace }}" in workflow
    assert "python3 scripts/export-board-library.py --check" in workflow
