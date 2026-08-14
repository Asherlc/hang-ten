from __future__ import annotations

import json
from pathlib import Path

import pytest

from hangboard_vectorizer.semantic_benchmark import (
    build_metolius_benchmark_report,
    main,
)


PACKAGE = Path(__file__).resolve().parents[3] / "Hangboards" / "metolius-wood-grips-compact-ii"


def test_canonical_package_benchmark_proves_semantic_parity(tmp_path: Path) -> None:
    report = build_metolius_benchmark_report(
        PACKAGE, tmp_path / "report.json", workspace_root=tmp_path
    )
    assert report["boardId"] == "metolius.wood-grips-compact-ii"
    assert report["parity"]["exact"] is True
    assert report["parity"]["semantics"]["exact"] is True
    assert len(report["packageSha256"]) == 64


def test_benchmark_cli_writes_canonical_sorted_report(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert main(["--package", str(PACKAGE), "--output", str(output), "--workspace-root", str(tmp_path)]) == 0
    document = json.loads(output.read_text())
    assert output.read_text() == json.dumps(document, indent=2, sort_keys=True) + "\n"


def test_benchmark_cli_rejects_outputs_outside_workspace_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must stay inside workspace root"):
        main(["--package", str(PACKAGE), "--output", str(tmp_path.parent / "escaped.json"), "--workspace-root", str(tmp_path)])
