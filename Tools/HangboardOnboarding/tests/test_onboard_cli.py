from __future__ import annotations

from pathlib import Path

import pytest

from hangboard_vectorizer.onboard_cli import main
from hangboard_vectorizer.onboarding_run import start_run


def test_start_run_rejects_output_outside_owned_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "owned"
    workspace.mkdir()
    outside = tmp_path / "outside" / "run"

    with pytest.raises(ValueError, match="must stay inside workspace root"):
        start_run(
            "Example Board",
            str(tmp_path / "source.png"),
            outside,
            workspace_root=workspace,
        )

    assert not outside.exists()


def test_onboard_cli_rejects_output_outside_owned_workspace(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    workspace = tmp_path / "owned"
    workspace.mkdir()
    outside = tmp_path / "outside" / "run"

    result = main(
        [
            "--product-name",
            "Example Board",
            "--source",
            str(tmp_path / "source.png"),
            "--workspace-root",
            str(workspace),
            "--output",
            str(outside),
        ]
    )

    assert result == 2
    assert "must stay inside workspace root" in capsys.readouterr().err
    assert not outside.exists()
