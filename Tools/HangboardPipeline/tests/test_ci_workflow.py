from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
CODEQL_WORKFLOW_PATH = REPOSITORY_ROOT / ".github" / "workflows" / "codeql.yml"


def test_ci_checks_the_generated_board_library() -> None:
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "name: Verify generated board library" in workflow
    assert "working-directory: ${{ github.workspace }}" in workflow
    assert "python3 scripts/export-board-library.py --check" in workflow


def test_codeql_workflow_uses_conditional_language_gate() -> None:
    workflow = CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8")

    assert "dorny/paths-filter@ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d" in workflow
    assert "languages: actions" in workflow
    assert "needs.changes.outputs.swift == 'true'" in workflow
    assert "needs.changes.outputs.python == 'true'" in workflow
    assert "needs.changes.outputs.javascript == 'true'" in workflow
    assert "name: CodeQL gate" in workflow
    assert "if: ${{ always() }}" in workflow
    assert "needs: [changes, analyze-actions, analyze-swift, analyze-python, analyze-javascript]" in workflow


def test_codeql_workflow_is_not_filtered_before_it_can_report_its_gate() -> None:
    workflow = CODEQL_WORKFLOW_PATH.read_text(encoding="utf-8")
    trigger_section = workflow.split("permissions:", 1)[0]

    assert "paths:" not in trigger_section
    assert "paths-ignore:" not in trigger_section
