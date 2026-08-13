from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"
README = REPO_ROOT / "README.md"
ADDING_A_BOARD = REPO_ROOT / "docs/ADDING_A_BOARD.md"


def test_active_delivery_guidance_uses_the_direct_approved_package_contract() -> None:
    """Removing a direct-package delivery step would let drafts or legacy outputs ship."""
    ci_workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    active_docs = "\n".join(
        path.read_text(encoding="utf-8") for path in (README, ADDING_A_BOARD)
    )

    assert "catalog validate --catalog Hangboards/catalog.json" in ci_workflow
    assert "test_generated_catalog_import.py" in ci_workflow
    assert "stage-approved-board-packages.py" in ci_workflow
    assert "BoardPackageStoreTests" in ci_workflow
    assert "status: draft" in active_docs
    assert "status: approved" in active_docs
    assert "drafts never ship" in active_docs
    assert "bundles only approved packages" in active_docs
    assert "GeneratedBoardCatalog" not in active_docs
